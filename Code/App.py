'''
Flask
Flask是一个使用Python编写的轻量级Web应用框架，
是仅次于django国内最通用的两大Web应用框架之一，
相比django，Flask更简单便捷，适应用于初学者，
它旨在快速开发小型应用，但也适用于构建更复杂的应用。

安装：pip install flask
'''
# 引入Flask框架
# 引入flask框架中的request
# 引入redirect
# 引入render_template模块，用于将HTML网页渲染到前端。
# 引入render_template之后，在项目根目录创建两个文件夹：templates，static
# templates:是用来放HTML网页的,网页中的首页的命名：index.html   default.html
# static: 是用来放静态资源的
# 将HTML网页模板放入templates。
# 引入session模块
from flask import Flask,request,redirect,render_template,session
# 直连数据库的实例=======================
# 引入数据库文件
# import mysql_db
# # 创建一个游标对象
# cursor = mysql_db.cursor
# from mysql_db import *
# 直连数据库的实例=======================

# 数据库连接池的实例=======================
from mysql_pool import *
import mysql_pool   # 显式引入模块本身：下文要用 mysql_pool.pool，避免和 redis_pool 的 pool 撞名
import json

# 创建对象
app = Flask(__name__,static_url_path='/')

# 设置session的加密设置，信息可以自己设定
# 从统一配置取（.env/环境变量可覆盖）；没设置时用随机值兜底，
# 但随机值每次重启都变，会导致已登录用户全部失效，生产务必在 .env 里固定 SECRET_KEY
import os
import config
app.secret_key = config.SECRET_KEY or os.urandom(24)

# 定义一个全局变量
school_name = '指针2509&2511&2512暑期集训'
# 定义一个字典类型
school_info = {
    'school_name':'指针科技',
    'address':'总部大厦B座',
    'tel':'138XXXXXXX'
}

# 引入redis连接池
from redis_pool import *

# ===== 服务端 Session（存 Redis）=====
# 原来 Flask 的 session 其实存在【浏览器 cookie】里（签名防篡改，但数据在客户端），
# 问题：数据太大会撑爆 cookie；多实例部署时每台机器的 secret_key 不同就互相不认。
# 现在改为：cookie 里只放一个 session_id，真正的 session 数据存 Redis——
# 这就是"分布式 Session 共享"：任意一台 Web 实例都能从 Redis 读到同一个登录态。
from flask_session import Session
app.config['SESSION_TYPE'] = 'redis'          # 后端存储用 redis
app.config['SESSION_REDIS'] = redis_client    # 复用 redis_pool.py 里那个带连接池的客户端
Session(app)

# 缓存工具（scan 替代 keys / TTL+抖动 / 空值防穿透，见 cache_utils.py 文件头）
import cache_utils

# 调用登录验证函数
import checkFunc

# ===== 每请求独立数据库连接（P0优化）=====
# 问题：原来所有请求共用 mysql_pool 里的全局 conn/cursor，
#       Flask 多线程并发时，两个请求的SQL结果会互相串，事务也会互相踩。
# 方案：每个请求第一次用数据库时，从连接池取一个【独立连接】，存在 flask.g 里；
#       请求结束后（无论正常返回还是报错）由 teardown_request 自动归还连接池。
from flask import g

def get_db_cursor():
    # 获取当前请求专属的 (conn, cursor)；同一请求内多次调用复用同一个连接
    # 注意必须写 mysql_pool.pool：本文件里 from redis_pool import * 也有一个 pool，
    # 裸写 pool 会拿到 redis 的连接池（之前直接报 AttributeError 的原因）
    if 'db_conn' not in g:
        g.db_conn = mysql_pool.pool.connection()      # 从MySQL连接池取一个独立连接
        g.db_cursor = g.db_conn.cursor()
    return g.db_conn, g.db_cursor

@app.teardown_request
def close_db(exception=None):
    # 请求结束后把连接归还连接池（close 不是真关闭，是还给池子复用）
    conn = g.pop('db_conn', None)
    if conn is not None:
        conn.close()

