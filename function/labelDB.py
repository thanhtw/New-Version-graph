import pymysql
import mysql.connector
import pandas as pd
import torch
from inference import load_model, predict_with_threshold
from mysql.connector import Error

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_path = "../models/roberta-smote-10fold-chinese_iteration_3"
model, tokenizer = load_model(model_path, device)

def db_connection():
    try:
        connection = mysql.connector.connect(
            host="140.134.25.64",  # Replace with your MySQL hostname or IP address
            port=33541,            # Replace with your MySQL port number
            user="root",           # Replace with your MySQL username
            password="Asdfghjk3839",  # Replace with your MySQL password
            database="ProgEdu64"   # Replace with the database you want to connect to
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def read_feedback():
    connection = db_connection()
    feedbacks = []
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT feedback FROM Review_Record;")
        feedbacks = [row[0] for row in cursor.fetchall()]
        print(f"Successfully read {len(feedbacks)} feedback records")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
    return feedbacks

# Prediction function
def predict_feedback(feedbacks, batch_size=64):
    predictions = []

    # Encode each feedback and send to model
    predictions = []
    for i in range(0, len(feedbacks), batch_size):
        batch_feedbacks = feedbacks[i:i+batch_size]
        
        # Tokenize batch
        inputs = tokenizer(
            batch_feedbacks,
            padding="max_length",
            truncation=True,
            max_length=128,  # Adjust to model's max length
            return_tensors="pt"  # Return PyTorch tensors
        )
        
        # Model inference
        model.eval()
        with torch.no_grad():
            outputs = model(**inputs)

        # Batch classification results
        logits = outputs.logits
        batch_predictions = torch.argmax(logits, dim=1).tolist()
        predictions.extend(zip(batch_feedbacks, batch_predictions))
        
        # Log: track progress
        print(f"Processed {i+len(batch_feedbacks)}/{len(feedbacks)} records")
    
    return predictions

# Write label results to database
def write_predictions_to_db(predictions):
    connection = db_connection()
    try:
        cursor = connection.cursor()
        
        # Ensure Review_Record table has predicted_label column
        cursor.execute("SHOW COLUMNS FROM Review_Record LIKE 'predicted_label';")
        result = cursor.fetchone()

        # If column doesn't exist, add it
        if result is None:
            cursor.execute("ALTER TABLE Review_Record ADD COLUMN predicted_label INT;")
            print("Successfully added predicted_label column.")
        
        # Update prediction results in database
        for feedback, predicted_label in predictions:
            cursor.execute("""
                UPDATE Review_Record 
                SET predicted_label = %s 
                WHERE feedback = %s
            """, (predicted_label, feedback))
        
        connection.commit()
        print(f"Successfully wrote prediction results to database!")
    
    except mysql.connector.Error as e:
        print(f"Error writing to database: {e}")
    finally:
        cursor.close()
        connection.close()
        print("Database connection closed.")

if __name__ == "__main__":
    # 1. Read database data
    feedbacks = read_feedback()

    # 2. Use model for classification
    results = predict_feedback(feedbacks)

    # 3. Choose to output or write to database
    print("Inference results (first 5):")
    for feedback, label in results[:5]:  # Only output first 5
        print(f"Feedback: {feedback}\nPredicted Label: {label}\n")

    # If needed, write results to database
    write_predictions_to_db(results)