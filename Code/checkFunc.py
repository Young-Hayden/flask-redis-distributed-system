import pymysql
#引入数据库连接池
import mysql_pool

#引入request用来接收外部传值
from flask import request

#引入日志
import logging
import logging.config
#配置日志配置文件
logging.config.fileConfig('logging.conf')
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