# 设置路由显示信息
# 路由：指URL网址的地址层次，默认首页/
@app.route('/')
def hello():
    # 在首页中调用搜索网页模板
    # 向模板中传参数

    # 取当前请求的独立数据库连接
    conn, cursor = get_db_cursor()
    # 从数据库连接池中读取数据（完整字段，单独存 stu_info，不再被下面的缓存逻辑覆盖）
    cursor.execute('select id,uname,sex,class from student order by id desc limit 5')
    stu_info = cursor.fetchall()

    # 缓存三件套改造：SCAN 替代 KEYS、写缓存带 TTL+抖动（防雪崩），见 cache_utils.py
    keys = cache_utils.scan_keys('stu_info:*')
    # 判断keys的长度，如果为0，则表示没有数据
    if len(keys) == 0:
        # 直接用上面查出来的 stu_info 写入缓存（不用再查一遍数据库）
        for row in stu_info:
            cache_utils.cache_set(f'stu_info:{row["id"]}', row)
        print('从数据库中来')
    else:
        print('从缓存中来')
    # 从缓存中将指定多行数据取出来==============================
    stu_list = []
    for key_i in keys:
        stu_list.append(cache_utils.cache_get(key_i))

    # redis 的 keys() 返回顺序不固定，按 id 倒序排一下，保证“最新5条”顺序稳定
    stu_list.sort(key=lambda x: x['id'], reverse=True)

    # stu_list就可以应用到项目中了。
    # print(stu_list)
    # 从缓存中将指定多行数据取出来==============================

    return render_template('index.html',school_name=school_name,stu_info=stu_info,stu_list=stu_list)

@app.route('/aboutus')
def aboutus():
    # 在首页中调用搜索网页模板
    # 向模板中传参数
    # 多个参数中间用逗号隔开
    about_info = '关于我们'
    # 字典类型数据传值
    # 1、拆解字典
    # return render_template('about.html',school_name=school_info['name'],address=school_info['address'],tel=school_info['tel'])
    # 2、解包：
    # 3、在模板中使用for循环

    # 定义一个用户字典变量
    user_info ={}

    if session.get('user') is not None:
        # 通过session中的user从redis中读取用户信息
        uname = redis_client.hget(session.get('user'),'uname').decode('utf-8')
        sex = redis_client.hget(session.get('user'), 'sex').decode('utf-8')
        class_ = redis_client.hget(session.get('user'), 'class').decode('utf-8')
        user_info ={
            'uname':uname,
            'sex':sex,
            'class':class_
        }
    return render_template('about.html',school=school_info,user_info=user_info,**school_info)

# 用户登录
@app.route('/login')
def login():
    # 判断登录状态，取session值，如果不为空，则直接跳转
    if session.get('user') is not None:
        return redirect('/aboutus')
    else:
        return render_template('login.html',school_name=school_name)

# 验证登录
# 接收Post传值，在路由地址后面加,methods=['POST']
@app.route('/rev_post',methods=['POST'])
def rev_post():
    # 接收post值，用的是request.form['参数值']
    name = request.form['name']
    pwd = request.form['pwd']

    # 调用登录验证函数
    res = checkFunc.checkLogin(name,pwd)

    '''
    缓存：临时存储的信息，用来记录系统应用时需要记录的一些临时信息。
    1、session: 当网页打开时，可以记录的信息，如果网页关闭，信息自动清除。
    2、cookie: 存储在浏览器本地，可以设置有效期，只要记录不删除不过期，则一直有效。
    3、redis: 缓存数据库的一种，用来存储临时数据，可以实现网络共享。
    '''

    # 开始调用session
    if res:
        # 登录成功，将信息存入session
        session['user'] = name
        # 密码不写入 session（明文存进 cookie 有泄露风险）

        # 获取session值
        username = session.get('user')
        # return '登录成功'
        # 直接跳转到首页
        # return redirect('/')
        # alert() javascript弹出框
        # location.href 在当前页跳转到指定的页。

        # 从数据库读取用户信息存入redis（不取 birthday，date 类型 redis 无法直接存）
        # 取当前请求的独立数据库连接
        conn, cursor = get_db_cursor()
        cursor.execute('select id,uname,sex,class from student where uname=%s and class=%s', (name, pwd))
        res = cursor.fetchone()
        # 用哈希（字典类型）存储用户数据
        redis_client.hset(res['uname'], mapping=res)

        # 防JS注入：用户名经 json.dumps 转成安全的JS字符串字面量（引号/反斜杠会被转义），
        # 并把 < 转成 <，防止恶意用户名里的 </script> 提前闭合标签
        username_js = json.dumps(username, ensure_ascii=False).replace('<', '\\u003c')
        return f'<script>alert("欢迎："+{username_js}+"，登录成功");location.href="/aboutus";</script>'
    else:
        return '<script>alert("账号密码错误,请重新登录");location.href="/login";</script>'

# 退出登录
@app.route('/login_out')
def login_out():
    # 未登录时 session.get('user') 是 None，先判空再删缓存，否则 delete(None) 会报错
    user = session.get('user')
    if user is not None:
        redis_client.delete(user)
    # 清除所有缓存
    session.clear()
    return redirect('/aboutus')


