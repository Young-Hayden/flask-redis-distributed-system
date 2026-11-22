'''
缓存工具统一封装
=================
把原来散落在 App.py 各路由里的缓存操作收拢成几个函数，并补上生产级要点
（面试常说的"缓存四防"）：

1. SCAN 替代 KEYS（防阻塞）：
   keys('stu_info:*') 一次扫全库、O(N) 阻塞——生产库百万键时会卡死整个 Redis。
   scan_iter 用游标分批扫，每次只看一小撮，随时能响应其他请求。

2. TTL + 随机抖动（防雪崩）：
   缓存不加过期时间 = 数据改了缓存永远是旧的；全加同一个过期时间 = 大量 key
   同一秒集体失效，请求瞬间全打到 MySQL（雪崩）。
   做法：基础 TTL + random 抖动，让过期时间摊开在一个区间里。

3. 空值缓存（防穿透）：
   查一个库里根本不存在的数据（恶意刷 / ID 碰撞），每次都穿到 MySQL。
   做法：查到"不存在"也往缓存写一个哨兵值 + 短 TTL，让后续请求被缓存挡住。

4. 互斥锁回源（防击穿）：
   某个热点 key 过期的瞬间，N 个并发请求同时发现 miss，全部冲向 MySQL。
   做法：miss 后先抢 Redis 锁（redis_lock.py），只有抢到的那个请求回源，
   其余请求短暂等待后重读缓存；回源前再查一次缓存（双重检查），
   防止等锁期间数据已被前一个请求回填、自己又重复回源。
'''
import json
import random
import time

import config
from redis_pool import redis_client
from redis_lock import RedisLock

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


# ============================================================
# 防击穿：互斥锁回源（读路径的 Cache-Aside 完整版）
# ============================================================
def cache_get_or_load(key: str, loader, ttl: int = None):
    """单 key 的缓存读：命中直接返回；miss 后抢锁回源（防击穿）。

    :param loader: 回源函数（查 MySQL），返回 None 表示数据不存在 → 自动写空值哨兵
    :return: 缓存值 / 空值哨兵 EMPTY / None（锁竞争下短暂 miss，调用方需兜底）
    """
    val = cache_get(key)
    if val is not None:
        return val
    # miss：抢锁。抢不到说明别的请求正在回源，稍等重读缓存即可
    lock = RedisLock(f'cache:{key}', expire=10, wait_timeout=1.5)
    if not lock.acquire():
        time.sleep(0.05)
        return cache_get(key)
    try:
        # 双重检查（Double-Check）：等锁期间缓存可能已被前面的请求回填
        val = cache_get(key)
        if val is None:
            val = loader()
            if val is None:
                cache_set_empty(key)     # 顺手把防穿透也做了
                val = EMPTY
            else:
                cache_set(key, val, ttl)
        return val
    finally:
        lock.release()


def cache_list_get_or_rebuild(pattern: str, rebuild, lock_name: str) -> list:
    """列表缓存的防击穿读：SCAN 到数据直接返回；缓存为空则抢锁，只放一个请求重建。

    :param rebuild: 重建函数，返回 [(key, value), ...]（内部自己查 MySQL）
    :param lock_name: 锁名后缀，如 'stu' / 'news'，不同列表互不干扰
    :return: 值列表（极端竞争下可能为空列表，调用方可用页面兜底）
    """
    keys = scan_keys(pattern)
    if keys:
        return [cache_get(k) for k in keys]

    lock = RedisLock(f'rebuild:{lock_name}', expire=10, wait_timeout=1)
    if not lock.acquire():
        # 没抢到锁：别人正在重建，稍等重读
        time.sleep(0.1)
        keys = scan_keys(pattern)
        return [cache_get(k) for k in keys]

    try:
        # 双重检查：等锁期间可能已被重建
        keys = scan_keys(pattern)
        if keys:
            return [cache_get(k) for k in keys]
        pairs = rebuild()
        for k, v in pairs:
            cache_set(k, v)
        return [v for _, v in pairs]
    finally:
        lock.release()
