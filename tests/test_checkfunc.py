'''业务函数单测：分页切片、登录失败限流计数器。'''
import checkFunc


def test_showpage_middle():
    """第 2 页、每页 3 条 → 切片 [3:6]。"""
    data = list(range(10))
    assert checkFunc.showPage(data, page=2, everyPage=3) == [3, 4, 5]


def test_showpage_beyond_end():
    """页码超出范围返回空列表，不报错。"""
    assert checkFunc.showPage(list(range(10)), page=99, everyPage=3) == []


def test_rate_limit_blocks_at_5th_fail():
    """失败 5 次触发限流；4 次不触发；成功清零后解除。"""
    name = '测试限流账号A'
    checkFunc.clear_login_fails(name)
    for _ in range(4):
        checkFunc.record_login_fail(name)
    assert checkFunc.login_too_many_fails(name) is False
    checkFunc.record_login_fail(name)                       # 第 5 次
    assert checkFunc.login_too_many_fails(name) is True
    checkFunc.clear_login_fails(name)
    assert checkFunc.login_too_many_fails(name) is False


def test_rate_limit_counter_has_ttl():
    """计数器必须带过期时间（10 分钟窗口），否则账号会被永久锁死。"""
    name = '测试限流账号B'
    checkFunc.record_login_fail(name)
    from redis_pool import redis_client
    ttl = redis_client.ttl(f'login_fail:{name}')
    assert 0 < ttl <= checkFunc.FAIL_WINDOW
    checkFunc.clear_login_fails(name)


def test_rate_limit_window_not_extended():
    """窗口内多次失败不续期：TTL 只减不增（SET NX EX 保证键只在第一次创建）。"""
    name = '测试限流账号C'
    checkFunc.clear_login_fails(name)
    checkFunc.record_login_fail(name)
    from redis_pool import redis_client
    ttl_1 = redis_client.ttl(f'login_fail:{name}')
    checkFunc.record_login_fail(name)
    ttl_2 = redis_client.ttl(f'login_fail:{name}')
    assert ttl_2 <= ttl_1            # 第二次失败没有把窗口重置回 600
    checkFunc.clear_login_fails(name)
