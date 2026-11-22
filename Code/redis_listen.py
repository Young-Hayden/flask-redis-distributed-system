# 本脚本是一个“缓存预热/同步”后台任务：
# 每隔一段时间，把 MySQL 中最新的学生数据刷写到 Redis，保证缓存与数据库一致。
# 典型用法：用 supervisor 单独托管这个进程，让它常驻后台定时刷新（见 项目根目录/supervisor）。
from redis_pool import *
from mysql_pool import *
import cache_utils
import json
# 引入时间函数
import time

# 死循环：让进程常驻，定时刷新缓存
while True:
    # 第一步：先清掉旧的缓存数据，避免残留过期记录（SCAN 版删除，不再用阻塞的 keys()）
    cache_utils.cache_delete_pattern('stu_info:*')
    # 第二步：从数据库中读取所有信息，存到redis里面
    cursor.execute('select id,uname,sex,class from student limit 5')
    res = cursor.fetchall()
    # 逐条写入缓存（cache_set 自带 TTL+随机抖动，防雪崩）
    for row in res:
        cache_utils.cache_set(f'stu_info:{row["id"]}', row)

    # 第三步：回读一次，确认缓存已写入
    keys = cache_utils.scan_keys('stu_info:*')
    print(keys)
    # 设置间隔时间：每隔 60 秒刷新一次缓存
    time.sleep(60)