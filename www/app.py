import asyncio
import datetime
import json
import logging
import os

import orm
from jinja2 import Environment, FileSystemLoader

from coroweb import add_routes, add_static

logging.basicConfig(level=logging.INFO)

from aiohttp import web


def init_jinja2(app, **kw):
    """
    初始化模板引擎jinja2
    :param app:
    :param kw:模板引擎参数,常用参数见下面的options
    :return:
    """
    logging.info('init jinja2...')
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    #   没有给定path,则使用当前文件所在路径的子目录/templates.
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


async def logger_factory(app, handler):
    """
    给request增加日志记录的装饰器
    :param app:
    :param handler:
    :return:
    """

    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return await handler(request)

    return logger


async def data_factory(app, handler):
    """
    请求数据获取的装饰器
    :param app:
    :param handler:
    :return:
    """

    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startwith('application/json'):
                request.__data__ = await request.json()
            elif request.content_type.startwith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return await handler(request)

    return parse_data


async def response_factory(app, handler):
    """
    midware ,将返回值转为web.Response
    :param app:
    :param handler:
    :return:
    """

    async def response(request):
        logging.info('Response handler...')
        # 结果
        r = await handler(request)
        # 已经是aiohttp的web.StreamResponse
        if isinstance(r, web.StreamResponse):
            return r
        #   如果是字节数组,作为Response的body,并指定Response的类型为字节流.
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        #   如果是字符串,则解码为字节数组,返回类型设为文本.
        if isinstance(r, str):
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        #   如果是字典类型. 没有模板,则转为json,有模板则根据模板渲染.
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dump(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        #   如果是介于100到600之间的整数, 当做状态码创建Response
        if isinstance(r, int) and 100 <= r < 600:
            return web.Response(status=r)
        #   如果r是tuple第一个元素的值介于[100,600)之间,则第一个元素作为状态码,第二个元素作为原因,创建Response.
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and 100 <= t < 600:
                return web.Response(status=t, reason=str(m))
        #   其他情况.r当做Reponse的body.
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp

    return response


def datetime_filter(t):
    """
    将时间转为中文, 返回unicode字符串.
    :param t:
    :return:
    """
    delta = int(datetime.time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s小时前' % (delta // 60)  # 取整除法,获得小时数
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    #   数字太大,说明是timestamp格式,转为datetime,然后拼接.
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


#   handler函数必须用协程
async def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')


# 新版aiohttp中,通过runner运行一个app.
async def init(loop):
    await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='www-data', password='www-data', db='awesome')
    app = web.Application(loop=loop, middlewares=[
        logger_factory, response_factory, data_factory
    ])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    #   router直接通过add_get更简单.
    app.router.add_get('/', lambda x: web.Response(body='Hello World!'))
    add_routes(app, 'handlers')
    add_static(app)

    runner = web.AppRunner(app)
    await runner.setup()
    #   由runner配置site,定制服务器.
    site = web.TCPSite(runner, 'localhost', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    await site.start()


#   必须要有loop, 协程init才能运行,否则报错.coroutine 'init' was never awaited
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
#   让协程一直运行,否则执行完会退出,服务器关闭.
loop.run_forever()
