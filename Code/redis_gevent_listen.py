# 引入数据库和redis缓存
from mysql_pool import *
from redis_pool import *
import cache_utils

# 引入协程库
import gevent
# 引入猴子补丁
from gevent import monkey
# 将协程从队列执行改为并列执行操作。
monkey.patch_all()


# 引入json
import json

# 定义时间间隔变量
wait_time = 3

# 定义存储学生数据的函数
def save_student_redis():
    # 定义一个死循环
    while True:
        # 先删旧缓存再重灌（SCAN 版删除 + cache_set 带 TTL+抖动）
        cache_utils.cache_delete_pattern('stu_info:*')
        cursor.execute('select id,uname,sex,class from student order by id desc limit 5')
        res = cursor.fetchall()
        for row in res:
            cache_utils.cache_set(f'stu_info:{row["id"]}', row)
        print('学生数据更新完成')

        # 设置间隔时间
        gevent.sleep(wait_time)

# 定义存储新闻数据的函数
def save_news_redis():
    # 定义一个死循环
    while True:
        # 先删旧缓存再重灌（SCAN 版删除 + cache_set 带 TTL+抖动）
        cache_utils.cache_delete_pattern('news_info:*')
        cursor.execute('select id,title,content from news order by id desc limit 5')
        res = cursor.fetchall()
        for row in res:
            cache_utils.cache_set(f'news_info:{row["id"]}', row)
        print('新闻数据更新完成')
        # 设置间隔时间
        gevent.sleep(wait_time)


# 定义任务队列
work_student_redis = gevent.spawn(save_student_redis)
work_news_redis    = gevent.spawn(save_news_redis)

# 将任务队列加入协程任务中等待执行
gevent.joinall(  [ work_student_redis , work_news_redis ]  )
