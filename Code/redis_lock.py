'''
Redis 分布式锁
================
解决什么问题：多个进程/多台机器同时想干"同一件只能一个人干的事"。
本项目场景：缓存刷新守护进程部署 2 个副本（高可用）时，两个副本会在同一秒
醒来抢着刷缓存——谁后写完谁生效，浪费一倍抓取流量还可能写花数据。
加锁后：同一时刻只有一个副本真正干活，另一个副本这轮直接跳过。

为什么单机的 threading.Lock 不行：它只锁本进程内的线程；
另一台机器上的进程根本感知不到。所以锁本身必须放在一个
"大家都能访问的地方"——Redis，这就是"分布式锁"。

实现三要素（面试必背）：
1. 互斥：SET key token NX EX 秒 —— NX=不存在才能写（抢锁），EX=自带过期时间
2. 防误删：锁的值存一个随机 token（uuid），删锁时只删自己的锁
   ——否则 A 干得慢、锁过期被 B 拿走，A 干完后一把删掉 B 的锁，互斥就破了
3. 原子释放：比较 token 和删除必须一步完成（Lua 脚本），
   否则"查完是自己、还没删、锁恰好过期换了主人"的窗口照样误删

进阶话题（追问可能问到）：锁续期（看门狗）、Redlock 多节点、可重入。
本实现是最常用的单实例版，Redis 主从切换极端场景下可能丢锁（面试可以主动讲）。
'''
import uuid
import time

from redis_pool import redis_client

# Lua 脚本：GET 和 DEL 在 Redis 端一次性执行，中间不会插入别人的命令
# KEYS[1]=锁名  ARGV[1]=调用方自己的 token
_RELEASE_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


class RedisLock:
    """阻塞式获取（可选等待）的 Redis 分布式锁，支持 with 语法。"""

    def __init__(self, name: str, expire: int = 30, wait_timeout: float = 0.0):
        self.key = f'lock:{name}'
        # expire：锁自动过期秒数（持有者崩溃时锁不会永远卡死——"自愈"能力靠它）
        self.expire = expire
        # wait_timeout：抢不到锁最多等多久（秒）；0 表示不等待，抢不到立即失败
        self.wait_timeout = wait_timeout
        # token：本次持锁的身份证，release 时凭它证明"锁是我的"
        self.token = None

    def acquire(self) -> bool:
        self.token = uuid.uuid4().hex
        deadline = time.time() + self.wait_timeout
        while True:
            # NX：key 不存在才写入（谁写成功谁抢到锁）；EX：同时设置过期时间
            # 注意 SET NX EX 是一条命令，"抢锁+过期"原子生效，不会出现抢到了但没来得及设过期
            if redis_client.set(self.key, self.token, nx=True, ex=self.expire):
                return True
            if time.time() >= deadline:
                return False
            time.sleep(0.1)  # 抢不到就歇 100ms 再试（自旋）

    def release(self) -> bool:
        if self.token is None:
            return False
        # 必须 Lua：比较 token 和删除是原子操作，防"删掉别人的锁"
        released = redis_client.eval(_RELEASE_LUA, 1, self.key, self.token)
        self.token = None
        return released == 1

    # 让锁支持 with RedisLock(...) as lock: 语法，异常时也能保证释放
    def __enter__(self):
        acquired = self.acquire()
        if not acquired:
            return None  # 调用方判断 if lock: 决定干不干活
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False  # 不吞异常


if __name__ == '__main__':
    # 自测：两个连接抢同一把锁，只有一个成功
    lock = RedisLock('test_lock', expire=10)
    print('第一次抢锁:', lock.acquire())          # True
    other = RedisLock('test_lock', expire=10, wait_timeout=0.5)
    print('别人再抢同一把锁:', other.acquire())   # False
    print('释放后别人再抢:', lock.release(), other.acquire())  # True True
    other.release()
