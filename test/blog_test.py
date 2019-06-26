import unittest
from models import Blog

import orm, asyncio
from test import user_test
from test.test_utils import async_test, dbpoolinit, clearTable


#   创建一个新的blog对象.
def getNewBlog(blog_id):
    u = user_test.getNewUser(1)
    return Blog(id=blog_id, user_id=u.id, user_name=u.name, user_image=u.image,
                name='First Blog', summary='test blog insert.', content='Hello world.')


class TestBlog(unittest.TestCase):

    #   blog的insert功能测试
    @async_test
    async def testSave(self):
        await dbpoolinit()
        await clearTable('blogs')
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
        #   准备5条id介于0到4的数据.
        await clearTable('blogs')
        for n in range(5):
            #   await表示等待另一个协程执行完成返回，必须在协程内才能使用
            b = getNewBlog(n)
            await b.save()
        where = 'id >= ? and id < ? '
        L = await Blog.findAll(where, [0, 5], limit=(0, 5), orderBy='id')
        self.assertEqual(5, len(L), 'findAll test failed.')

    #   测试Blog的findNumber方法
    @async_test
    async def testFindNumbers(self):
        await dbpoolinit()
        await clearTable('blogs')
        for n in range(5):
            b = getNewBlog(n)
            await b.save()
        result = await Blog.findNumber('id','id >= ? and id <? ',[0,3])
        self.assertEqual(3, result, 'findNumbers test failed.')


if __name__ == '__main__':
    unittest.main()
