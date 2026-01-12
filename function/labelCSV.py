from inference import load_model, predict_with_threshold
import torch
import pandas as pd
from tqdm import tqdm  # Progress bar

def main():
    # Model initialization
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_path = "../models/roberta-smote-10fold-chinese_iteration_3"
    model, tokenizer = load_model(model_path, device)

    data_path = "../data/homework/1131_rr.csv"
    df = pd.read_csv(data_path, on_bad_lines="skip")
    print(df.head())

    if 'feedback' not in df.columns:
        raise ValueError("Data is missing 'feedback' column!")

    required_features = {'id', 'feedback'}
    if not required_features.issubset(df.columns):
        raise ValueError(f"Missing columns {required_features - set(df.columns)}")

    # Handle NaN (set empty values to "" for inference)
    df['feedback'] = df['feedback'].fillna("").astype(str)

    # Add tqdm progress bar
    print("Starting inference...")
    batch_size = 32  # Use batch processing to avoid OOM
    predictions = []
    confidences = []

    for i in tqdm(range(0, len(df), batch_size), desc="Inferring"):
        batch_feedbacks = df['feedback'].iloc[i:i+batch_size].tolist()
        batch_preds, batch_confs = predict_with_threshold(
            model, tokenizer, device, {"texts": batch_feedbacks}, threshold=0.8
        )
        predictions.extend(batch_preds)
        confidences.extend(batch_confs)

    # Save back
    df['prediction'] = predictions
    df['confidence'] = confidences
    output_path = "../data/homework/1131_Labelrr.csv"
    df[['id', 'feedback', 'prediction', 'confidence']].to_csv(output_path, index=False)
    
    print(f"Inference results saved to {output_path}")

if __name__ == "__main__":
    main()