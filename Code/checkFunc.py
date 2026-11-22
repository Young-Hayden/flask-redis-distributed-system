import os

import pymysql
#引入数据库连接池
import mysql_pool

#引入redis客户端（登录失败限流的计数器用它）
from redis_pool import redis_client

#引入request用来接收外部传值
from flask import request

#引入日志
import logging
import logging.config
#配置日志配置文件
# 无论从项目根目录还是 Code/ 启动，都按当前模块位置读取日志配置。
LOGGING_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
logging.config.fileConfig(LOGGING_CONFIG)
#创建日志对象
logger = logging.getLogger('applog')

# 定义一个过滤函数，对指定的函数中操作数据库的过程进行校验
# 如果数据库操作有误，将错误记录到日志中。

# 这是一个“装饰器”：在不修改原函数代码的前提下，给它包一层额外逻辑。
# 用法：在目标函数上方加 @DBCatchError，调用目标函数时就会先走 wrapper 里的逻辑。
#
# P0改动：原来装饰器和被装饰函数共用 mysql_pool 里的全局连接 yht/cursor，
# 多线程并发时，A请求begin的事务里会混入B请求的SQL，互相串、互相回滚。
# 现在每次调用都从连接池取一个【独立连接】，事务、游标都在它上面，用完归还。
import functools
def DBCatchError(func):

    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        # 从连接池取本次调用专属的连接（多线程互不干扰）
        conn = mysql_pool.pool.connection()
        cursor = conn.cursor()
        try:
            #强制开启一个事务
            conn.begin()  # 之后执行的所有SQL语句必须提交才生能效
            print('这里是检测过程')
            # 执行传入函数，把本连接的游标传进去用，结果接收过来并代替输出
            result = func(cursor, *args, **kwargs)
            # 一切正常，提交事务
            conn.commit()
            return result
        except pymysql.MySQLError as e:
            # 将MYSQL报错信息存入日志
            logger.debug(e)
            # 获取用户IP地址
            client_ip = request.remote_addr
            logger.debug(f'用户IP地址：{client_ip}')

            # 撤消之前的所有操作（只回滚本连接的事务，不影响别人）
            conn.rollback()
            return False
        finally:
            # 无论之前操作是否生效，此处收尾：归还连接到连接池（复用，不是真关闭）。
            # 用 finally 保证即使中途出错，连接也一定能还回池里，不会泄漏导致池耗尽。
            conn.close()

    return wrapper

@DBCatchError
def checkLogin(cursor, name, pwd):
    # 第一个参数 cursor 由装饰器注入（是本调用专属连接的游标）；
    # 真正调用时仍写 checkLogin(name, pwd) 即可，装饰器会自动补上 cursor。
    #
    # 实现登录验证
    # 这里用 class(班级) 当作“密码”来校验（教学示例）：name 对应 uname，pwd 对应 class。
    # mydb2509.student 没有 age 字段，故用 class 代替。
    # count(*) 命中数 > 0 即认为账号密码正确。
    cursor.execute('select count(*) as num from student where uname=%s and class=%s', (name, pwd))
    res = cursor.fetchone()

    if res['num'] > 0:
        return True
    else:
        return False


#  分页函数:
# （页码-1）*条数 = 切片法中的起始索引，
#  页码*条数     = 切片法中的结束索引，
def showPage(list1,page=1,everyPage=5):
    return list1[(page-1)*everyPage:page*everyPage]


# ============================================================
# 登录失败限流（Redis 计数器：INCR + EXPIRE）
# ============================================================
# 解决什么问题：登录接口不限次数 = 可以无限试密码（暴力破解）。
# 思路：同一个账号名，失败次数记在 Redis 的计数器里，
#       窗口（FAIL_WINDOW 秒）内失败满 FAIL_LIMIT 次，就暂时禁止再试。
#
# 为什么用 Redis 而不是 Python 变量：
#   1. 多个 Web 实例共享同一个计数器（本机变量只有自己看得见）；
#   2. INCR 是原子操作，100 个并发同时 +1 也不会丢计数；
#   3. EXPIRE 让窗口自动过期，不用自己写清理定时任务。
#
# 面试讲法："Redis 除了缓存还能当分布式计数器用——INCR 原子自增 +
#           EXPIRE 自动过期，就是最简单的滑动窗口限流雏形。"
FAIL_LIMIT = 5        # 窗口内允许的最大失败次数
FAIL_WINDOW = 600     # 限流窗口（秒），10 分钟


def login_too_many_fails(name):
    """查询该账号是否已被限流（失败次数达到上限且窗口未过期）。"""
    fails = redis_client.get(f'login_fail:{name}')
    blocked = fails is not None and int(fails) >= FAIL_LIMIT
    if blocked:
        logger.debug(f'登录限流命中：账号={name}，累计失败 {int(fails)} 次')
    return blocked


def record_login_fail(name):
    """记一次登录失败：先 SET NX EX 保证键一定带过期时间，再 INCR 计数。

    为什么要先 SET NX EX 再 INCR（而不是 INCR 后 EXPIRE）：
    INCR 和 EXPIRE 是两条命令，如果 INCR 之后进程崩溃，EXPIRE 没执行，
    这个计数器就永远不过期 = 账号被永久锁死。先 SET NX EX 一步保证
    "键存在则必带 TTL"，之后 INCR 只管加数，窗口不会被续期。
    （要绝对原子可以上 Lua 脚本或事务 MULTI/EXEC，这里 SET NX EX 已经够用。）
    """
    key = f'login_fail:{name}'
    redis_client.set(key, 0, nx=True, ex=FAIL_WINDOW)   # 键不存在才创建，且自带 10 分钟 TTL
    redis_client.incr(key)                              # 原子 +1


def clear_login_fails(name):
    """登录成功后清零计数（正常用户偶尔手滑不该被累计惩罚）。"""
    redis_client.delete(f'login_fail:{name}')


