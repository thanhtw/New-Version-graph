#!/usr/bin/env python3
"""
ProgEdu Review Local Server - Fixed JSON Response Issues
Resolves static file serving and CORS issues
"""

import http.server
import socketserver
import os
import sys
import mimetypes
from urllib.parse import unquote
import json

# Use the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ProgEduHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler with CORS support and proper JSON handling"""
    
    def __init__(self, *args, **kwargs):
        # Ensure running in the correct directory
        super().__init__(*args, directory=BASE_DIR, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        # URL decode
        path = unquote(self.path)
        
        # Remove query parameters
        if '?' in path:
            path = path.split('?')[0]
        
        print(f"🌐 Received request: {path}")
        
        # Special handling for JSON files - before other processing
        if (path.endswith('.json') or 'visualization_data.json' in path):
            print(f"📊 JSON request: {path}")
            self._serve_json_only(path)
            return
        
        # Redirect root to static
        if path == '/':
            self.send_response(301)
            self.send_header('Location', '/static/')
            self._add_cors_headers()
            self.end_headers()
            return
            
        # Handle static directory index
        if path == '/static/' or path == '/static':
            self._list_static_directory()
            return
        
        # For all other files, call parent method
        print(f"📄 Standard handling: {path}")
        try:
            super().do_GET()
        except Exception as e:
            print(f"❌ Standard handling failed {path}: {e}")
            self.send_error(404, f"File not found: {path}")

    def _serve_json_only(self, path):
        """Handle JSON files specifically, return pure JSON data"""
        try:
            print(f"🔧 Processing JSON: {path}")
            
            # Build full file path
            if path.startswith('/'):
                file_path = path[1:]
            else:
                file_path = path
            
            full_path = os.path.join(BASE_DIR, file_path)
            print(f"📂 File path: {full_path}")
            
            if not os.path.exists(full_path):
                print(f"❌ File not found: {full_path}")
                self._send_json_error(404, "JSON file not found")
                return
            
            # Read JSON file
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"📊 JSON size: {len(content)} characters")
            
            # Validate JSON format
            try:
                json.loads(content)
                print("✅ JSON format validation passed")
            except json.JSONDecodeError as e:
                print(f"❌ JSON format error: {e}")
                self._send_json_error(500, f"Invalid JSON: {e}")
                return
            
            # Send pure JSON response
            self._send_pure_json(content)
            print("✅ JSON response sent successfully")
            
        except Exception as e:
            print(f"❌ JSON processing failed: {e}")
            import traceback
            traceback.print_exc()
            self._send_json_error(500, f"Server error: {e}")

    def _send_pure_json(self, json_content):
        """Send pure JSON content without extra HTTP headers"""
        try:
            content_bytes = json_content.encode('utf-8')
            
            # Build minimal HTTP response
            response_parts = [
                "HTTP/1.0 200 OK",
                "Content-Type: application/json; charset=utf-8",
                f"Content-Length: {len(content_bytes)}",
                "Access-Control-Allow-Origin: *",
                "Access-Control-Allow-Methods: GET, POST, OPTIONS",
                "Access-Control-Allow-Headers: Content-Type",
                "",  # Empty line separates headers and body
                ""   # This will be replaced by JSON content
            ]
            
            # Send response headers
            response_headers = "\r\n".join(response_parts[:-1]) + "\r\n"
            self.wfile.write(response_headers.encode('utf-8'))
            
            # Send JSON content
            self.wfile.write(content_bytes)
            self.wfile.flush()
            
        except Exception as e:
            print(f"❌ Failed to send JSON response: {e}")

    def _send_json_error(self, status_code, message):
        """Send JSON formatted error response"""
        try:
            error_json = json.dumps({"error": message, "status": status_code})
            content_bytes = error_json.encode('utf-8')
            
            response_parts = [
                f"HTTP/1.0 {status_code} Error",
                "Content-Type: application/json; charset=utf-8",
                f"Content-Length: {len(content_bytes)}",
                "Access-Control-Allow-Origin: *",
                "",
                ""
            ]
            
            response_headers = "\r\n".join(response_parts[:-1]) + "\r\n"
            self.wfile.write(response_headers.encode('utf-8'))
            self.wfile.write(content_bytes)
            self.wfile.flush()
            
        except Exception as e:
            print(f"❌ Failed to send error response: {e}")

    def _add_cors_headers(self):
        """Add CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def end_headers(self):
        """Override end_headers to add CORS support"""
        self._add_cors_headers()
        super().end_headers()

    def _list_static_directory(self):
        """List static directory contents"""
        try:
            static_path = os.path.join(BASE_DIR, "static")
            files = os.listdir(static_path)
            
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>ProgEdu Review - File Directory</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    h1 { color: #333; }
                    .file-list { list-style: none; padding: 0; }
                    .file-list li { margin: 10px 0; }
                    .file-list a { 
                        text-decoration: none; 
                        color: #0066cc; 
                        padding: 8px 12px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        display: inline-block;
                        min-width: 200px;
                    }
                    .file-list a:hover { background: #f0f8ff; }
                    .html-file { background: #e8f5e8; }
                    .js-file { background: #fff8e1; }
                    .json-file { background: #f3e5f5; }
                </style>
            </head>
            <body>
                <h1>🎓 ProgEdu Review - File Directory</h1>
                <div class="alert alert-success">
                    <strong>✅ JSON Fix Complete!</strong> Visualization data can now be loaded normally
                </div>
                <h2>📁 Main Pages</h2>
                <ul class="file-list">
            """
            
            # 分類文件
            html_files = [f for f in files if f.endswith('.html')]
            js_files = [f for f in files if f.endswith('.js')]
            json_files = [f for f in files if f.endswith('.json')]
            
            # Show important pages first
            important_pages = [
                ('visualizationAnalysis.html', '📊 Visualization Analysis (Main Feature)'),
                ('test_json_load.html', '🔍 JSON Load Test'),
                ('academicTables.html', '📋 Academic Tables'),
                ('multipleRegressionReport.html', '📈 Multiple Regression Report')
            ]
            
            for page, description in important_pages:
                if page in html_files:
                    html_content += f'<li><a href="/static/{page}" class="html-file">{description}</a></li>\n'
                    html_files.remove(page)
            
            # 其他HTML文件
            for file in sorted(html_files):
                html_content += f'<li><a href="/static/{file}" class="html-file">📄 {file}</a></li>\n'
            
            html_content += """
                </ul>
                <h2>📁 Data Files</h2>
                <ul class="file-list">
            """
            
            # JSON 文件
            for file in sorted(json_files):
                html_content += f'<li><a href="/static/{file}" class="json-file">📊 {file}</a></li>\n'
            
            html_content += """
                </ul>
                <footer style="margin-top: 40px; color: #666;">
                    <p>🚀 Server running successfully, JSON issues fixed</p>
                </footer>
            </body>
            </html>
            """
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error listing directory: {e}")

    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.date_time_string()}] {format % args}")

