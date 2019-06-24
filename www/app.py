import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from aiohttp import web


#   handler函数必须用协程
async def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')


# 新版aiohttp中,通过runner运行一个app.
async def init():
    app = web.Application()
    #   router直接通过add_get更简单.
    app.router.add_get('/', index)
    runner = web.AppRunner(app)
    await runner.setup()
    #   由runner配置site,定制服务器.
    site = web.TCPSite(runner, 'localhost', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    await site.start()


#   必须要有loop, 协程init才能运行,否则报错.coroutine 'init' was never awaited
loop = asyncio.get_event_loop()
loop.run_until_complete(init())
#   让协程一直运行,否则执行完会退出,服务器关闭.
loop.run_forever()
