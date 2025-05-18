
import json
from aiohttp import web, ClientSession
from asyncio import Lock

wdl_lock = Lock()
top_moves_lock = Lock()
move_analysis_lock = Lock()

ROUTE_URLS = {
    "wdl": "http://wdl-container:8080/predict",
    "top-moves": "http://top-moves-container:8080/predict",
    "move-analysis": "http://move-analysis-container:8083/predict",  # Updated port to 8083
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
                        print(f"Upstream error: {url} returned status {resp.status}: {text}")
                        # Still return 200 to the client with an error message
                        result = {
                            'statusCode': 404,
                            'body': json.dumps({
                                "message": "Analysis service unavailable",
                                "data": None,
                                "error": f"Upstream error: {text}"
                            })
                        }
                        return web.Response(
                            body=result['body'],
                            status=200,  # Return 200 to avoid client errors
                            content_type='application/json'
                        )

                    result = json.loads(text)
                    body = result.get('body', text)
                    status = result.get('statusCode', 200)
                    return web.Response(
                        body=body,
                        status=status,
                        content_type='application/json'
                    )
            except Exception as e:
                print(f"Router exception for {url}: {e}")
                # Still return 200 to the client with an error message
                result = {
                    'body': json.dumps({
                        "message": "Analysis service unavailable",
                        "data": None,
                        "error": f"Router exception: {e}"
                    })
                }
                return web.Response(
                    body=result['body'],
                    status=200,  # Return 200 to avoid client errors
                    content_type='application/json'
                )

    return handle_route

def main():
    app = web.Application()
    app.add_routes([
        web.get('/dev/wdl', create_handler(ROUTE_URLS["wdl"], wdl_lock)),
        web.get('/dev/top-moves', create_handler(ROUTE_URLS["top-moves"], top_moves_lock)),
        web.get('/dev/move-analysis', create_handler(ROUTE_URLS["move-analysis"], move_analysis_lock)),
    ])
    web.run_app(app, port=8000)

if __name__ == '__main__':
    main()

