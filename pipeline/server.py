#!/usr/bin/env python3
"""
Pipeline Server for Review Graph Visualization
Provides HTTP API for uploading CSV files, running the pipeline, and serving visualization.
"""

import os
import sys
import json
import cgi
import time
import shutil
import traceback
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading

# Pipeline modules
from csv_converter import convert_csv_to_json
from data_organizer import organize_json_file
from ml_inference import run_inference_simple, run_inference_with_model

# Paths
PIPELINE_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = PIPELINE_DIR.parent
UPLOAD_DIR = PIPELINE_DIR / "uploads"
OUTPUT_DIR = PIPELINE_DIR / "output"
STATIC_DIR = PIPELINE_DIR / "static"  # Use local static folder
MODEL_PATH = PROJECT_ROOT / "models" / "bert_3label_finetuned_model"

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Pipeline status tracking
pipeline_status = {
    "running": False,
    "step": 0,
    "message": "Ready",
    "error": None,
    "result": None
}


class PipelineHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler for Pipeline Server."""
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/' or path == '/index.html':
            self.serve_index()
        elif path == '/graph' or path == '/graph.html':
            self.serve_graph()
        elif path == '/correlation' or path == '/score_review_correlation.html':
            self.serve_correlation()
        elif path == '/api/run-analysis':
            self.run_score_analysis()
        elif path == '/status':
            self.serve_status()
        elif path == '/result':
            self.serve_result()
        elif path.startswith('/static/'):
            self.serve_static_file(path[8:])
        elif path.startswith('../static/'):
            # Handle relative path from graph.html
            self.serve_static_file(path[10:])
        elif path.startswith('/function/'):
            self.serve_function_file(path[10:])
        elif path.startswith('/output/'):
            self.serve_output_file(path[8:])
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/upload':
            self.handle_upload()
        elif path == '/run':
            self.handle_run_pipeline()
        else:
            self.send_error(404, "Not Found")
    
    def serve_index(self):
        """Serve the main HTML page."""
        html_path = PIPELINE_DIR / "index.html"
        if html_path.exists():
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "index.html not found")
    
    def serve_graph(self):
        """Serve the graph visualization page."""
        html_path = PIPELINE_DIR / "graph.html"
        if html_path.exists():
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "graph.html not found")
    
    def serve_correlation(self):
        """Serve the score-review correlation analysis page."""
        html_path = PIPELINE_DIR / "score_review_correlation.html"
        if html_path.exists():
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "score_review_correlation.html not found")
    
    def run_score_analysis(self):
        """Run score-review correlation analysis and return results."""
        try:
            from score_review_analysis import generate_analysis_report
            report = generate_analysis_report()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(report, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
    
    def serve_status(self):
        """Serve pipeline status as JSON."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(pipeline_status).encode('utf-8'))
    
    def serve_result(self):
        """Serve the final result JSON."""
        result_path = OUTPUT_DIR / "final_result.json"
        if result_path.exists():
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(result_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "Result not found. Please run pipeline first.")
    
    def serve_static_file(self, filename):
        """Serve files from static directory."""
        file_path = STATIC_DIR / filename
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            
            # Set content type
            if filename.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif filename.endswith('.js'):
                content_type = 'application/javascript; charset=utf-8'
            elif filename.endswith('.css'):
                content_type = 'text/css; charset=utf-8'
            elif filename.endswith('.json'):
                content_type = 'application/json; charset=utf-8'
            else:
                content_type = 'application/octet-stream'
            
            self.send_header('Content-type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, f"File not found: {filename}")
    
    def serve_function_file(self, filename):
        """Serve files from function directory."""
        function_dir = PROJECT_ROOT / "function"
        file_path = function_dir / filename
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, f"Function file not found: {filename}")
    
    def serve_output_file(self, filename):
        """Serve files from output directory."""
        file_path = OUTPUT_DIR / filename
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, f"Output file not found: {filename}")
    
    def handle_upload(self):
        """Handle CSV file upload."""
        try:
            content_type = self.headers.get('Content-Type', '')
            
            if 'multipart/form-data' in content_type:
                # Parse multipart form data
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={
                        'REQUEST_METHOD': 'POST',
                        'CONTENT_TYPE': content_type
                    }
                )
                
                if 'file' in form:
                    file_item = form['file']
                    if file_item.filename:
                        # Save uploaded file
                        filename = os.path.basename(file_item.filename)
                        if not filename.endswith('.csv'):
                            filename += '.csv'
                        
                        upload_path = UPLOAD_DIR / filename
                        with open(upload_path, 'wb') as f:
                            f.write(file_item.file.read())
                        
                        # Send success response
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response = {
                            "success": True,
                            "filename": filename,
                            "path": str(upload_path)
                        }
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                        return
            
            self.send_error(400, "Invalid file upload")
            
        except Exception as e:
            self.send_error(500, f"Upload error: {str(e)}")
    
    def handle_run_pipeline(self):
        """Handle pipeline execution request."""
        global pipeline_status
        
        if pipeline_status["running"]:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": "Pipeline is already running"
            }).encode('utf-8'))
            return
        
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            params = json.loads(body) if body else {}
            
            filename = params.get('filename', '')
            use_ml = params.get('use_ml', False)
            hw_start = params.get('hw_start', 1)
            hw_end = params.get('hw_end', 7)
            
            if not filename:
                # Find most recent upload
                uploads = list(UPLOAD_DIR.glob('*.csv'))
                if uploads:
                    filename = uploads[-1].name
                else:
                    self.send_error(400, "No CSV file uploaded")
                    return
            
            # Start pipeline in background thread
            thread = threading.Thread(
                target=run_pipeline_async,
                args=(filename, use_ml, hw_start, hw_end)
            )
            thread.start()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "message": "Pipeline started"
            }).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error starting pipeline: {str(e)}")
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_pipeline_async(filename: str, use_ml: bool, hw_start: int, hw_end: int):
    """Run the pipeline asynchronously."""
    global pipeline_status
    
    pipeline_status = {
        "running": True,
        "step": 0,
        "message": "Starting pipeline...",
        "error": None,
        "result": None
    }
    
    try:
        csv_path = UPLOAD_DIR / filename
        json_converted_path = OUTPUT_DIR / "step1_converted.json"
        json_organized_path = OUTPUT_DIR / "step2_organized.json"
        json_final_path = OUTPUT_DIR / "final_result.json"
        
        # Step 1: CSV to JSON
        pipeline_status["step"] = 1
        pipeline_status["message"] = "Step 1: Converting CSV to JSON..."
        print(f"\n{'='*50}")
        print("Step 1: CSV to JSON Conversion")
        print(f"{'='*50}")
        
        step1_stats = convert_csv_to_json(str(csv_path), str(json_converted_path))
        
        # Step 2: Organize Data
        pipeline_status["step"] = 2
        pipeline_status["message"] = "Step 2: Organizing data..."
        print(f"\n{'='*50}")
        print("Step 2: Data Organization")
        print(f"{'='*50}")
        
        step2_stats = organize_json_file(
            str(json_converted_path), 
            str(json_organized_path),
            hw_start, 
            hw_end
        )
        
        # Step 3: ML Inference
        pipeline_status["step"] = 3
        pipeline_status["message"] = "Step 3: Running ML inference..."
        print(f"\n{'='*50}")
        print("Step 3: ML Inference")
        print(f"{'='*50}")
        
        if use_ml and MODEL_PATH.exists():
            step3_stats = run_inference_with_model(
                str(json_organized_path),
                str(json_final_path),
                str(MODEL_PATH)
            )
        else:
            step3_stats = run_inference_simple(
                str(json_organized_path),
                str(json_final_path)
            )
        
        # Step 4: Score-Review Correlation Analysis
        pipeline_status["step"] = 4
        pipeline_status["message"] = "Step 4: Running score-review correlation analysis..."
        print(f"\n{'='*50}")
        print("Step 4: Score-Review Correlation Analysis")
        print(f"{'='*50}")
        
        step4_stats = None
        try:
            from score_review_analysis import generate_analysis_report
            analysis_report = generate_analysis_report()
            if analysis_report and 'error' not in analysis_report:
                step4_stats = {
                    "total_students": analysis_report.get('summary', {}).get('total_students', 0),
                    "total_reviews": analysis_report.get('summary', {}).get('total_reviews_given', 0),
                    "analysis_file": str(OUTPUT_DIR / "score_review_analysis.json")
                }
                print(f"Analysis completed: {step4_stats['total_students']} students, {step4_stats['total_reviews']} reviews")
            else:
                print("Score analysis skipped (no score data or error)")
        except Exception as e:
            print(f"Score-review analysis skipped: {e}")
       
        # Complete
        pipeline_status["step"] = 5
        pipeline_status["message"] = "Pipeline completed successfully!"
        pipeline_status["running"] = False
        pipeline_status["result"] = {
            "step1": step1_stats,
            "step2": step2_stats,
            "step3": step3_stats,
            "step4": step4_stats,
            "output_file": str(json_final_path)
        }
        
        print(f"\n{'='*50}")
        print("Pipeline Complete!")
        print(f"{'='*50}")
        print(f"Output: {json_final_path}")
        
    except Exception as e:
        pipeline_status["running"] = False
        pipeline_status["error"] = str(e)
        pipeline_status["message"] = f"Error: {str(e)}"
        print(f"\nPipeline Error: {e}")
        traceback.print_exc()


def start_server(port: int = 8002):
    """Start the pipeline server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, PipelineHandler)
    
    print(f"\n{'='*60}")
    print("  Review Graph Visualization - Pipeline Server")
    print(f"{'='*60}")
    print(f"\n  Server running at: http://localhost:{port}")
    print(f"  Upload page:       http://localhost:{port}/")
    print(f"  View graph:        http://localhost:{port}/graph")
    print(f"\n  Press Ctrl+C to stop the server")
    print(f"{'='*60}\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.shutdown()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8002
    start_server(port)
