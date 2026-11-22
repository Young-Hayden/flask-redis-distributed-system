'''
pytest 共享配置：让测试能 import Code/ 下的模块，并自动清理测试产生的 Redis 键。

为什么 chdir 到 Code/：checkFunc.py 在 import 时执行 fileConfig('logging.conf')，
用的是相对路径——不在 Code/ 下运行会直接 FileNotFoundError。
'''
import os
import sys

CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Code'))
sys.path.insert(0, CODE_DIR)
os.chdir(CODE_DIR)

import pytest


@pytest.fixture(autouse=True)
def clean_test_keys():
    """每个用例跑完后清理本组测试写入的 Redis 键（只删 test 前缀，不碰业务数据）。"""
    from redis_pool import redis_client
    yield
    patterns = ('test:*', 'cache:test:*', 'rebuild:test*',
                'stu_name:测试*', 'login_fail:测试*', 'lock:test*')
    keys = []
    for pattern in patterns:
        keys.extend(redis_client.scan_iter(pattern))
    if keys:
        redis_client.delete(*keys)
