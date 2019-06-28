#   创建一个数据库连接池
import logging

import aiomysql

import enum

logging.basicConfig(level=logging.INFO)

__pool = None


def log(sql, args=()):
    logging.info('SQL: %s' % sql)


#   使用async和await实现协程.
async def create_pool(loop, **kw):
    logging.info('create a database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


class Result(enum.Enum):
    Failed = 0
    Success = 1


#   sql查询语句
async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async  with __pool.acquire() as conn:
        cur = await conn.cursor(aiomysql.DictCursor)
        await cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = await cur.fetchmany(size)
        else:
            rs = await cur.fetchall()
        await cur.close()
        logging.info('rows returned: %s' % len(rs))
        return rs


#   insert, update, delete
#   返回影响的行数.
async def execute(sql, args):
    log(sql)
    global __pool
    async with __pool.acquire() as conn:
        try:
            cur = await conn.cursor()
            #   用%s替换?,然后传入游标的execute方法执行.
            await cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            await cur.close()
        except BaseException as e:
            raise
        return affected


#   创建多个?,用逗号连缀在一起.如: ?, ?, ?
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)


#   定义元类ModelMataclass,用来生成其它类.
# noinspection SqlResolve
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        #   排出Model类本身,也就是说Model中是没有__select__,__insert__等属性的.
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        #   获取table名称
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        #   获取所有的Field和主键名
        mappings = dict()
        fields = []
        #   记录是否已经定义主键
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info(' found mapping: %s ===> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到重复的主键
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field : %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        #   将fields转义为sql语句需要的格式,即field的外面用反引号引起来.
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        #   保存属性和列的映射关系
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tableName
        #   主键属性名
        attrs['__primary_key__'] = primaryKey
        #   主键外的属性名
        attrs['__fields__'] = fields
        #   构造默认的SELECT,INSERT,UPDATE和DELETE语句:
        attrs['__select__'] = 'SELECT `%s`, %s FROM `%s`' % (primaryKey, ','.join(escaped_fields), tableName)
        attrs['__insert__'] = 'INSERT INTO `%s` (%s, `%s`) VALUES (%s)' % (
            tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        """
        ','.join(map(lambda f:'`%s`=?' % (mappings.get(f).name or f ), fields))
        将fields中所有的元素拿到lambda中进行运算,结果为 `f.name or f`=?组成的list.再通过join函数,用','将所有元素连接起来.最后的结果类似 `f1.name`=?, `f2`=?
        所以最终拼接得到的update语句为:
        UPDATE `tableName` SET `f1.name`=?, `f2`=?... WHERE `primaryKey`=?
        """
        attrs['__update__'] = 'UPDATE `%s` SET %s WHERE `%s` =?' % (
            tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        # 这里的`(反引号)是sql语句中用来给表名和列名做引用的.最后拼出的语句如下:
        #   DELETE FROM `user` WHERE `id`=?
        attrs['__delete__'] = 'DELETE FROM `%s` WHERE `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


#   ORM映射类的基类Model
# noinspection SqlResolve
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super().__init__(**kw)

    #   通过__getattr__和__setattr__,能够更容易的访问类成员(直接获取)
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    #   调用__getattr__有异常处理.
    def getValue(self, key):
        return getattr(self, key, None)

    #   对于没有默认值的可以,获取类中定义的默认值
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        #   从类内部维护的指点中查找可以,如果找到是可调用函数则调用获得值,否则直接获得该值作为默认值.
        if value is None:
            field = self.__mappings__[key]
            value = field.default() if callable(field.default) else field.default
            logging.debug('using default value for %s: %s' % (key, str(value)))
            setattr(self, key, value)
        return value

    #   用@classmethod注解类方法.
    @classmethod
    async def find(cls, pk):
        # 'find object by primary key.'
        #   由于下面定义了cls.__select__的前半句,这里只需要加上WHERE限定语句即可.

        rs = await select('%s WHERE `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        #   最终转为调用类的对象.这里的**表示将字典中的元素拆分成key=value的参数形式,如果是*则是把元祖的成员转为单个参数.
        return cls(**rs[0])

    #   findAll()找出所有满足条件的记录.这里结果需要转为对应对象,所以也设计为类方法.
    #   查找所有记录的where子句还包括是否排序和是否分页的选项. 排序和分页可能没有,所以用**kw
    #   查询条件可以由参数args直接输入例如: args=['id between 1 and 10']
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        sql = cls.__select__
        if where!= None:
            sql = sql + ' WHERE %s' % (where,)
        orderby = kw.get('orderBy', None)
        if orderby:
            sql = sql + ' ORDER BY ' + orderby
        limit = kw.get('limit', None)
        if limit:
            if isinstance(limit, int):
                sql = sql + ' LIMIT ' + limit
            elif isinstance(limit, tuple):
                sql = sql + '  LIMIT ' + str(limit[0]) + ' ,' + str(limit[1])
            else:
                raise ValueError('Invalid limit value, limit must be an Integer or an tuple with Integer.')
        rs = await select(sql, args)
        return [cls(**r) for r in rs]

    #   查找符合条件的记录总数.
    @classmethod
    async def findNumber(cls, selectedField, where=None, args=None):
        #   这里用_num_作为别名,方便最后从结果中取得数据.
        sql = 'SELECT  count(%s)  _num_  FROM `%s`' % (selectedField, cls.__table__)
        if where != None:
            sql = sql + ' WHERE %s ' % (where, )
        rs = await select(sql, args)
        if len(rs) == 0:
            return 0
        return rs[0]['_num_']

    #   实例方法
    async def save(self):
        #   将__fields__没有赋值的元素设置默认值,转为list.
        args = list(map(self.getValueOrDefault, self.__fields__))
        #   将主键获取默认值后添加到list.
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s ' % rows)
            return Result.Failed
        else:
            return Result.Success

    #   更新一条记录.
    async def update(self):
        #   通过getvalue方法获取模型中对应field的值.
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warning('failed to update record: affected rows: %s' % rows)
            return Result.Failed
        else:
            return Result.Success

    #   删除一条记录
    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warning('failed to remove record: affected rows: %s' % rows)
            return Result.Failed
        else:
            return Result.Success


#   映射列的基类
class Field(object):
    #   default为默认值
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s: %s>' % (self.__class__.__name__, self.column_type, self.name)


#   映射varchar列为StringField
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


#  映射BOOL列为BooleanField
class BooleanField(Field):
    def __init__(self, name=None, primary_key=False, default=False, ddl='BOOLEAN'):
        super().__init__(name, ddl, primary_key, default)


#   映射FLOAT列为FloatField
class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='REAL'):
        super().__init__(name, ddl, primary_key, default)


#   映射TEXT列为TextField
class TextField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='MEDIUMTEXT'):
        super().__init__(name, ddl, primary_key, default)
