import json
import os
from aiohttp import web, ClientSession
from asyncio import Lock

HOST_URL = os.environ.get('HOST_URL', 'localhost')

# Locks ensure that a Lambda container does not
# get additional requests while in execution
# which causes the container to crash
wdl_lock = Lock()
top_moves_lock = Lock()


def get_url(port: int):
    return f'http://{HOST_URL}:{port}/2015-03-31/functions/function/invocations'


def create_handler(port: int, lock: Lock):
    """
    Generic async route handler with locking.

    Locking with `lock` allows requests to a specific lambda container, specified by `port`,
    to be made one at a time, as that is all a lambda container can handle.

    Handler will:
      - Parse the request query to create body for new request
      - Lock access to lambda container as request is made to it
      - Parse response from lambda container and return to caller
    """

    url = get_url(port)

    async def handle_route(request: web.Request):
        q = dict(request.query.items())
        data = json.dumps({'queryStringParameters': q})

        async with lock, \
                   ClientSession() as session, \
                   session.post(url, data=data) as resp:

            result = json.loads(await resp.text())

        return web.Response(body=result['body'], status=result['statusCode'])

    return handle_route


def main():
    app = web.Application()
    app.add_routes([web.get('/dev/wdl', create_handler(8081, wdl_lock)),
                   web.get('/dev/top-moves', create_handler(8082, top_moves_lock))])
    web.run_app(app, port=8000)


if __name__ == '__main__':
    main()
