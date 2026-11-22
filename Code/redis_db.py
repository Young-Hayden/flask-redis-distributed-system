# 引入redis模块,安装模块：pip install redis==5  指定安装redis5,现在最新是redis6
# 直连数据库
# 直连方式：每次操作都建立一个新的连接，简单但开销大；
# 对比 redis_pool.py 的“连接池”方式（复用连接），适合并发场景。
import redis

# 创建连接
# StrictRedis：Redis 的严格模式客户端，所有方法名与 Redis 命令一一对应。
redis_client = redis.StrictRedis(
    # 必填项
    host='127.0.0.1',
    port=6379,
    db = 0, # 连默认数据库（Redis 默认有 16 个库：0~15）

    # 非必填项
    # 设置密码
    # password='you_pasword'
)

# 提取数据库中的值
# redis_client.set('test','abc')
# print(redis_client.get('test'))
