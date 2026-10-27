# Stands in for GitHub's OIDC endpoint and for the STS on 127.0.0.1:18080, so
# the action completes its authenticated path without real credentials. Every
# GET returns an OIDC token and every POST returns the access token
# "standin-guard-token", except a POST under /reject/, which answers the way
# the STS refuses an exchange.
import http.server, json

class Handler(http.server.BaseHTTPRequestHandler):
    def reply(self, body, status=200):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply({'value': 'standin-oidc-token'})

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length') or 0))
        if self.path.startswith('/reject/'):
            self.reply({'message': 'invalid ID token'}, 400)
            return
        self.reply({'access_token': 'standin-guard-token', 'expires_in': 1800})

    def log_message(self, *args):
        pass

http.server.HTTPServer(('127.0.0.1', 18080), Handler).serve_forever()
