# -*- encoding: utf-8 -*-
import asyncio
import functools
import inspect
import logging
import os
from urllib import parse

from aiohttp import web

from apis import APIError


def get(path):
    """
    get装饰器,用来把一个函数装饰为处理对应GET类型请求的函数.
    由于装饰器只支持func作为参数,所以要传入path参数,则需要在外层再套一个函数.
    """

    def decorator(func):
        """
        functools.wraps 的作用是将原函数对象的指定属性复制给包装函数对象, 默认有 module、name、doc,或者通过参数选择。
        如果不适用wraps,则包装后的函数名仍然为wrapper
        """

        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper

    return decorator

#   post装饰器,同get.
def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)

        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper

    return decorator

def get_required_kw_args(fn):
    """
    获取函数中没有默认值的关键字参数(排在*或者*args后面),这些参数名是调用时必须输入的
    :param fn: 待分析函数
    :return: 没有默认值的关键字参数组成的tuple
    """
    args = []
    #   inspect模块用来解析一个类或者函数,可以获取它的成员信息,参数信息等等.
    #   这里使用signature获取fn对应的签名对象Signature, parameters获取的是变量名和参数组成的字典
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        #   参数是KEYWORD_ONLY,也就是排在* 或者*args后面的关键字参数,调用时必须给出该关键字.
        #   且参数是empy,是指该参数没有默认值.
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):
    """
    获取函数fn中的所有关键字参数
    :param fn:
    :return:
    """
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):
    """
    判断函数fn是否有关键字参数.
    :param fn:
    :return: Boolean 有True,无False
    """
    params = inspect.signature(fn).parames
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_args(fn):
    """
    判断fn是否有**kw类型的参数.
    :param fn:
    :return:    Boolean 有True,无False
    """
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    """
    判断fn是否有参数request
    :param fn:
    :return: Boolean 有True,无False
    """
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        # VAR_POSITIONAL 表示这是*args参数.
        # VAR_POSITIONAL 表示命名参数, 位于* 和 *args 后面
        # VAR_KEYWORD 表示这是**kw参数,
        #   同时不满足这三个条件,说明request后面的参数在这三者之前, 则request也必然位于这三者之前
        #   则request不满足命名参数应该位于*或*args之后的规定,所以报错.
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' %(fn.__name__, str(sig)))
    return found

class RequestHandler(object):
    #
    def __init__(self, app, fn):
        """
        初始化,对给定的fn进行解析
        :param app: 当前应用
        :param fn: 要处理的函数名
        """
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_args(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        """
        根据传入的request调用fn函数, 前面对fn的参数进行了各种处理,根据请求类型不同,内容类型不同做不同的检查.
        :param request: 用户请求
        :return:
        """
        kw = None
        #   1.如果有参数:根据请求方法和内容类型获取对应参数放入kw
        #   fn拥有(**kw类型, 关键字参数, 必填关键参数)之一.
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('applicaton/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**kw)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s ' % request.content_type)

            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    #   将查询参数转为字典.
                    for k,v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        #   2.如果没有参数:则kw保存match_info,即route_name和handler(请求路径和处理函数的映射)
        if kw is None:
            kw = dict(**request.match_info)
        else:
            #   3.有参数, 则筛选出关键字参数保存到kw中
            #   不含**kw类型参数 且 含有关键字参数
            if not self._has_var_kw_arg and self._named_kw_args:
                # 移除所有非关键词参数
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # 检查match_info中的route_name,如果在kw中,即是关键字参数,说明关键字参数重复了,报警.
            # 将match_info对应的值更新到kw字典中.用来调用fn.
            for k,v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # 3.检查没有默认值的关键字参数是否已经赋值.
        if self._required_kw_args:
            for name in self._required_kw_args:
                #   没有给定该参数的值,返回调用参数缺失的异常.
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s'  %  name)
        logging.info('call with args: %s' % str(kw))
        #   4.使用解析好的kw调用_func
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):
    """
    给路径拼接static字符串.获得静态资源的相对路径
    :param app:
    :return:
    """
    #   获取当前文件所在文件夹路径,然后拼接一个static在末尾.
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    #   add_static用来添加返回静态内容的路由
    #   add_static仅仅在开发模式使用,因为线上项目应该用nginx等专门的http服务器处理静态文件.
    #   前缀必须以/开头和结尾. 这里表示static类型的文件在当前文件夹的子目录/static中.
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

def add_route(app,fn):
    """
    注册URL处理函数
    :param app:
    :param fn:
    :return:
    """
    method = getattr(fn,'__method__',None)
    path = getattr(fn,'__route__',None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    #   fn既不是协程函数, 又不是生成器函数,则对其进行装饰,转为协程函数
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s=>%s(%s)' % (method, path, fn.__name__,
                                              ','.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app,fn))


def add_routes(app, module_name):
    """
    扫描handler模块,注册符合条件的处理函数.
    :param app:
    :param module_name:
    :return:
    """
    n = module_name.rfind('.')
    #   module_name中不含有'.', 导入该模块
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        #   取最后一个'.'后面的部分作为模块名.
        mod_name = module_name[n+1:]
        #   内部的__import__函数, 取module_name中最后一个'.'前面你的部分作包名, fromList为[mod_name]给出模块名
        #   当fromList不为空时,相当于from name import [mod_name] 如果没有这个则直接导入import name (这里的name就是module_name[:n])
        #   外部的getattr函数,取出第一个参数object的属性, 即object.name
        mod = getattr(__import__(module_name[:n], globals(), locals(), [mod_name]), mod_name)

    #   dir()传入module对象,获取它的全部属性.
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        #   获取模块中所有可调用函数. 然后从其中取出对应的方法和路由,然后添加到路由表中.
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app,fn)
