'''
Locust 压测：对比"命中缓存"与"穿透到数据库"的性能差距
======================================================
启动：
    pip install locust
    locust -f bench/locustfile.py --host http://localhost:5000
    浏览器打开 http://localhost:8089 设置并发数开始

两个对比场景（压测报告里按名称分开统计）：
1. 命中缓存：/get_name?name=李军 —— 第一次之后数据已在 Redis，请求不再碰 MySQL
2. 穿透到库：同名请求，但每次先删掉缓存键，强制回源 MySQL
   —— 两者 QPS 差距就是"缓存的价值"，可以直接写进简历/README

另外附带首页任务模拟真实流量混合。
'''
from locust import HttpUser, task, between

import sys
import os
# 把 Code/ 目录加进搜索路径，才能复用项目的 config 和连接池
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Code'))

import config
from redis_pool import redis_client

# 压测对象：库里真实存在的一个学生（schema.sql 种子数据里的"李军"）
TEST_NAME = '李军'


class CacheUser(HttpUser):
    wait_time = between(0.1, 0.3)   # 每个虚拟用户两次请求之间随机等 0.1~0.3 秒

    @task(8)
    def home(self):
        """首页：列表缓存大部分时间是热的，模拟真实页面流量"""
        self.client.get('/', name='首页')

    @task(6)
    def point_query_cache_hit(self):
        """场景1：点查询，命中缓存（key: stu_name:李军）"""
        self.client.get(f'/get_name?name={TEST_NAME}', name='点查询_命中缓存')

    @task(2)
    def point_query_cache_miss(self):
        """场景2：点查询，先删缓存强制回源 MySQL（对照组）"""
        redis_client.delete(f'stu_name:{TEST_NAME}')
        self.client.get(f'/get_name?name={TEST_NAME}', name='点查询_穿透到库')
