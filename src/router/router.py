
import json
from aiohttp import web, ClientSession
from asyncio import Lock

wdl_lock = Lock()
top_moves_lock = Lock()

ROUTE_URLS = {
    "wdl": "http://wdl-container:8080/predict",
    "top-moves": "http://top-moves-container:8080/predict",
}

def create_handler(url: str, lock: Lock):
    async def handle_route(request: web.Request):
        q = dict(request.query.items())
        data = json.dumps({'queryStringParameters': q})

        async with lock, ClientSession() as session:
            headers = {'Content-Type': 'application/json'}
            try:
                async with session.post(url, data=data, headers=headers) as resp:
                    text = await resp.text()
                    # print("Upstream raw response:", text)  # 👈 Add this line
                    if resp.status != 200:
                        return web.Response(status=resp.status, text=f'Upstream error: {text}')
                    result = json.loads(text)
                    body = result.get('body', text)
                    status = result.get('statusCode', 200)
                    return web.Response(body=body, status=status)
            except Exception as e:
                return web.Response(status=500, text=f'Router exception: {e}')

    return handle_route

def main():
    app = web.Application()
    app.add_routes([
        web.get('/dev/wdl', create_handler(ROUTE_URLS["wdl"], wdl_lock)),
        web.get('/dev/top-moves', create_handler(ROUTE_URLS["top-moves"], top_moves_lock)),
    ])
    web.run_app(app, port=8000)

if __name__ == '__main__':
    main()

