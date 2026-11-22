# 引入redis
# 连接池方式：预先建立好一批连接放池子里，取用复用，比 redis_db.py 的直连更高效。
import redis
# 引入统一配置（Redis 地址不再硬编码，分布式部署时改 .env 即可指向缓存机器）
import config

# 创建连接池
pool = redis.ConnectionPool(
    host = config.REDIS_HOST,
    port = config.REDIS_PORT
)
# 创建连接
# 多个 Redis 客户端可以共用同一个连接池，连接在用完后自动归还池中。
redis_client = redis.Redis(connection_pool=pool)

if __name__=='__main__':
    # 提取数据库中的值
    # 设置键值对
    # redis_client.set('test','张三')
    # # redis里面的值是byte类型，汉字会直接被转码成Byte类型
    # # 使用时需要用.decode('utf-8')进行转换才能正常显示
    # # 读取键的值
    # print(redis_client.get('test').decode('utf-8'))

    # 设置哈希类型（字典类型）
    # 设置字典变量中的某个值
    # redis_client.hset('张三',mapping={'name':'张三','age':18,'sex':'男'})
    # # 读取字典变量中的值
    # print(redis_client.hget('张三','name').decode('utf-8'))

    # 从数据库中读取一条字典数据，写入缓存并从缓存中读出来=====================
    # 删除缓存
    # redis_client.delete('张一二')

    # 缓存的正确使用方法
    # stu_name = redis_client.hget('张一二', 'stu_name')

    # 判断缓存值是否存在，如果为None，要从MYSQL数据库提取
    # if stu_name is None:
    #     # 从数据库中读取姓名为张一二的所有信息，存到redis里面
    #     from mysql_pool import *
    #     cursor.execute("select * from student where stu_name='张一二'")
    #     res = cursor.fetchone()
    #     redis_client.hset('张一二', mapping=res)
    #     # 从缓存中读取张一二的相关信息
    #     print('从数据库读取')
    # else:
    #     print('从缓存中读取')
    #
    # # 不管数据从来哪的，都从缓存中读取
    # print(redis_client.hget('张一二', 'stu_name').decode('utf-8'))
    # print(redis_client.hget('张一二', 'sex').decode('utf-8'))
    # print(redis_client.hget('张一二', 'age').decode('utf-8'))

    # 从数据库中读取一条字典数据，写入缓存并从缓存中读出来=====================


    # 从数据库中读取所有数据逐条写入缓存，并从缓存中读出来=====================
    # 下面这段是“缓存预热”的独立演示：先查缓存，缓存为空则从 MySQL 取数据写入缓存，
    # 再从缓存读出来——逻辑和 App.py 首页路由里的一致，可对照理解。
    from mysql_pool import *
    import json
    # 正确使用流程
    # 先从缓存中读取想要的值
    # 删除指定的数组序列变量
    # keys = redis_client.keys('stu_info:*')
    # if len(keys)>0:
    #     redis_client.delete(*keys)

    keys = redis_client.keys('stu_info:*')
    # 判断keys的长度，如果为0，则表示没有数据
    if len(keys)==0:
        # 从数据库中读取所有信息，存到redis里面

        cursor.execute('select id,uname,sex,class from student order by id desc limit 5')
        res = cursor.fetchall()
        # print(res)

        # 通过循环将数据读出来，以字符串类型逐条存入缓入
        for row in res:
            # 定义一个变量名的键值，用来做（伪）列表主键
            key = f'stu_info:{row["id"]}'
            # 定义变量值，将字典类型数据转成json
            value = json.dumps(row)
            # 将键和值以字符串变量的形式存入缓存
            redis_client.set(  key  , value )
        # 在这里从缓存重新读取数据
        keys = redis_client.keys('stu_info:*')
        # print(keys)
        print('从数据库中来')
    else:
        print('从缓存中来')
    # 从缓存中将指定多行数据取出来==============================
    stu_list = []
    for key_i in keys:
        # 通过变量名key_i取出变量的值（json类型的）
        value = redis_client.get(key_i)
        # 将json类型转成原来的类型
        value = json.loads(value)

        # 将值存入到指定的列表变量中，组成新的列表数据（跟从数据库中取出的一样）
        stu_list.append(value)

    # stu_list就可以应用到项目中了。
    print(stu_list)
    # 从缓存中将指定多行数据取出来==============================