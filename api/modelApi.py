import os
from transformers import BertForSequenceClassification, BertTokenizer
from flask import Flask, request, jsonify

# Flask application initialization
app = Flask(__name__)

# Model path - use current script directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(BASE_DIR, "models", "saved_model")
# Load saved model and tokenizer
try:
    model = BertForSequenceClassification.from_pretrained(model_path)
    tokenizer = BertTokenizer.from_pretrained(model_path)
    model.eval()  # Set to inference mode
    print("Model loaded successfully, switched to inference mode!")
except Exception as e:
    print(f"Model loading failed: {e}")
    raise
 
# Flask API route logic
@app.route("/")
def index():
    return "Model initialized, ready for inference requests!" 
                                                                                                                                                                            
if __name__ == "__main__":
    app.run(debug=True, port=5001)