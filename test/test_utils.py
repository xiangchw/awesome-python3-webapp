import asyncio

import orm


# 装饰,增加loop,支持协程运行.
def async_test(coro):
    def wrapper(*args, **kwargs):
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        return _loop.run_until_complete(coro(*args, **kwargs))

    return wrapper


#   初始化数据库连接池
async def dbpoolinit():
    await orm.create_pool(asyncio.get_event_loop(), user='www-data', password='www-data', db='awesome')


#   清空comments表
async def clearTable(table_name):
    sql = 'DELETE FROM `%s`' % (table_name,)
    await orm.execute(sql, None)
