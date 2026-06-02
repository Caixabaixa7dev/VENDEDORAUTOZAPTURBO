from aiohttp import web
import os
import logging

logger = logging.getLogger(__name__)


async def health_check(request):
    return web.json_response({"status": "ok", "service": "zapturbo-bot"})


async def start_web_server():
    port = int(os.getenv("PORT", "10000"))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server running on port {port}")
