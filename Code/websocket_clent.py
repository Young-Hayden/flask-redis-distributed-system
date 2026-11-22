# 安装websockets：pip install websockets
# 引入websockets
import websockets
# 引入异步模块,实现协程的功能。
import asyncio

# 定义一个发送消息的函数
async def send_message():
    # 定义连接地址,此地址可以应用网页端
    url = 'ws://localhost:8888'
    try:
        async with websockets.connect(url) as websocket:
            print('已连接服务器')
            while True:
                # 定义用户输入的信息
                message = input("请输入：")

                # 将用户消息发送到服务端
                await websocket.send(message)

                # 接收服务端返回值
                response = await websocket.recv()
                # 输出服务端消息
                print(f'服务端：{response}')
    except Exception as e:
        print(f'发送信息失败，错误：{e}')


# 启动客户端
if __name__=="__main__":
    asyncio.run(send_message())


