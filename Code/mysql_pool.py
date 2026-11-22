# 安装数据库连接池模块：pip install dbutils
from dbutils.pooled_db import PooledDB
# 引入需要调用的数据库模块
import pymysql
# import pymysql.cursors
# 引入统一配置（地址/密码不再硬编码，见 config.py 的"配置与代码解耦"）
import config
# 创建数据库连接池
# 连接池的作用：预先创建一批连接放在一起，谁要用就从池里取，用完还回去，
# 避免每次操作都重新建立连接（建连开销大），尤其适合 Web 这种高频访问场景。
pool = PooledDB(
    # 必填项
    # 指定数据库类型
    creator=pymysql,
    # 数据库地址（环境变量/.env 可覆盖，分布式部署时指向数据库机器）
    host = config.MYSQL_HOST,
    # 用户名
    user = config.MYSQL_USER,
    # 密码：
    password = config.MYSQL_PASSWORD,
    # 数据库名
    db = config.MYSQL_DB,
    # 连接池中允许的最大连接数
    maxconnections= config.MYSQL_MAX_CONNECTIONS,
    # 连接池中空连接的最大数量（闲置连接的上限，超过的会被释放）
    maxcached= config.MYSQL_MAX_CACHED,
    # 如果超过最大连接数，是否阻塞并等待。
    # True：池满时调用方等待，直到有空闲连接（安全，不会报错）；
    # False：池满时直接报错。
    blocking=True,

    # 非必填写项
    port = config.MYSQL_PORT,
    # 从池中取连接时先ping一下,若连接已被MySQL服务端断开(如隔夜超时)则自动重建,
    # 避免拿到"死连接"报错。0=从不ping(默认) 1=取出时ping
    ping = 1,
    # 让查询结果以字典形式返回（字段名做 key），默认是元组
    cursorclass = pymysql.cursors.DictCursor
)

# 通过数据库连接池，创建数据库连接
# 从连接池中获取一个连接，创建连接对象
# 注意：这个全局 conn/cursor 只留给 redis_listen*.py 等【单线程后台脚本】用。
#       Web 路由(App.py)不要用它们——多线程并发会互相串数据;
#       路由里应通过 App.py 的 get_db_cursor() 获取每请求独立的连接。
conn:pymysql.Connection = pool.connection()
# 创建游标
cursor = conn.cursor()

# 测试连接是否成功
if __name__=='__main__':
    cursor.execute('select * from student')
    res = cursor.fetchall()
    print(res)