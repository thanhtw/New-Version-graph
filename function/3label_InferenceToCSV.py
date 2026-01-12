from inference import load_model, batch_predict
import torch
import pandas as pd
from tqdm import tqdm  # Progress bar

def main():
    # Model initialization
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_path = "../models/3label_finetuned_model"
    model, tokenizer = load_model(model_path, device)

    data_path = "../data/homework/1131_rr.csv"
    df = pd.read_csv(data_path, on_bad_lines="skip")
    print(df.head())

    label_names = ["relevance", "concreteness", "constructive"]


    if 'feedback' not in df.columns:
        raise ValueError("Data is missing 'feedback' column!")

    required_features = {'id', 'feedback'}
    if not required_features.issubset(df.columns):
        raise ValueError(f"Missing columns {required_features - set(df.columns)}")

    # Handle NaN (set empty values to "" for inference)
    df['feedback'] = df['feedback'].fillna("").astype(str)

    # Add tqdm progress bar
    print("Starting inference...")
    print("Note: If review contains 'suggestion' keyword, constructive label will be automatically set to 1")
    
    batch_size = 32  # Use batch processing to avoid OOM
    all_predictions = []
    
    # Threshold settings
    thresholds = [0.5, 0.5, 0.7]  # relevance, concreteness, constructive
    
    for i in tqdm(range(0, len(df), batch_size), desc="Inferring"):
        batch_feedbacks = df['feedback'].iloc[i:i+batch_size].tolist()
        
        # Use new batch_predict function
        batch_results = batch_predict(
            model, tokenizer, device, batch_feedbacks, thresholds, batch_size
        )
        all_predictions.extend(batch_results)

    # Convert prediction results to DataFrame columns
    for label in label_names:
        df[label] = [pred[label] for pred in all_predictions]


    output_path = "../data/homework/1131_3Labelrr11.csv"
    
    # Output columns: id, feedback, three label columns
    cols = ['id', 'feedback'] + label_names
    df_out = df[cols]
    df_out.to_csv(output_path, index=False)
    
    # Statistics results
    total_feedbacks = len(df)
    total_with_suggestion = sum(1 for feedback in df['feedback'] if '建議' in str(feedback))
    
    print(f"Inference results saved to {output_path}")
    print(f"Total processed {total_feedbacks} reviews")
    print(f"Reviews containing 'suggestion' keyword: {total_with_suggestion}")
    
    # Display label statistics
    for label in label_names:
        count = df[label].sum()
        percentage = (count / total_feedbacks) * 100
        print(f"{label}: {count} ({percentage:.1f}%)")

if __name__ == "__main__":
    main()