def start_server(port=8001):
    """Start the server"""
    try:
        # Change to the correct working directory
        os.chdir(BASE_DIR)
        
        with socketserver.TCPServer(("", port), ProgEduHTTPRequestHandler) as httpd:
            print(f"🎓 ProgEdu Review Server Started Successfully! (JSON Fixed Version)")
            print(f"📡 Address: http://127.0.0.1:{port}")
            print(f"📁 Root Directory: {os.getcwd()}")
            print(f"🌐 Main Page: http://127.0.0.1:{port}/static/")
            print(f"📊 Visualization Analysis: http://127.0.0.1:{port}/static/visualizationAnalysis.html")
            print(f"🔍 JSON Test: http://127.0.0.1:{port}/static/test_json_load.html")
            print(f"🔗 Network Graph: http://127.0.0.1:{port}/static/3label.html")
            print(f"\n✅ JSON loading issue fixed!")
            print("Press Ctrl+C to stop the server")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except OSError as e:
        if e.errno in (48, 98):  # Address already in use (48=macOS, 98=Linux)
            print(f"❌ Port {port} is already in use, trying port {port + 1}")
            start_server(port + 1)
        else:
            print(f"❌ Server startup failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    # Check if port is specified
    port = 8001
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Port number must be a number")
            sys.exit(1)
    
    start_server(port)
