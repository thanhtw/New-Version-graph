#!/usr/bin/env python3
"""
ML Inference Module for Review Data Pipeline
Adds 3-label predictions (Relevance, Concreteness, Constructive) to review data.
"""

import json
import sys
import os
from pathlib import Path

# Add parent directory to path for model imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_inference_simple(input_path: str, output_path: str) -> dict:
    """
    Run inference without ML model (placeholder labels).
    Use this when ML model is not available.
    
    Returns:
        dict with inference statistics
    """
    print(f"Reading input file: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_feedbacks = 0
    
    for hw_key in data:
        assignments = data[hw_key]
        print(f"Processing {hw_key}: {len(assignments)} assignments")
        
        for assignment in assignments:
            for round_entry in assignment.get('Round', []):
                feedback = round_entry.get('Feedback', '')
                
                # Simple rule-based labeling (placeholder)
                has_content = len(feedback.strip()) > 5
                is_specific = len(feedback.strip()) > 20
                has_suggestion = any(kw in feedback.lower() for kw in ['建議', 'suggestion', '可以', 'should', 'could'])
                
                round_entry['Relevance'] = 1 if has_content else 0
                round_entry['Concreteness'] = 1 if is_specific else 0
                round_entry['Constructive'] = 1 if has_suggestion else 0
                
                total_feedbacks += 1
    
    print(f"Writing output file: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    stats = {
        "total_feedbacks": total_feedbacks,
        "homework_count": len(data),
        "model_used": "rule-based"
    }
    
    print(f"Processed {total_feedbacks} feedbacks")
    return stats


def run_inference_with_model(input_path: str, output_path: str, model_path: str) -> dict:
    """
    Run inference with BERT ML model.
    
    Returns:
        dict with inference statistics
    """
    try:
        import torch
        from function.inference import load_model, batch_predict
    except ImportError as e:
        print(f"Warning: Could not import ML modules: {e}")
        print("Falling back to rule-based inference...")
        return run_inference_simple(input_path, output_path)
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"Warning: Model not found at {model_path}")
        print("Falling back to rule-based inference...")
        return run_inference_simple(input_path, output_path)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    print(f"Loading model from: {model_path}")
    model, tokenizer = load_model(model_path, device)
    
    # Thresholds for label prediction
    thresholds = [0.5, 0.5, 0.7]  # relevance, concreteness, constructive
    
    print(f"Reading input file: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_feedbacks = 0
    
    for hw_key in data:
        assignments = data[hw_key]
        print(f"Processing {hw_key}: {len(assignments)} assignments")
        
        for assignment in assignments:
            feedbacks = [r.get('Feedback', '') for r in assignment.get('Round', [])]
            
            predictions = batch_predict(
                model, tokenizer, device, feedbacks,
                thresholds=thresholds,
                batch_size=32
            )
            
            for round_entry, pred in zip(assignment.get('Round', []), predictions):
                round_entry['Relevance'] = int(pred['relevance'])
                round_entry['Concreteness'] = int(pred['concreteness'])
                round_entry['Constructive'] = int(pred['constructive'])
                total_feedbacks += 1
    
    print(f"Writing output file: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    stats = {
        "total_feedbacks": total_feedbacks,
        "homework_count": len(data),
        "model_used": "bert-3label"
    }
    
    print(f"Processed {total_feedbacks} feedbacks with ML model")
    return stats


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        model_path = sys.argv[3] if len(sys.argv) > 3 else "../models/bert_3label_finetuned_model"
        run_inference_with_model(sys.argv[1], sys.argv[2], model_path)
    else:
        print("Usage: python ml_inference.py <input.json> <output.json> [model_path]")
