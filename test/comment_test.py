import unittest

from models import Comment
from test import blog_test, user_test
import orm
from test.test_utils import async_test, dbpoolinit, clearTable


#   创建一个新的评论对象.
def getNewComment(comment_id):
    u = user_test.getNewUser(1)
    b = blog_test.getNewBlog(1)
    return Comment(id=comment_id, blog_id=b.id,user_id=u.id,user_name=u.name,user_image=u.image,content='good job!')

class TestComments(unittest.TestCase):

    #   测试save函数.
    @async_test
    async def testSave(self):
        await dbpoolinit()
        await clearTable('comments')
        c = getNewComment(1)
        result = await c.save()
        self.assertEqual(orm.Result.Success, result, 'save test failed.')

    #   测试 find函数
    @async_test
    async def testFind(self):
        await dbpoolinit()
        c = await Comment.find(1)
        self.assertNotEqual(None, c, 'find test failed.')

    #   测试update函数
    @async_test
    async def testUpdate(self):
        await dbpoolinit()
        c = await Comment.find(1)
        self.assertNotEqual(None, c, 'update test failed: there is no recored with provied id.')
        c.content='I changed my comments'
        result = await c.update()
        self.assertEqual(orm.Result.Success, result, 'update test failed.')

    #   测试remove方法
    @async_test
    async def testRemove(self):
        await dbpoolinit()
        c = await Comment.find(1)
        self.assertNotEqual(None, c, 'remove test failed: there is no record with provied id.')
        result = await c.remove()
        self.assertEqual(orm.Result.Success, result, 'remove test failed.')

    # 测试findAll方法
    @async_test
    async def testFindAll(self):
        await dbpoolinit()
        await clearTable('comments')
        #   初始化5条数据
        for x in range(5):
            c = getNewComment(x)
            await c.save()
        where = 'id >= ? and id < ? '
        result = await Comment.findAll(where,[0,5], orderBy='id',limit=(0,5))
        self.assertEqual(5,len(result), 'findAll test failed.')

    # 测试findNumbers方法
    @async_test
    async def testFindNumbers(self):
        await dbpoolinit()
        await clearTable('comments')
        #   初始化5条数据
        for x in range(5):
            c = getNewComment(x)
            await c.save()
        result = await Comment.findNumber('id','id>=? and id <? ',[0,3])
        print('找到', result)
        self.assertEqual(3, result,'findNumbers test failed.')

if __name__=='__main__':
    unittest.main()
