import unittest
from models import Blog

import orm, asyncio
from test import user_test
from test.user_test import async_test, dbpoolinit


# # 装饰,增加loop,支持协程运行.
# def async_test(coro):
#     def wrapper(*args, **kwargs):
#         _loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(_loop)
#         return _loop.run_until_complete(coro(*args, **kwargs))

    # return wrapper

#   创建一个新的blog对象.
def getNewBlog(blog_id):
    u = user_test.getNewUser(1)
    return Blog(id=blog_id, user_id=u.id, user_name=u.name, user_image=u.image,
                name='First Blog', summary='test blog insert.', content='Hello world.')


# 清空表格
# noinspection SqlWithoutWhere
async def clearBlogs():
    await orm.execute('DELETE FROM blogs', None)


"""
    协程写的测试方法,如果同时运行,可能导致测试失败(remove操作在insert之前执行).
    最好在每一个方法上面点击run,按方法依次测试.
"""


class TestBlog(unittest.TestCase):

    #   blog的insert功能测试
    @async_test
    async def testSave(self):
        await dbpoolinit()
        await clearBlogs()
        b = getNewBlog(1)
        result = await b.save()
        self.assertEqual(orm.Result.Success, result, 'insert test failed.')

    #   测试Blog的select功能.
    @async_test
    async def testFind(self):
        await dbpoolinit()
        u = await Blog.find(1)
        self.assertNotEqual(None, u, 'select test failed.')

    #   测试Blog的update功能
    @async_test
    async def testUpdate(self):
        await dbpoolinit()
        b = await Blog.find(1)
        self.assertNotEqual(None, b, 'update test failed: there is no record with provied id.')
        b.name = 'Hello World'
        result = await b.update()
        self.assertEqual(orm.Result.Success, result, 'update test failed.')

    #   测试Blog的remove功能
    @async_test
    async def testRemove(self):
        await dbpoolinit()
        b = await Blog.find(1)
        self.assertNotEqual(None, b, 'remove test failed: there is no record with provied id.')
        result = await b.remove()
        self.assertEqual(orm.Result.Success, result, 'remove test failed.')

    # 测试Blog的findAll方法,
    @async_test
    async def testFindAll(self):
        await dbpoolinit()
        #   准备3条id介于0到2的数据.
        await clearBlogs()
        for n in range(3):
            #   await表示等待另一个协程执行完成返回，必须在协程内才能使用
            b = getNewBlog(n)
            await b.save()
        where = 'id between ? and ?'
        L = await Blog.findAll(where, [0, 8], limit=(0, 2), orderBy='id')
        self.assertEqual(2, len(L), 'findAll test failed.')

    #   测试Blog的findNumber方法
    @async_test
    async def testFindNumbers(self):
        await dbpoolinit()
        #   准备id为5和6的两条数据
        await clearBlogs()
        for n in [5, 6]:
            b = getNewBlog(n)
            await b.save()
        where = 'id between ? and ? '
        result = await Blog.findNumber('id', where, [5, 6])
        self.assertEqual(2, result, 'findNumbers test failed.')


if __name__ == '__main__':
    unittest.main()
