from redis_pool import *
from mysql_pool import *
import json
# 引入时间函数
import time

while True:
    # 删除指定的数组序列变量
    keys = redis_client.keys('news_info:*')
    if len(keys) > 0:
        redis_client.delete(*keys)

    # 重新读取数据写入缓存
    cursor.execute('select id,title,content from news order by id desc limit 5')
    res = cursor.fetchall()

    # 通过循环将数据读出来，以字符串类型逐条存入缓入
    for row in res:
        # 定义一个变量名的键值，用来做（伪）列表主键
        key = f'news_info:{row["id"]}'
        # 定义变量值，将字典类型数据转成json
        value = json.dumps(row)
        # 将键和值以字符串变量的形式存入缓存
        redis_client.set(key, value)
    print('新闻数据更新完成')
    # 设置间隔时间
    time.sleep(60)
    