# 录入学生信息
@app.route('/add_student')
def add_student():
    # 判断登录状态，取session值，如果为空，跳回到登录
    if session.get('user') is None:
        return '<script>alert("登录信息为空,请重新登录");location.href="/login";</script>'
    else:
        return render_template('add_student.html',school_name=school_name)

# 保存学生信息
@app.route('/save_student',methods=['POST'])
def save_student():
    # 接收学生信息
    uname = request.form['uname']
    sex = request.form['sex']
    class_ = request.form['class']
    # 取当前请求的独立数据库连接
    conn, cursor = get_db_cursor()
    # 验证数据表中是否有相同信息
    cursor.execute('select * from student where uname=%s and sex=%s and class=%s',(uname,sex,class_))
    res = cursor.fetchone()
    # 如果查询结果不为空，则返回录入页面。
    if res is not None:
        return '<script>alert("学生信息已存在，请重新录入");location.href="/add_student";</script>'
    else:
        try:
            cursor.execute('insert into student(uname,sex,class)values(%s,%s,%s)',(uname,sex,class_))
            # 提交事务：连接池默认不自动提交，没有这句 insert 不会真正写入数据库
            conn.commit()
            # 更新缓存：先删旧键（SCAN 版删除），再回填最新 5 条（cache_set 自带 TTL+抖动）
            cache_utils.cache_delete_pattern('stu_info:*')
            cursor.execute('select id,uname,sex,class from student order by id desc limit 5')
            res = cursor.fetchall()
            for row in res:
                cache_utils.cache_set(f'stu_info:{row["id"]}', row)
            # 更新缓存之后，跳转到首页，查看结果
            return '<script>alert("添加成功");location.href="/";</script>'
        except pymysql.MySQLError as e:
            print(e)
            return '<script>alert("信息录入失败，请重新录入");location.href="/add_student";</script>'

# 新闻展示页面
@app.route('/news_list')
def news_list():
    # 取当前请求的独立数据库连接
    conn, cursor = get_db_cursor()
    # 从缓存中读取数据

    # 从数据库中读取所有数据逐条写入缓存，并从缓存中读出来=====================
    keys = cache_utils.scan_keys('news_info:*')
    # 判断keys的长度，如果为0，则表示没有数据
    if len(keys) == 0:
        # 从数据库中读取所有信息，存到redis里面
        cursor.execute('select id,title,content from news order by id desc limit 5')
        res = cursor.fetchall()
        for row in res:
            cache_utils.cache_set(f'news_info:{row["id"]}', row)
        # 在这里重新扫一遍缓存键
        keys = cache_utils.scan_keys('news_info:*')
        print('从数据库中来')
    else:
        print('从缓存中来')
    # 从缓存中将指定多行数据取出来==============================
    # 定义一个学生列表变量
    news_list = []
    for key_i in keys:
        news_list.append(cache_utils.cache_get(key_i))

    # redis 的 keys() 返回顺序不固定，按 id 倒序排一下
    news_list.sort(key=lambda x: x['id'], reverse=True)

    return render_template('news_list.html',news_list=news_list)


# 添加新闻
@app.route('/add_news')
def add_news():
    # 判断登录状态，取session值，如果为空，跳回到登录
    if session.get('user') is None:
        return '<script>alert("登录信息为空,请重新登录");location.href="/login";</script>'
    else:
        return render_template('add_news.html',school_name=school_name)


# 保存新闻信息
@app.route('/save_news',methods=['POST'])
def save_news():
    # 接收新闻信息
    title = request.form['title']
    content = request.form['content']
    # 取当前请求的独立数据库连接
    conn, cursor = get_db_cursor()
    # 验证数据表中是否有相同信息
    cursor.execute('select * from news where title=%s and content=%s',(title,content))
    res = cursor.fetchone()
    # 如果查询结果不为空，则返回录入页面。
    if res is not None:
        return '<script>alert("新闻信息已存在，请重新录入");location.href="/add_news";</script>'
    else:
        try:
            cursor.execute('insert into news(title,content)values(%s,%s)',(title,content))
            conn.commit()
            # 更新缓存：删旧回填（SCAN 版），cache_set 自带 TTL+抖动
            cache_utils.cache_delete_pattern('news_info:*')
            cursor.execute('select id,title,content from news order by id desc limit 5')
            res = cursor.fetchall()
            for row in res:
                cache_utils.cache_set(f'news_info:{row["id"]}', row)
            # 更新缓存之后，跳转到首页，查看结果
            return '<script>alert("添加成功");location.href="/news_list";</script>'
        except pymysql.MySQLError as e:
            print(e)
            return '<script>alert("信息录入失败，请重新录入");location.href="/add_news";</script>'

