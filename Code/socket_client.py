import socket

# 创建连接对象
client = socket.socket()

# 定义连接地址
ip_port = ('127.0.0.1',8888)
# 连接服务器
client.connect(ip_port)

while True:
    # 接收服务端消息
    data = client.recv(1024)
    # 打印接收的数据
    print(data.decode('utf-8'))

    # 让客户端主动给服务端发消息
    msg_input = input("请输入要发送的信息：") # 在此处进行阻断，直到按回车

    # 将客户端的消息发送给服务端
    client.send(msg_input.encode('utf-8'))

    # 判断是否终连接
    if msg_input == 'exit':
        break