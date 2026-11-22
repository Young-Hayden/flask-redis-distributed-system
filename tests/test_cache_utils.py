'''缓存工具单测：读写往返、TTL 抖动、空值防穿透、互斥锁回源（防击穿）。'''
import json

import cache_utils
from redis_pool import redis_client


def test_cache_set_get_roundtrip():
    """写入的 Python 对象能原样读回（json 序列化往返）。"""
    data = {'id': 1, 'uname': '测试同学', 'sex': '男', 'class': '2511班'}
    cache_utils.cache_set('test:roundtrip', data)
    assert cache_utils.cache_get('test:roundtrip') == data


def test_ttl_has_jitter(monkeypatch):
    """TTL 必须落在 [基础值, 基础值+抖动上限] 区间内（防雪崩的核心保证）。"""
    base, jitter = 100, 50
    monkeypatch.setattr(cache_utils.config, 'CACHE_TTL_JITTER', jitter)
    cache_utils.cache_set('test:ttl', 'x', ttl=base)
    ttl = redis_client.ttl('test:ttl')
    assert base <= ttl <= base + jitter


def test_missing_key_returns_none():
    assert cache_utils.cache_get('test:no_such_key') is None


def test_get_or_load_loader_called_once():
    """命中后不再回源：loader 只应被调用一次。"""
    calls = []

    def loader():
        calls.append(1)
        return {'id': 9, 'uname': '测试回源'}

    first = cache_utils.cache_get_or_load('test:or_load', loader, ttl=60)
    second = cache_utils.cache_get_or_load('test:or_load', loader, ttl=60)
    assert first == second == {'id': 9, 'uname': '测试回源'}
    assert len(calls) == 1               # 第二次走缓存，loader 没有再执行


def test_get_or_load_empty_value():
    """loader 返回 None → 写空值哨兵（防穿透），后续请求拿到 EMPTY 而不是再回源。"""
    calls = []

    def loader():
        calls.append(1)
        return None                      # 模拟"查无此人"

    first = cache_utils.cache_get_or_load('test:empty', loader)
    second = cache_utils.cache_get_or_load('test:empty', loader)
    assert first == cache_utils.EMPTY
    assert second == cache_utils.EMPTY
    assert len(calls) == 1               # 空值被缓存，第二次不再回源
    # 哨兵带短 TTL，不会永久占位
    assert 0 < redis_client.ttl('test:empty') <= 30 + 60


def test_list_rebuild_with_lock():
    """列表缓存 miss 时重建：rebuild 只执行一次，且写入的键能被读回。"""
    rebuild_calls = []

    def rebuild():
        rebuild_calls.append(1)
        return [(f'test:list:{i}', {'id': i, 'v': f'数据{i}'}) for i in range(3)]

    first = cache_utils.cache_list_get_or_rebuild('test:list:*', rebuild, 'teststu')
    second = cache_utils.cache_list_get_or_rebuild('test:list:*', rebuild, 'teststu')
    assert len(first) == 3 and len(second) == 3
    assert len(rebuild_calls) == 1       # 第二次 SCAN 已命中，不再重建
    assert {r['id'] for r in second} == {0, 1, 2}


def test_scan_keys_finds_written_keys():
    """SCAN 能扫到刚写入的键（替代 KEYS 的行为一致性）。"""
    redis_client.set('test:scan:1', 'a')
    redis_client.set('test:scan:2', 'b')
    keys = cache_utils.scan_keys('test:scan:*')
    assert len(keys) == 2
