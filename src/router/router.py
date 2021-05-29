from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
from urllib.parse import parse_qs
import os
import requests

host_url = os.environ.get('HOST_URL', 'localhost')

class RedirectHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        route, query = self.path.split('?')
        *_, target = route.split('/')

        port = {
            'wdl': 8081,
            'top-moves': 8082
        }.get(target, None)

        if port:
            data = json.dumps({'queryStringParameters': { k: v[0] for k, v in parse_qs(query).items()}})
            response = requests.post(f'http://{host_url}:{port}/2015-03-31/functions/function/invocations', data)
            message = json.dumps(json.loads(json.loads(response.content)['body']))
            self.wfile.write(bytes(message, 'utf8'))
        else:
            message = json.dumps({ 'message': 'FAILURE', 'data': 'bad URL' })
            self.wfile.write(bytes(message, 'utf8')) 


def main():
    handler = HTTPServer(('0.0.0.0', 8000), RedirectHandler)
    print("serving at port %s" % 8000)
    handler.serve_forever()

if __name__ == '__main__':
    main()
    