@app.route('/edit_news/<id>')
def edit_news(id):
    if id is not None and id.isdigit():
        id = int(id)
        # 取当前请求的独立数据库连接
        conn, cursor = get_db_cursor()
        # 根据ID查询相关内容
        cursor.execute('select * from news where id=%s',(id,))
        news_info = cursor.fetchone()
        return render_template('edit_news.html',news_info=news_info,school_name=school_name)
    else:
        return '<script>alert("参数错误");location.href="/news_list";</script>'

# 保存修改后的新闻信息
@app.route('/save_edit_news',methods=['POST'])
def save_edit_news():
    # 接收新闻信息
    id = request.form['id']
    title = request.form['title']
    content = request.form['content']
    # 取当前请求的独立数据库连接
    conn, cursor = get_db_cursor()
    try:
        cursor.execute('update news set title=%s , content=%s where id=%s',(title,content,id))
        conn.commit()
        # 更新缓存：删旧回填（SCAN 版），cache_set 自带 TTL+抖动
        cache_utils.cache_delete_pattern('news_info:*')
        cursor.execute('select id,title,content from news order by id desc limit 5')
        res = cursor.fetchall()
        for row in res:
            cache_utils.cache_set(f'news_info:{row["id"]}', row)
        # 更新缓存之后，跳转到首页，查看结果
        return '<script>alert("修改成功");location.href="/news_list";</script>'
    except pymysql.MySQLError as e:
        print(e)
        return '<script>alert("参数错误");location.href="/news_list";</script>'


# post传值
@app.route('/search')
def search():
    return render_template('search_get.html',school_name=school_name)


'''
网址传参：
get传值：
1、明文传值：http://127.0.0.1:5000/?name=tom
2、伪静态传值：http://127.0.0.1:5000/tom   *************
post传值:
隐式传值，所传参数在URL网址不会有体现，这样更安全。

用途：
1、post:带有安全性的数据传递要用post，注册、登录、验证码之类。
2、get: 带有网址标识性的信息，要用get的传值
'''
# 定义第二个页：明文传值
@app.route('/get_name')
def get_name():
    # request.args.get('name','备用值') 备用值是当get获取None值时，显示此值。
    name = request.args.get('name','李军')

    # 缓存防穿透示例（点查询的 Cache-Aside，键：stu_name:{名字}）=====================
    # 先查缓存 → 命中直接返回；未命中才查库，并把结果（包括"查无此人"）写进缓存
    key = f'stu_name:{name}'
    cached = cache_utils.cache_get(key)
    res = None
    if cached is not None:
        # 命中"空值哨兵"：库里根本没这个人，直接回复——请求打不到 MySQL（防穿透）
        if cached == cache_utils.EMPTY:
            return '用户不存在（缓存拦截）'
        res = cached
        print('get_name 从缓存中来')
    else:
        # 取当前请求的独立数据库连接（不查 birthday，date 类型 Redis 存不了）
        conn, cursor = get_db_cursor()
        cursor.execute('select id,uname,sex,class from student where uname = %s',(name,))
        res = cursor.fetchone()
        if res is not None:
            cache_utils.cache_set(key, res)      # 正常数据入缓存（TTL+抖动）
            print('get_name 从数据库中来')
        else:
            cache_utils.cache_set_empty(key)     # 查无此人 → 写空值哨兵，短 TTL（防穿透）
            print('get_name 空值写入缓存')
    # 缓存防穿透示例 =====================

    if res is not None:
        # escape() 转义HTML特殊字符，防止库里的数据被当成HTML/JS执行（XSS）
        from markupsafe import escape
        txt = '姓名：'+str(escape(res['uname']))+'  '+'性别：'+str(escape(res['sex']))
        return txt
    else:
        return '用户不存在'

# 定义第二个页：伪静态
@app.route('/show_name/<name>/<age>')
def show_name(name,age):
    if name =='tom':
        # escape() 转义后再输出，防止伪静态参数里的HTML/JS被原样反射到页面（XSS）
        from markupsafe import escape
        return f'name:{escape(name)},age:{escape(age)}'
    else:
        # 网址跳转 ******************
        return redirect('http://baidu.com')


