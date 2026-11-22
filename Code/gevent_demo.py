'''
gevent库：多线程、协程库
gevent 是一个基于协程的 Python 网络库，它使用 greenlet 包作为底层实现。
协程允许你在单一线程内执行多个并发任务，这对于处理I/O密集型任务（
如网络请求、文件读写等）特别有用，因为它可以显著提高程序的效率和响应速度。
'''
# 安装gevent : pip install gevent
import gevent
# 引入时间函数
import time

# 正常执行协程需要按顺序执行，消耗时间比较长
# 通过引入猴子补丁，可以将协程改成异步执行，相当于多线程执行
from gevent import monkey
# 将协程从队列执行改为并列执行操作。
monkey.patch_all()

# 创建一任务（函数）
def work(msg):
    for i in range(10):
        print(i,msg)
        time.sleep(1)

# 通过协程执行任务
# gevent.spawn(work('你好')).join()
# 定义开始时间
start = time.time()

# 定义三个任务
w1 = gevent.spawn(work,'我是一号，请等待1秒')
w2 = gevent.spawn(work,'我是二号，请等待1秒')
w3 = gevent.spawn(work,'我是三号，请等待1秒')

# 将三个任务放在一个队列中，加入到协程任务中
# 启动并等待协程完成任务
gevent.joinall( [w1,w2,w3] )
# 定义结束时间
end = time.time()
# 输出时间差
print(end - start)