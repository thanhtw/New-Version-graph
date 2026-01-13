#!/usr/bin/env python3
"""
Pipeline Server for Review Graph Visualization
Provides HTTP API for uploading CSV files, running the pipeline, and serving visualization.
Multi-user support with login authentication and separate directories per user.
"""

import os
import sys
import json
import cgi
import time
import shutil
import traceback
import socket
import socketserver
import uuid
import hashlib
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from http.cookies import SimpleCookie
import threading

# Pipeline modules
from csv_converter import convert_csv_to_json
from data_organizer import organize_json_file
from ml_inference import run_inference_simple, run_inference_with_model

# Paths
PIPELINE_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = PIPELINE_DIR.parent
BASE_UPLOAD_DIR = PIPELINE_DIR / "uploads"
BASE_OUTPUT_DIR = PIPELINE_DIR / "output"
STATIC_DIR = PIPELINE_DIR / "static"
MODEL_PATH = PROJECT_ROOT / "models" / "bert_3label_finetuned_model"
USERS_FILE = PIPELINE_DIR / "users.json"

# Ensure directories exist
BASE_UPLOAD_DIR.mkdir(exist_ok=True)
BASE_OUTPUT_DIR.mkdir(exist_ok=True)

# Session management
sessions = {}  # token -> user_info
SESSION_TIMEOUT = 86400  # 24 hours

# Per-user pipeline status
user_pipeline_status = {}  # user_id -> status


def load_users():
    """Load users from JSON file."""
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('users', [])
    return []


def save_users(users):
    """Save users to JSON file."""
    with open(USERS_FILE, 'w') as f:
        json.dump({"users": users}, f, indent=2)


def authenticate_user(username: str, password: str):
    """Authenticate user and return user info if valid."""
    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            return user
    return None


def create_session(user: dict) -> str:
    """Create a new session for user and return token."""
    token = str(uuid.uuid4())
    sessions[token] = {
        "user": user,
        "created_at": time.time()
    }
    return token


def get_session(token: str):
    """Get session by token, return None if invalid or expired."""
    if token in sessions:
        session = sessions[token]
        if time.time() - session['created_at'] < SESSION_TIMEOUT:
            return session
        else:
            del sessions[token]
    return None


def get_user_dirs(user_id: str):
    """Get or create user-specific directories."""
    upload_dir = BASE_UPLOAD_DIR / user_id
    output_dir = BASE_OUTPUT_DIR / user_id
    upload_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    return upload_dir, output_dir


def get_pipeline_status(user_id: str):
    """Get pipeline status for specific user."""
    if user_id not in user_pipeline_status:
        user_pipeline_status[user_id] = {
            "running": False,
            "step": 0,
            "message": "Ready",
            "error": None,
            "result": None
        }
    return user_pipeline_status[user_id]


class PipelineHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler for Pipeline Server with user authentication."""
    
    timeout = 30
    
    def handle(self):
        """Handle with timeout protection."""
        try:
            super().handle()
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Connection error: {e}")
    
    def get_session_token(self):
        """Get session token from cookies."""
        cookie_header = self.headers.get('Cookie', '')
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        if 'session' in cookie:
            return cookie['session'].value
        return None
    
    def get_current_user(self):
        """Get current logged-in user from session."""
        token = self.get_session_token()
        if token:
            session = get_session(token)
            if session:
                return session['user']
        return None
    
    def require_auth(self):
        """Check if user is authenticated, redirect to login if not."""
        user = self.get_current_user()
        if not user:
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return None
        return user
    
    def send_json_response(self, data: dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Public routes (no auth required)
        if path == '/login' or path == '/login.html':
            self.serve_login()
            return
        
        # API routes
        if path == '/api/check-session':
            self.handle_check_session()
            return
        
        if path == '/api/logout':
            self.handle_logout()
            return
        
        # Protected routes (auth required)
        user = self.get_current_user()
        if not user:
            # For API calls, return JSON error
            if path.startswith('/api/') or path in ['/status', '/result']:
                self.send_json_response({"error": "Not authenticated"}, 401)
                return
            # For page requests, redirect to login
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return
        
        # Authenticated routes
        if path == '/' or path == '/index.html':
            self.serve_index()
        elif path == '/graph' or path == '/graph.html':
            self.serve_graph()
        elif path == '/correlation' or path == '/score_review_correlation.html':
            self.serve_correlation()
        elif path == '/api/run-analysis':
            self.run_score_analysis(user)
        elif path == '/api/user-info':
            self.send_json_response({"user": user})
        elif path == '/status':
            self.serve_status(user)
        elif path == '/result':
            self.serve_result(user)
        elif path.startswith('/static/'):
            self.serve_static_file(path[8:])
        elif path.startswith('../static/'):
            self.serve_static_file(path[10:])
        elif path.startswith('/function/'):
            self.serve_function_file(path[10:])
        elif path.startswith('/output/'):
            self.serve_output_file(path[8:], user)
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Login doesn't require auth
        if path == '/api/login':
            self.handle_login()
            return
        
        # All other POST routes require auth
        user = self.get_current_user()
        if not user:
            self.send_json_response({"error": "Not authenticated"}, 401)
            return
        
        if path == '/upload':
            self.handle_upload(user)
        elif path == '/run':
            self.handle_run_pipeline(user)
        else:
            self.send_error(404, "Not Found")
    
    def serve_login(self):
        """Serve the login page."""
        html_path = PIPELINE_DIR / "login.html"
        if html_path.exists():
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "login.html not found")
    
    def handle_login(self):
        """Handle login POST request."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
            
            username = data.get('username', '')
            password = data.get('password', '')
            
            user = authenticate_user(username, password)
            if user:
                token = create_session(user)
                
                # Create user directories
                get_user_dirs(user['id'])
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Set-Cookie', f'session={token}; Path=/; HttpOnly; Max-Age={SESSION_TIMEOUT}')
                self.end_headers()
                
                response = {
                    "success": True,
                    "user": {
                        "id": user['id'],
                        "username": user['username'],
                        "name": user['name'],
                        "role": user.get('role', 'user')
                    }
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
            else:
                self.send_json_response({
                    "success": False,
                    "message": "Invalid username or password"
                }, 401)
                
        except Exception as e:
            self.send_json_response({"success": False, "message": str(e)}, 500)
    
    def handle_logout(self):
        """Handle logout request."""
        token = self.get_session_token()
        if token and token in sessions:
            del sessions[token]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Set-Cookie', 'session=; Path=/; Max-Age=0')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
    
    def handle_check_session(self):
        """Check if session is valid."""
        user = self.get_current_user()
        if user:
            self.send_json_response({
                "logged_in": True,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "name": user['name'],
                    "role": user.get('role', 'user')
                }
            })
        else:
            self.send_json_response({"logged_in": False})
    
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
    
    def run_score_analysis(self, user: dict):
        """Run score-review correlation analysis and return results."""
        try:
            from score_review_analysis import generate_analysis_report
            
            # Get user output directory
            _, output_dir = get_user_dirs(user['id'])
            report = generate_analysis_report(str(output_dir / "final_result.json"))
            
            self.send_json_response(report)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)
    
    def serve_status(self, user: dict):
        """Serve pipeline status as JSON for specific user."""
        status = get_pipeline_status(user['id'])
        self.send_json_response(status)
    
    def serve_result(self, user: dict):
        """Serve the final result JSON for specific user."""
        _, output_dir = get_user_dirs(user['id'])
        result_path = output_dir / "final_result.json"
        
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
            self.send_header('Cache-Control', 'public, max-age=3600')
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
            self.send_header('Cache-Control', 'public, max-age=300')
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, f"Function file not found: {filename}")
    
    def serve_output_file(self, filename, user: dict):
        """Serve files from user's output directory."""
        _, output_dir = get_user_dirs(user['id'])
        file_path = output_dir / filename
        
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'public, max-age=60')
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, f"Output file not found: {filename}")
    
    def handle_upload(self, user: dict):
        """Handle CSV file upload for specific user."""
        try:
            content_type = self.headers.get('Content-Type', '')
            
            if 'multipart/form-data' in content_type:
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
                        # Get user upload directory
                        upload_dir, _ = get_user_dirs(user['id'])
                        
                        # Save uploaded file
                        filename = os.path.basename(file_item.filename)
                        if not filename.endswith('.csv'):
                            filename += '.csv'
                        
                        upload_path = upload_dir / filename
                        with open(upload_path, 'wb') as f:
                            f.write(file_item.file.read())
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response = {
                            "success": True,
                            "filename": filename,
                            "path": str(upload_path),
                            "user_id": user['id']
                        }
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                        return
            
            self.send_error(400, "Invalid file upload")
            
        except Exception as e:
            self.send_error(500, f"Upload error: {str(e)}")
    
    def handle_run_pipeline(self, user: dict):
        """Handle pipeline execution request for specific user."""
        user_id = user['id']
        status = get_pipeline_status(user_id)
        
        if status["running"]:
            self.send_json_response({
                "success": False,
                "error": "Pipeline is already running for this user"
            }, 400)
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            params = json.loads(body) if body else {}
            
            filename = params.get('filename', '')
            use_ml = params.get('use_ml', False)
            hw_start = params.get('hw_start', 1)
            hw_end = params.get('hw_end', 7)
            
            upload_dir, _ = get_user_dirs(user_id)
            
            if not filename:
                uploads = list(upload_dir.glob('*.csv'))
                if uploads:
                    filename = uploads[-1].name
                else:
                    self.send_error(400, "No CSV file uploaded")
                    return
            
            # Start pipeline in background thread
            thread = threading.Thread(
                target=run_pipeline_async,
                args=(user_id, filename, use_ml, hw_start, hw_end)
            )
            thread.start()
            
            self.send_json_response({
                "success": True,
                "message": "Pipeline started",
                "user_id": user_id
            })
            
        except Exception as e:
            self.send_error(500, f"Error starting pipeline: {str(e)}")
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        user = self.get_current_user()
        user_info = f"[{user['username']}]" if user else "[anonymous]"
        print(f"[{self.log_date_time_string()}] {user_info} {format % args}")