# post传值
@app.route('/sina_news')
def sina_news():

    # 获取新浪新闻的数据（老师版：加redis缓存层，第二次访问起走缓存，不再重复抓http接口）=====
    # 如果想强制刷新缓存，取消下面两行的注释：
    # keys = redis_client.keys('sina_info:*')
    # if len(keys) > 0: redis_client.delete(*keys)
    keys = cache_utils.scan_keys('sina_info:*')
    # 判断keys的长度，如果为0，则表示缓存为空，要从http接口取数据
    if len(keys) == 0:
        # 引入urllib.request 可以获取指定网址中的源代码
        import urllib.request
        # 通过urllib.request获取指定网址中的源码（接口地址走 config，不再写死 127.0.0.1:8000）
        html_code = urllib.request.urlopen(f'http://{config.API_HOST}:{config.API_PORT}/')
        # 通过json.load(html_code)将源码通过json转成原类型
        sina_list = json.load(html_code)
        # 用序号做键逐条写入缓存（cache_set 自带 TTL+抖动）
        index = 1
        for row in sina_list:
            cache_utils.cache_set(f'sina_info:{index}', row)
            index = index + 1
        # 在这里从缓存重新读取数据
        keys = cache_utils.scan_keys('sina_info:*')
        print('从http接口中获取数据')
    else:
        print('从缓存中获取数据')

    # 从缓存中将所有数据取出来==============================
    # 注意：SCAN 返回的顺序是随机的，按序号排一下，否则翻页时新闻顺序会乱跳
    keys.sort(key=lambda k: int(k.decode().split(':')[1]))
    news_total_list = []
    for key_i in keys:
        news_total_list.append(cache_utils.cache_get(key_i))

    # 通过分页方式展示数据===========================================
    # 接收外部的传进来的页码
    # request.args.get('name','备用值') 备用值是当get获取None值时，显示此值。
    # 定义当前页码的变量
    page = int( request.args.get('page',1) )

    # 定义每页显示的条数
    everyPage = 10 # 每页显示10条信息
    # 定义总页数= （新闻条数 / 每页数量）
    import math
    totalPage = math.ceil( len(news_total_list) / everyPage )

    # 定义翻页的HTML代码
    pre_page = '上一页'
    next_page = '下一页'
    # 此处的page记得要事先转成int
    if page>1:
        pre_page = f'<a href="/sina_news?page={page - 1}">上一页</a>'
    if page < totalPage:
        next_page = f'<a href="/sina_news?page={page + 1}">下一页</a>'

    # 通过分页函数获取当前应该显示的数据
    news_list = checkFunc.showPage(news_total_list,page,everyPage)

    return render_template('sina_news.html',school_name=school_name,news_list=news_list,pre_page=pre_page,next_page=next_page)


# 网易新闻（逻辑和 /sina_news 一样：数据源是 http_server.py 的 /wangyi 接口，同样带redis缓存层）
@app.route('/wangyi_news')
def wangyi_news():
    import urllib.request
    import math

    # redis缓存层：缓存为空才从http接口取，之后翻页直接读缓存
    keys = cache_utils.scan_keys('wangyi_info:*')
    if len(keys) == 0:
        html_code = urllib.request.urlopen(f'http://{config.API_HOST}:{config.API_PORT}/wangyi')
        wangyi_list = json.load(html_code)
        index = 1
        for row in wangyi_list:
            cache_utils.cache_set(f'wangyi_info:{index}', row)
            index = index + 1
        keys = cache_utils.scan_keys('wangyi_info:*')
        print('从http接口中获取数据')
    else:
        print('从缓存中获取数据')

    # SCAN 返回顺序随机，按序号排序保证翻页顺序正确
    keys.sort(key=lambda k: int(k.decode().split(':')[1]))
    news_total_list = []
    for key_i in keys:
        news_total_list.append(cache_utils.cache_get(key_i))

    # 分页（和 /sina_news 同一套逻辑）
    page = int(request.args.get('page', 1))
    everyPage = 10
    totalPage = math.ceil(len(news_total_list) / everyPage)

    pre_page = '上一页'
    next_page = '下一页'
    if page > 1:
        pre_page = f'<a href="/wangyi_news?page={page - 1}">上一页</a>'
    if page < totalPage:
        next_page = f'<a href="/wangyi_news?page={page + 1}">下一页</a>'

    news_list = checkFunc.showPage(news_total_list, page, everyPage)

    return render_template('wangyi_news.html',school_name=school_name,news_list=news_list,pre_page=pre_page,next_page=next_page)


# 为websocket创建路由（在线聊天室页面，真正的通信由 websocket_server.py 在 ws://localhost:8888 提供）
@app.route("/websocket")
def websocket():
    return render_template('websocket.html',school_name=school_name)


# 启动项目
if __name__=='__main__':
    # 默认地址：127.0.0.1:5000
    app.run(
        # 按WIN + R：cmd
        # 输入：ipconfig 查本机IP地址
        # host='192.168.6.79',
        # port=5000
    )
