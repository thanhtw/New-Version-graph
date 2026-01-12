#!/usr/bin/env python3
"""
CSV to JSON Converter
Converts data64_inference.csv format to 1111test_64_addscore.json format

CSV columns: Owner_name, Reviewer_name, feedback, Time, Assignment, Metrics, PMetric, Round
JSON fields: Author_ID, Reviewer_ID, Author_Name, Reviewer_Name, Feedback, Score, Label, Time, Assignment, Metrics, Category, Round
"""

import csv
import json
import os
from typing import Dict, List, Any

def create_id_mapping(names: List[str]) -> Dict[str, int]:
    """
    Create a mapping from unique names to sequential IDs.
    
    Args:
        names: List of names to map
        
    Returns:
        Dictionary mapping name to ID
    """
    # Filter out None values and empty strings
    valid_names = [name for name in names if name and name.strip()]
    unique_names = sorted(set(valid_names))
    return {name: idx + 1 for idx, name in enumerate(unique_names)}

def calculate_score(feedback: str) -> int:
    """
    Calculate score based on feedback content.
    Score is based on the length and complexity of the feedback.
    
    Args:
        feedback: The feedback text
        
    Returns:
        Score value (1 or 2)
    """
    if not feedback or feedback.strip() == '':
        return 0
    # If feedback has more content (longer than simple yes/no), give score 2
    if len(feedback.strip()) > 5:
        return 2
    return 1

def calculate_label(feedback: str) -> int:
    """
    Calculate label based on feedback content.
    Label indicates if the feedback is meaningful (1) or not (0).
    
    Args:
        feedback: The feedback text
        
    Returns:
        Label value (0 or 1)
    """
    if not feedback or feedback.strip() == '':
        return 0
    # Simple feedback like single characters or very short responses get label 0
    simple_responses = ['是', '否', '有', '無', '可', '好', '0', '1', '?']
    if feedback.strip() in simple_responses:
        return 0
    # Longer, more meaningful feedback gets label 1
    if len(feedback.strip()) > 3:
        return 1
    return 0

def convert_csv_to_json(csv_path: str, json_path: str) -> None:
    """
    Convert CSV file to JSON format.
    
    Args:
        csv_path: Path to input CSV file
        json_path: Path to output JSON file
    """
    records = []
    all_authors = []
    all_reviewers = []
    
    # First pass: read all data and collect unique names
    print(f"Reading CSV file: {csv_path}")
    with open(csv_path, 'r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        
    print(f"Found {len(rows)} rows in CSV")
    
    # Collect all unique author and reviewer names
    for row in rows:
        author = row.get('Owner_name', '')
        reviewer = row.get('Reviewer_name', '')
        if author and author.strip():
            all_authors.append(author)
        if reviewer and reviewer.strip():
            all_reviewers.append(reviewer)
    
    # Create ID mappings
    author_id_map = create_id_mapping(all_authors)
    reviewer_id_map = create_id_mapping(all_reviewers)
    
    print(f"Found {len(author_id_map)} unique authors")
    print(f"Found {len(reviewer_id_map)} unique reviewers")
    
    # Second pass: convert each row to JSON record
    for row in rows:
        author_name = row.get('Owner_name', '') or ''
        reviewer_name = row.get('Reviewer_name', '') or ''
        
        # Skip rows with missing author or reviewer
        if not author_name.strip() or not reviewer_name.strip():
            continue
            
        feedback = row.get('feedback', '') or ''
        
        # Handle empty feedback
        if feedback == '':
            feedback_text = ''
        else:
            feedback_text = feedback
        
        # Get numeric fields with default values
        metrics_str = row.get('Metrics', '') or '0'
        pmetric_str = row.get('PMetric', '') or '0'
        round_str = row.get('Round', '') or '1'
        
        try:
            metrics = int(metrics_str)
        except (ValueError, TypeError):
            metrics = 0
            
        try:
            category = int(pmetric_str)
        except (ValueError, TypeError):
            category = 0
            
        try:
            round_num = int(round_str)
        except (ValueError, TypeError):
            round_num = 1
        
        record = {
            "Author_ID": author_id_map[author_name],
            "Reviewer_ID": reviewer_id_map[reviewer_name],
            "Author_Name": author_name,
            "Reviewer_Name": reviewer_name,
            "Feedback": feedback_text,
            "Score": calculate_score(feedback_text),
            "Label": calculate_label(feedback_text),
            "Time": row.get('Time', '') or '',
            "Assignment": row.get('Assignment', '') or '',
            "Metrics": metrics,
            "Category": category,
            "Round": round_num
        }
        records.append(record)
    
    # Write JSON output
    print(f"Writing JSON file: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(records, json_file, ensure_ascii=False, indent='\t')
    
    print(f"Successfully converted {len(records)} records")
    print(f"Output saved to: {json_path}")

def main():
    """Main function to run the conversion."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert CSV to JSON format')
    parser.add_argument('--input', '-i', type=str, default='data64_inference.csv',
                        help='Input CSV file path (default: data64_inference.csv)')
    parser.add_argument('--output', '-o', type=str, default='22data64_inference_converted.json',
                        help='Output JSON file path (default: data64_inference_converted.json)')
    args = parser.parse_args()
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define input and output paths (use absolute paths if provided, else relative to script dir)
    csv_path = args.input if os.path.isabs(args.input) else os.path.join(script_dir, args.input)
    json_path = args.output if os.path.isabs(args.output) else os.path.join(script_dir, args.output)
    
    # Check if input file exists
    if not os.path.exists(csv_path):
        print(f"Error: Input file not found: {csv_path}")
        return
    
    # Run conversion
    convert_csv_to_json(csv_path, json_path)

if __name__ == '__main__':
    main()
