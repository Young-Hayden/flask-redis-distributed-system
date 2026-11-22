'''
基于 Waitress(Gevent) 和 Supervisor 部署生产环境
'''
# 安装gevent   : pip install gevent
# 安装waitress : pip install waitress

# 引入gevent
import gevent
# 引入猴子补丁
from gevent import monkey
monkey.patch_all()

# 引入waitress
from waitress import serve

# 引入主项目app.py文件中的app对象变量（文件名是 App.py，明确大小写，避免部署到 Linux 时 ImportError）
from App import app

# 引入统一配置（端口/地址不再写死，多实例部署时改 .env 即可起 5000/5001 两个实例）
import config

if __name__=='__main__':

    serve(
        app,
        host=config.WEB_HOST,
        port=config.WEB_PORT,   # 主应用用 5000，8000 留给 http_server.py（新浪爬虫，/sina_news 要去 8000 取 JSON）

        # 设置配置信息
        threads= 4, # 设置线程数
        channel_timeout = 30,
        cleanup_interval = 30,
        _quiet = True
    )