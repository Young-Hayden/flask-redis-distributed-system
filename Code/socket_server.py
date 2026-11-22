# 引入socket
import socket

# 默认连接方式是TCP
# 创建一个连接对象
sk = socket.socket()
# 设置服务端的地址和端口
ip_port = ('127.0.0.1',8888)
# 将连接设置ip_port与连接对象绑定
sk.bind(ip_port)
# 设置最大连接数
sk.listen(5)

# 开始执行服务程序
while True:
    # 在服务端输出提示信息
    print("正在等待连接.....")

    # 等待客户端连接
    conn,address = sk.accept() # 相当于input() 阻断在此处，直到有用户连接
    # 接上用户之后,给用户发送提示信息
    msg = '连接成功'
    # 将提示信息发送给客户端
    # python 3.x以上网络数据发送的格式都是byte类型
    # 如果发送的内容中有汉字的，需要进行编码（加密）
    conn.send(msg.encode('utf-8'))

    # 处理与客户端的实时通信
    while True:
        # 接收客户端传来的信息
        data = conn.recv(1024)   # 相当于input() 阻断在此处，直到有用户连接
        data = data.decode('utf-8')
        # 将客户端信息输出,需要将用户信息进行解码（解密）
        print("客户端：" + data)

        # 设置退出验证
        if data == 'exit':
            break

        # 给客户端发消息
        conn.send('您说的是:'.encode('utf-8') + data.encode())





