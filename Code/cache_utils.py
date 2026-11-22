'''
缓存工具统一封装
=================
把原来散落在 App.py 各路由里的缓存操作收拢成几个函数，并补上三个生产级要点
（面试常说的"缓存三件套"）：

1. SCAN 替代 KEYS：
   keys('stu_info:*') 一次扫全库、O(N) 阻塞——生产库百万键时会卡死整个 Redis。
   scan_iter 用游标分批扫，每次只看一小撮，随时能响应其他请求。

2. TTL + 随机抖动（防雪崩）：
   缓存不加过期时间 = 数据改了缓存永远是旧的；全加同一个过期时间 = 大量 key
   同一秒集体失效，请求瞬间全打到 MySQL（雪崩）。
   做法：基础 TTL + random 抖动，让过期时间摊开在一个区间里。

3. 空值缓存（防穿透）：
   查一个库里根本不存在的数据（恶意刷 / ID 碰撞），每次都穿到 MySQL。
   做法：查到"不存在"也往缓存写一个哨兵值 + 短 TTL，让后续请求被缓存挡住。
'''
import json
import random

import config
from redis_pool import redis_client

# 空值哨兵：代表"数据库里也没有这条数据"
EMPTY = '__EMPTY__'


def scan_keys(pattern: str) -> list:
    """按模式扫 key，替代 redis_client.keys()（阻塞大忌，见文件头注释）。"""
    return list(redis_client.scan_iter(match=pattern, count=100))


def cache_set(key: str, value, ttl: int = None) -> None:
    """把 Python 对象 json 序列化后写入缓存，带 TTL+随机抖动。

    :param value: 任意可 json 化的对象（dict/str/list）
    :param ttl:   基础过期秒数；None 时用 config.CACHE_DEFAULT_TTL
    """
    if ttl is None:
        ttl = config.CACHE_DEFAULT_TTL
    # 抖动：过期时间 = 基础值 ± [0, jitter)，把"同一秒集体过期"摊开
    real_ttl = ttl + random.randint(0, config.CACHE_TTL_JITTER)
    redis_client.setex(key, real_ttl, json.dumps(value, ensure_ascii=False))


def cache_get(key: str):
    """读缓存。返回：None=键不存在；EMPTY=空值哨兵；否则为反序列化后的对象。"""
    value = redis_client.get(key)
    if value is None:
        return None
    if value == EMPTY.encode('utf-8'):
        return EMPTY
    return json.loads(value)


def cache_delete_pattern(pattern: str) -> int:
    """按模式删缓存（原来 App.py 里的 delete(*keys) 写法），返回删除数量。"""
    keys = scan_keys(pattern)
    if keys:
        return redis_client.delete(*keys)
    return 0


def cache_set_empty(key: str) -> None:
    """写空值哨兵，短 TTL（config.CACHE_EMPTY_TTL），防止反复查不存在数据打穿数据库。"""
    redis_client.setex(key, config.CACHE_EMPTY_TTL, EMPTY)
