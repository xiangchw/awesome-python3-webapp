import unittest, asyncio, orm
from models import User, Blog, Comment

import orm, asyncio
from random import Random
import time

# 装饰,增加loop,支持协程运行.
def async_test(coro):
    def wrapper(*args, **kwargs):
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        return _loop.run_until_complete(coro(*args, **kwargs))

    return wrapper


async def dbpoolinit():
    await orm.create_pool(asyncio.get_event_loop(), user='www-data', password='www-data', db='awesome')

#   获取一个新的User对象
def getNewUser(user_id):
    return User(id=user_id, name='Test', email=str(Random().randint(50000, 100000)) + '@test.com',
                passwd='1234567890', image='ablout:blank')

async def clearUsers():
    await orm.execute('DELETE FROM Users',None)

class TestUser(unittest.TestCase):
    '''
    由于这里是协程执行,所以增删改查的操作是同时进行的.所以,应该每个方法单独运行测试.
    '''
    save_id = 1
    find_id = 13
    delete_id = 11

    #   这里的->None是参数注解,表示本方法调用时不用输入参数.
    def setUp(self) -> None:
        pass

    #   测试users的insert.
    @async_test
    async def testSave(self):
        await dbpoolinit()
        await clearUsers()
        u = getNewUser(1)
        result = await u.save()
        self.assertEqual(result, orm.Result.Success, 'save test failed.')

    #   测试users的select
    @async_test
    async def testSelect(self):
        await dbpoolinit()
        user = await User.find(1)
        self.assertNotEqual(None, user, 'find test failed.')

    # 测试users的update
    @async_test
    async def testUpdate(self):
        await dbpoolinit()
        user = await User.find(1)
        self.assertNotEqual(None, user, 'update test failed, there is no record with provided id.')
        user.name = 'Changed'
        result = await user.update()
        self.assertEqual(orm.Result.Success, result, 'update test failed.')

    #   测试users的delete
    @async_test
    async def testRemove(self):
        await dbpoolinit()
        user = await User.find(1)
        self.assertNotEqual(None, user, 'delete test failed: there is no record with provided id')
        result = await user.remove()
        self.assertEqual(orm.Result.Success, result, 'delete test failed.')

    #   测试findAll方法
    @async_test
    async def testFindAll(self):
        await dbpoolinit()
        await clearUsers()
        #   初始化三条记录
        for x in [1,2,3]:
            u = getNewUser(x)
            await u.save()
        result = await User.findAll('id between ? and ? ',[1,5],orderby='id', limit=(0,3))
        self.assertEqual(3, len(result),'findAll method test failed.')

    #   测试findNumbers
    @async_test
    async def testFindNumbers(self):
        await dbpoolinit()
        await clearUsers()
        #   初始化4条数据
        for x in range(5):
            u = getNewUser(x)
            await u.save()
        where =  'id >=? and id <=? '
        result = await User.findNumber('id',where, [0,5])
        self.assertEqual(5,result,'findNumbers method test failed.')

if __name__ == '__main__':
    unittest.main()
