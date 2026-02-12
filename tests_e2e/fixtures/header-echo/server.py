#!/usr/bin/env python3
"""Simple HTTP server that echoes all request headers"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class HeaderEchoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        # Collect all headers
        headers = dict(self.headers)

        # Add the client IP as seen by this server
        response = {
            'headers': headers,
            'client_ip': self.client_address[0],
            'x_forwarded_for': self.headers.get('X-Forwarded-For', 'NOT SET')
        }

        self.wfile.write(json.dumps(response, indent=2).encode())

    def log_message(self, format, *args):
        # Log to stdout
        print(f"{self.address_string()} - {format % args}")

if __name__ == '__main__':
    port = 8080
    server = HTTPServer(('0.0.0.0', port), HeaderEchoHandler)
    print(f'Header echo server running on port {port}...')
    server.serve_forever()
