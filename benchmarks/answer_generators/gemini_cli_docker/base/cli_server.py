import http.server
import json
import os
import subprocess
import sys

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            
            # Expecting 'args' list: ["gemini", "prompt", ...]
            args = data.get('args', [])
            
            # Optional: 'env' dictionary to merge with system env
            request_env = data.get('env', {})
            
            if not args or args[0] != "gemini":
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid command. Must start with 'gemini'.")
                return

            print(f"Executing: {args}")
            
            # Merge env
            full_env = os.environ.copy()
            full_env.update(request_env)

            # Run the command
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                env=full_env 
            )
            
            response = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_GET(self):
        if self.path == "/version":
            self.send_response(200)
            self.end_headers()
            try:
                with open("version.txt", "r") as f:
                    version = f.read().strip()
                self.wfile.write(version.encode())
            except FileNotFoundError:
                self.wfile.write(b"unknown")
        else:
            # Health check
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Gemini CLI Server Ready")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}")
    server = http.server.HTTPServer(('0.0.0.0', port), RequestHandler)
    server.serve_forever()