def run_pipeline_async(user_id: str, filename: str, use_ml: bool, hw_start: int, hw_end: int):
    """Run the pipeline asynchronously for specific user."""
    status = get_pipeline_status(user_id)
    
    status.update({
        "running": True,
        "step": 0,
        "message": "Starting pipeline...",
        "error": None,
        "result": None
    })
    
    upload_dir, output_dir = get_user_dirs(user_id)
    
    try:
        csv_path = upload_dir / filename
        json_converted_path = output_dir / "step1_converted.json"
        json_organized_path = output_dir / "step2_organized.json"
        json_final_path = output_dir / "final_result.json"
        
        # Step 1: CSV to JSON
        status["step"] = 1
        status["message"] = "Step 1: Converting CSV to JSON..."
        print(f"\n[{user_id}] {'='*50}")
        print(f"[{user_id}] Step 1: CSV to JSON Conversion")
        print(f"[{user_id}] {'='*50}")
        
        step1_stats = convert_csv_to_json(str(csv_path), str(json_converted_path))
        
        # Step 2: Organize Data
        status["step"] = 2
        status["message"] = "Step 2: Organizing data..."
        print(f"\n[{user_id}] {'='*50}")
        print(f"[{user_id}] Step 2: Data Organization")
        print(f"[{user_id}] {'='*50}")
        
        step2_stats = organize_json_file(
            str(json_converted_path), 
            str(json_organized_path),
            hw_start, 
            hw_end
        )
        
        # Step 3: ML Inference
        status["step"] = 3
        status["message"] = "Step 3: Running ML inference..."
        print(f"\n[{user_id}] {'='*50}")
        print(f"[{user_id}] Step 3: ML Inference")
        print(f"[{user_id}] {'='*50}")
        
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
        status["step"] = 4
        status["message"] = "Step 4: Running score-review correlation analysis..."
        print(f"\n[{user_id}] {'='*50}")
        print(f"[{user_id}] Step 4: Score-Review Correlation Analysis")
        print(f"[{user_id}] {'='*50}")
        
        step4_stats = None
        try:
            from score_review_analysis import generate_analysis_report
            analysis_report = generate_analysis_report(str(json_final_path))
            if analysis_report and 'error' not in analysis_report:
                step4_stats = {
                    "total_students": analysis_report.get('summary', {}).get('total_students', 0),
                    "total_reviews": analysis_report.get('summary', {}).get('total_reviews_given', 0),
                    "analysis_file": str(output_dir / "score_review_analysis.json")
                }
                print(f"[{user_id}] Analysis completed: {step4_stats['total_students']} students, {step4_stats['total_reviews']} reviews")
            else:
                print(f"[{user_id}] Score analysis skipped (no score data or error)")
        except Exception as e:
            print(f"[{user_id}] Score-review analysis skipped: {e}")
       
        # Complete
        status["step"] = 5
        status["message"] = "Pipeline completed successfully!"
        status["running"] = False
        status["result"] = {
            "step1": step1_stats,
            "step2": step2_stats,
            "step3": step3_stats,
            "step4": step4_stats,
            "output_file": str(json_final_path)
        }
        
        print(f"\n[{user_id}] {'='*50}")
        print(f"[{user_id}] Pipeline Complete!")
        print(f"[{user_id}] {'='*50}")
        print(f"[{user_id}] Output: {json_final_path}")
        
    except Exception as e:
        status["running"] = False
        status["error"] = str(e)
        status["message"] = f"Error: {str(e)}"
        print(f"\n[{user_id}] Pipeline Error: {e}")
        traceback.print_exc()


# Multi-threaded HTTP Server
class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""
    daemon_threads = True
    allow_reuse_address = True
    
    def server_bind(self):
        """Set socket options for better reliability."""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


def start_server(port: int = 8002):
    """Start the pipeline server."""
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, PipelineHandler)
    httpd.socket.settimeout(1)
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "localhost"
    
    print(f"\n{'='*60}")
    print("  Review Graph Visualization - Pipeline Server")
    print("  Multi-User Mode Enabled")
    print(f"{'='*60}")
    print(f"\n  Local:    http://localhost:{port}")
    print(f"  Network:  http://{local_ip}:{port}")
    print(f"\n  Pages:")
    print(f"    - Login:       http://{local_ip}:{port}/login")
    print(f"    - Pipeline:    http://{local_ip}:{port}/")
    print(f"    - Graph View:  http://{local_ip}:{port}/graph")
    print(f"    - Correlation: http://{local_ip}:{port}/correlation")
    print(f"\n  Users file: {USERS_FILE}")
    print(f"\n  Press Ctrl+C to stop the server")
    print(f"{'='*60}\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()
        print("Server stopped.")


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8002
    start_server(port)
