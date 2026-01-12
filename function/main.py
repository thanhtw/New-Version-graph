import json
import torch
import pandas as pd
from inference import load_model, batch_predict, find_uncertain_predictions

def process_json_with_predictions(input_path, output_path, model_path, device):
    print(f"Starting JSON data processing...")
    print(f"Input file: {input_path}")
    print(f"Output file: {output_path}")
    print(f"Model path: {model_path}")
    print(f"Using 'suggestion' keyword rule to enhance constructive labels")
    
    model, tokenizer = load_model(model_path, device)

    label_thresholds = {
        "relevance": 0.5,
        "concreteness": 0.5,
        "constructive": 0.7
    }

    thresholds_list = [
        label_thresholds["relevance"],
        label_thresholds["concreteness"],
        label_thresholds["constructive"]
    ]

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Read {len(data)} homework assignments")
    
    total_assignments = sum(len(assignments) for assignments in data.values())
    print(f"Total {total_assignments} assignments")
    
    processed_count = 0
    
    # List to store all inference results
    all_results = []
    all_texts = []
    all_predictions = []

    for hw_key in data:  # e.g., "HW1"
        assignments = data[hw_key]
        print(f"Processing {hw_key}: {len(assignments)} assignments")
        
        for assignment in assignments:
            feedbacks = [r.get('Feedback', '') for r in assignment.get('Round', [])]
            predictions = batch_predict(
                model, 
                tokenizer, 
                device, 
                feedbacks,
                thresholds=thresholds_list,
                batch_size=32
            )
            
            # Collect all text and predictions for analysis
            all_texts.extend(feedbacks)
            all_predictions.extend(predictions)
            
            for round_entry, pred in zip(assignment.get('Round', []), predictions):
                # Update original data structure
                round_entry.update({
                    "Relevance": int(pred["relevance"]),
                    "Concreteness": int(pred["concreteness"]),
                    "Constructive": int(pred["constructive"])
                })
                
                # Collect detailed results for CSV
                result_record = {
                    "homework": hw_key,
                    "assignment_id": assignment.get('AssignmentID', ''),
                    "feedback": round_entry.get('Feedback', ''),
                    "relevance": int(pred["relevance"]),
                    "concreteness": int(pred["concreteness"]),
                    "constructive": int(pred["constructive"]),
                    "relevance_confidence": float(pred["relevance_confidence"]),
                    "concreteness_confidence": float(pred["concreteness_confidence"]),
                    "constructive_confidence": float(pred["constructive_confidence"])
                }
                all_results.append(result_record)
            
            processed_count += 1
            if processed_count % 50 == 0:
                print(f"Processed {processed_count}/{total_assignments} assignments")
    
    # Save original JSON results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Generate CSV file
    csv_output_path = output_path.replace('.json', '_detailed_results.csv')
    try:
        df = pd.DataFrame(all_results)
        df.to_csv(csv_output_path, index=False, encoding='utf-8-sig')
        print(f"Detailed results saved to CSV: {csv_output_path}")
    except NameError:
        print("Warning: pandas not installed, skipping CSV generation")
        # Manually generate CSV
        import csv
        with open(csv_output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            if all_results:
                fieldnames = all_results[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_results)
        print(f"Detailed results saved to CSV: {csv_output_path}")
    
    # Find detection error examples
    print("\n=== Finding suspicious detection results ===")
    uncertain_cases = find_uncertain_predictions(all_texts, all_predictions)
    
    # Output top 5 examples for each type
    for case_type, cases in uncertain_cases.items():
        print(f"\n--- {case_type.upper()} (Top 5 examples) ---")
        for i, case in enumerate(cases[:5]):
            print(f"{i+1}. Text: {case['text'][:100]}{'...' if len(case['text']) > 100 else ''}")
            pred = case['predictions']
            print(f"   Prediction: R={pred['relevance']}({pred['relevance_confidence']:.3f}), "
                  f"C={pred['concreteness']}({pred['concreteness_confidence']:.3f}), "
                  f"Co={pred['constructive']}({pred['constructive_confidence']:.3f})")
            
            if case_type == "low_confidence":
                print(f"   Lowest confidence score: {case['min_confidence']:.3f}")
            elif case_type == "conflicting_labels":
                print(f"   Confidence score range: {case['confidence_range']:.3f}")
            elif case_type == "keyword_override":
                print(f"   Original constructive confidence: {case['original_confidence']:.3f}")
            elif case_type == "high_confidence_negative":
                print(f"   {case['label_type']} high confidence negative prediction: {case['confidence']:.3f}")
            print()
        
        if len(cases) > 5:
            print(f"   ... {len(cases) - 5} more similar cases")
        print(f"Total {len(cases)} {case_type} cases")
    
    print(f"\nProcessing complete! Processed {processed_count} assignments")
    print(f"JSON results saved to: {output_path}")
    print(f"CSV detailed results saved to: {csv_output_path}")

def generate_error_analysis_report(all_texts, all_predictions, output_prefix="error_analysis"):
    """
    Generate detailed detection error analysis report
    """
    uncertain_cases = find_uncertain_predictions(all_texts, all_predictions)
    
    # Generate error analysis CSV
    error_analysis_data = []
    
    for case_type, cases in uncertain_cases.items():
        for case in cases:
            pred = case['predictions']
            record = {
                'error_type': case_type,
                'text': case['text'],
                'relevance': pred['relevance'],
                'concreteness': pred['concreteness'],
                'constructive': pred['constructive'],
                'relevance_confidence': pred['relevance_confidence'],
                'concreteness_confidence': pred['concreteness_confidence'],
                'constructive_confidence': pred['constructive_confidence'],
                'text_length': len(case['text']),
                'contains_suggestion': 'suggestion' in case['text'].lower() or '建議' in case['text']
            }
            
            # Add specific analysis fields
            if case_type == "low_confidence":
                record['min_confidence'] = case['min_confidence']
            elif case_type == "conflicting_labels":
                record['confidence_range'] = case['confidence_range']
            elif case_type == "keyword_override":
                record['original_constructive_confidence'] = case['original_confidence']
            elif case_type == "high_confidence_negative":
                record['negative_label_type'] = case['label_type']
                record['negative_confidence'] = case['confidence']
            
            error_analysis_data.append(record)
    
    # Save error analysis CSV
    error_csv_path = f"{output_prefix}_error_cases.csv"
    try:
        df_errors = pd.DataFrame(error_analysis_data)
        df_errors.to_csv(error_csv_path, index=False, encoding='utf-8-sig')
        print(f"Error analysis report saved to: {error_csv_path}")
    except NameError:
        # Manually generate CSV
        import csv
        if error_analysis_data:
            with open(error_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = error_analysis_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(error_analysis_data)
            print(f"Error analysis report saved to: {error_csv_path}")
    
    # Generate statistics summary
    summary_path = f"{output_prefix}_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=== Detection Error Analysis Summary ===\n\n")
        
        total_predictions = len(all_predictions)
        f.write(f"Total predictions: {total_predictions}\n\n")
        
        for case_type, cases in uncertain_cases.items():
            f.write(f"{case_type.upper()}: {len(cases)} 個案例 ({len(cases)/total_predictions*100:.1f}%)\n")
            
            if cases:
                f.write("Examples:\n")
                for i, case in enumerate(cases[:3]):  # Top 3 examples
                    pred = case['predictions']
                    f.write(f"{i+1}. {case['text'][:80]}{'...' if len(case['text']) > 80 else ''}\n")
                    f.write(f"   R={pred['relevance']}({pred['relevance_confidence']:.3f}), "
                           f"C={pred['concreteness']}({pred['concreteness_confidence']:.3f}), "
                           f"Co={pred['constructive']}({pred['constructive_confidence']:.3f})\n")
                f.write("\n")
        
        # Overall statistics
        all_confidences = []
        for pred in all_predictions:
            all_confidences.extend([
                pred['relevance_confidence'],
                pred['concreteness_confidence'], 
                pred['constructive_confidence']
            ])
        
        avg_confidence = sum(all_confidences) / len(all_confidences)
        low_confidence_count = sum(1 for c in all_confidences if c < 0.6)
        
        f.write(f"Average confidence score: {avg_confidence:.3f}\n")
        f.write(f"Low confidence score (<0.6) ratio: {low_confidence_count}/{len(all_confidences)} ({low_confidence_count/len(all_confidences)*100:.1f}%)\n")
    
    print(f"Statistics summary saved to: {summary_path}")
    return uncertain_cases

if __name__ == "__main__":
    input_json = "../utils/processed_data/selected_assignments_addscore.json"
    output_json = "3labeled_processed_totalData11.json"
    model_path = "../models/3label_finetuned_model"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print("=== Starting inference and analysis ===")
    process_json_with_predictions(input_json, output_json, model_path, device)
    
    print("\n=== Generating detailed error analysis report ===")
    # Reload results for detailed analysis
    try:
        # For more detailed error analysis, can reload data
        print("Error analysis completed during main processing")
        print("Please check the generated CSV file and terminal output for error examples")
    except Exception as e:
        print(f"Error occurred during error analysis generation: {e}")
    
    print("\n=== Execution complete ===")
    print("Generated files:")
    print("1. JSON result file (with label predictions)")
    print("2. CSV detailed result file (with confidence scores)")
    print("3. Error detection examples in terminal output")
