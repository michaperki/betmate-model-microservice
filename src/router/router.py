
import json
from aiohttp import web, ClientSession
from asyncio import Lock

wdl_lock = Lock()
top_moves_lock = Lock()
move_analysis_lock = Lock()

# Simple in-process counters for observability in dev
STATS = {
    "wdl": {"ok": 0, "error": 0, "exception": 0},
    "top-moves": {"ok": 0, "error": 0, "exception": 0},
    "move-analysis": {"ok": 0, "error": 0, "exception": 0},
}

ROUTE_URLS = {
    "wdl": "http://wdl-container:8080/predict",
    "top-moves": "http://top-moves-container:8080/predict",
    "move-analysis": "http://move-analysis-container:8080/predict",  # Fixed port to match container
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
                    # print("Upstream raw response:", text)
                    if resp.status != 200:
                        print(f"[router] Upstream error: {url} status={resp.status} body={text[:200]}...")
                        # increment counters
                        for key, route_url in ROUTE_URLS.items():
                            if route_url == url:
                                STATS[key]["error"] += 1
                        # Return non-200 to surface failures while keeping a structured body
                        body = json.dumps({
                            "message": "Analysis service unavailable",
                            "data": None,
                            "error": f"Upstream error: {text}",
                            "upstream_status": resp.status
                        })
                        return web.Response(
                            body=body,
                            status=502,
                            content_type='application/json'
                        )

                    result = json.loads(text)
                    body = result.get('body', text)
                    status = result.get('statusCode', 200)
                    # increment ok counter
                    for key, route_url in ROUTE_URLS.items():
                        if route_url == url:
                            STATS[key]["ok"] += 1
                    return web.Response(
                        body=body,
                        status=status,
                        content_type='application/json'
                    )
            except Exception as e:
                print(f"[router] Exception for {url}: {e}")
                for key, route_url in ROUTE_URLS.items():
                    if route_url == url:
                        STATS[key]["exception"] += 1
                # Return non-200 with structured error
                body = json.dumps({
                    "message": "Analysis service unavailable",
                    "data": None,
                    "error": f"Router exception: {e}"
                })
                return web.Response(
                    body=body,
                    status=502,
                    content_type='application/json'
                )

    return handle_route

def main():
    app = web.Application()
    app.add_routes([
        # Root routes for local development
        web.get('/wdl', create_handler(ROUTE_URLS["wdl"], wdl_lock)),
        web.get('/top-moves', create_handler(ROUTE_URLS["top-moves"], top_moves_lock)),
        web.get('/move-analysis', create_handler(ROUTE_URLS["move-analysis"], move_analysis_lock)),
        web.get('/health', lambda _req: web.json_response({"status": "ok"})),
        web.get('/stats', lambda _req: web.json_response(STATS)),

        # Backwards-compatible stage-prefixed routes
        web.get('/dev/wdl', create_handler(ROUTE_URLS["wdl"], wdl_lock)),
        web.get('/dev/top-moves', create_handler(ROUTE_URLS["top-moves"], top_moves_lock)),
        web.get('/dev/move-analysis', create_handler(ROUTE_URLS["move-analysis"], move_analysis_lock)),
        web.get('/dev/health', lambda _req: web.json_response({"status": "ok"})),
        web.get('/dev/stats', lambda _req: web.json_response(STATS)),
    ])
    web.run_app(app, port=8000)

if __name__ == '__main__':
    main()
