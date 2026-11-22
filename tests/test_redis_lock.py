'''分布式锁单测：互斥、token 防误删、释放后可再抢。需要本机 Redis 在运行。'''
from redis_lock import RedisLock


def test_mutual_exclusion():
    """同一把锁同时只能被一个持有者拿到。"""
    lock_a = RedisLock('test:mutex', expire=10, wait_timeout=0)
    lock_b = RedisLock('test:mutex', expire=10, wait_timeout=0)
    assert lock_a.acquire() is True
    assert lock_b.acquire() is False      # A 持有期间 B 抢不到
    lock_a.release()
    assert lock_b.acquire() is True       # 释放后 B 能拿到
    lock_b.release()


def test_wrong_token_cannot_release():
    """别人的 token 删不掉锁（防误删的关键）。"""
    lock_a = RedisLock('test:token', expire=10)
    assert lock_a.acquire() is True

    impostor = RedisLock('test:token', expire=10)
    impostor.token = '伪造的token'         # 模拟 B 拿着假 token 来释放
    assert impostor.release() is False    # Lua 比较失败，锁还在

    assert lock_a.release() is True       # 真 token 才能释放


def test_wait_timeout():
    """wait_timeout 内抢不到就返回 False，而不是死等。"""
    lock_a = RedisLock('test:wait', expire=10)
    assert lock_a.acquire() is True
    lock_b = RedisLock('test:wait', expire=10, wait_timeout=0.3)
    assert lock_b.acquire() is False
    lock_a.release()


def test_lock_auto_expire_key():
    """锁键必须带 TTL（持有者崩溃也能自愈），TTL 不超过 expire 值。"""
    lock = RedisLock('test:expire', expire=7)
    assert lock.acquire() is True
    from redis_pool import redis_client
    ttl = redis_client.ttl('lock:test:expire')
    assert 0 < ttl <= 7
    lock.release()
