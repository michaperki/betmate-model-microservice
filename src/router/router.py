from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
from urllib.parse import parse_qs
import os
import aiohttp
import asyncio

HOST_URL = os.environ.get('HOST_URL', 'localhost')


class RouteHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        """
        Parses path of request to determine which Lambda to pass request to.
        Then asynchonously waits for response from Lambda, which is then parsed and returned to caller.

        Also reformats request to fit Lambda schema:
        - Takes query string and turns it into a JSON body
        - Makes a POST request instead of GET

        Returns 400 if:
        - Route is incorrect
        - Query string is incorrect
        """

        route, query = self.path.split('?')
        *_, target = route.split('/')

        port = {
            'wdl': 8081,
            'top-moves': 8082
        }.get(target, None)

        if port:
            url = f'http://{HOST_URL}:{port}/2015-03-31/functions/function/invocations'
            data = json.dumps({'queryStringParameters': {k: v[0] for k, v in parse_qs(query).items()}})

            asyncio.run(self.make_request(url, data))

        else:
            self.make_headers(400)
            message = json.dumps({'message': 'FAILURE', 'data': 'bad URL'})
            self.wfile.write(bytes(message, 'utf8'))

    def make_headers(self, code: int):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    async def make_request(self, url: str, data: str):
        """Asynchronous request. Returns parsed response to caller."""
        async with aiohttp.ClientSession() as session,\
                   session.post(url, data=data) as resp:
            payload = await resp.text()
            data = json.loads(payload)
            self.make_headers(data['statusCode'])
            message = json.dumps(json.loads(data['body']))
            self.wfile.write(bytes(message, 'utf8'))


def main():
    handler = HTTPServer(('0.0.0.0', 8000), RouteHandler)
    print("serving at port %s" % 8000)
    handler.serve_forever()


if __name__ == '__main__':
    main()
