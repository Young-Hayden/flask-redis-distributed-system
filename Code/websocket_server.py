# 安装websockets：pip install websockets
# 引入websockets
import websockets
# 引入异步模块,实现协程的功能。
import asyncio

# 引入正则表达式模块 RE库
import re

# 引入数据库连接池
from mysql_pool import *
'''
python 实现websocket应用的主要原理依赖的异步，在定义函数时，
可以调用async构成异步编程的核心语法。
await是用来实现异步等待的关键字，在执行一些函数或是对象时，
通过await可以实现异步任务。
'''
# 定义一个协程类型的功能函数，用来接收和处理客户端的数据
async def echo(websocket):
    # 在服务端输出入提示词
    print('用户端已连接')
    # 修 bug：原来用的是 mysql_pool 里的全局 cursor——多个 websocket 连接是并发协程，
    # 会互相踩 SQL 结果。现在每个连接从池里取自己的独立连接，用完归还。
    conn = pool.connection()
    cursor = conn.cursor()
    # 通过try测试的方式验证传入的websocket是否有效，是否有用户连接入
    try:
        # 通过协程实现多用户信息验证
        async for message in websocket:
            print(f'客户端：{message}')
            # 给客户端回消息
            # respone = f'服务端：收到您发的{message}'
            user_recv = ''

            # 用正则表达式定义匹配规则，用来检测客户端传过来的信息
            # 筛选用户信息中是否包含：XXX在吗？
            # .*? 表示匹配任意字符
            # ()是表示如果筛选到数据，将括号中信息提取出来
            # .*?在吗？ 表示将：XXX在吗？ 一整句都提取出来
            info_check = '(.*?)在吗'
            # 将正则表达式转成re所能识别的格式
            re_txt = re.compile(info_check)
            # 通过re_txt来解析message的信息是否符合条件
            username = re_txt.findall(message)
            print(username)
            if len(username)>0:
                username = username[0]
                # 在数据库查找是否有此用户
                # 修 bug：字段名是 uname（表里没有 stu_name）；参数必须传元组 (username,)，
                # 原来 (username) 只是加了个括号的字符串，pymysql 会报参数数量错误
                cursor.execute("select id,uname,sex,class from student where uname=%s",(username,))
                res = cursor.fetchone()
                if res is not None:
                    user_recv = f'{res["uname"]}在家，您找他有什么事？'
                else:
                    user_recv = '您所找的人不存在'
            else:
                # 重新定义规则
                # 筛选客户端信息中是否包含：有没有钱，借钱之类的话
                info_check = '.*?有.*?钱.*?|.*?借.*?钱.*?'
                # 将正则表达式转成re所能识别的格式
                re_txt = re.compile(info_check)
                # 通过re_txt来解析message的信息是否符合条件
                username = re_txt.findall(message)
                if len(username) > 0:
                    user_recv = '您拨打的电话已关机'
                else:
                    user_recv = 'ok'
            await websocket.send(user_recv)
    except Exception as e:
        print('连接出错或客户端断开:', e)
    finally:
        # 修 bug：连接用完一定归还连接池（原来的全局 cursor 永不归还，还会互相串数据）
        cursor.close()
        conn.close()

# 定义服务端地址和端口（走统一配置 config.py）：
import config
host = config.WS_HOST
port = config.WS_PORT

# 定义服务端运行的主函数
async def main():
    async with websockets.serve(echo,host=host,port=port):
        print(f'服务端地址：ws://{host}：{port}')
        # 通过异步模块执行websockets服务，Future()表示永久执行。
        await asyncio.Future()

# 开始执行服务
if __name__ =="__main__":
    # 通过asyncio来执行主函数main()
    asyncio.run(main())