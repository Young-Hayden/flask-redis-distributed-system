# 定时刷新 新浪/网易 新闻缓存的后台进程
# 和 redis_listen_news.py 一个模式：常驻后台，每隔一段时间删旧缓存、重新抓取写入。
# 用法：
#   1. 直接跑：python redis_listen_wangyi_sina.py
#   2. 或用 supervisor 托管（见 supervisor/myapp3.ini 示例）
# 前提：http_server.py（8000端口）必须在运行——新闻数据是从它的 / 和 /wangyi 接口取的。
#
# 分布式锁改造：这个守护进程可以部署多个副本（高可用），但没有锁时两个副本会在
# 同一秒醒来抢着刷缓存。现在每轮刷新先抢 Redis 锁（redis_lock.py），
# 抢到的干活，没抢到的本轮直接跳过——多副本之间不重复劳动、不互相覆盖。
from redis_pool import *
import cache_utils
from redis_lock import RedisLock
import json
import time
import urllib.request

import config

# 刷新间隔（秒）。新闻类数据不用太频繁，300秒=5分钟刷一次，
# 既保证新鲜度，也不会给新浪/网易服务器造成压力。
wait_time = 300


def refresh(prefix, url):
    """
    刷新一类新闻缓存：抢锁 -> 删旧 -> 从http接口取 -> 逐条写回
    :param prefix: 缓存键前缀，如 'sina_info' / 'wangyi_info'
    :param url:    http_server.py 提供的数据接口地址
    """
    # 每类新闻一把锁：锁名带 prefix，两类新闻互不干扰
    lock = RedisLock(f'refresh_{prefix}', expire=60, wait_timeout=0)
    if not lock.acquire():
        print(f'{prefix} 本轮跳过：另一个副本正在刷（分布式锁生效）')
        return

    try:
        # 先从接口取数据，取成功了才动缓存（接口挂了本轮跳过，旧缓存继续用）
        try:
            html_code = urllib.request.urlopen(url, timeout=15)
            news_list = json.load(html_code)
        except Exception as e:
            print(f'{prefix} 刷新失败，本轮跳过（请检查 http_server.py 是否在运行）: {e}')
            return

        # redis 操作也要包一层：redis 重启/抖动时跳过本轮，守护进程不能死
        # （教训：2026-08-14 redis 服务重启过一次，没包这层时进程直接被 ConnectionError 打死）
        try:
            # 删除旧缓存（SCAN 版删除，不再用阻塞的 keys()）
            cache_utils.cache_delete_pattern(f'{prefix}:*')

            # 用序号做键，逐条写入新数据（和 App.py 里 /sina_news 的缓存格式一致，
            # cache_set 自带 TTL+随机抖动，防止多类新闻同一秒集体过期）
            index = 1
            for row in news_list:
                cache_utils.cache_set(f'{prefix}:{index}', row)
                index = index + 1

            print(f'{prefix} 缓存刷新完成，共 {index - 1} 条')
        except Exception as e:
            print(f'{prefix} 写入缓存失败，本轮跳过（请检查 redis 是否在运行）: {e}')
    finally:
        # 无论刷没刷成，本轮结束都释放锁（with 语义，见 redis_lock.py）
        lock.release()


# 死循环：让进程常驻，定时刷新
# 加 __main__ 判断：这样别的脚本可以 import refresh() 单独用，不会一导入就卡进死循环
if __name__ == '__main__':
    while True:
        refresh('sina_info', f'http://{config.API_HOST}:{config.API_PORT}/')           # 新浪新闻
        refresh('wangyi_info', f'http://{config.API_HOST}:{config.API_PORT}/wangyi')  # 网易新闻
        # 设置间隔时间
        time.sleep(wait_time)
