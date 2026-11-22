from flask import Flask
import json
app = Flask(__name__)

# 引入urllib.request,用来读取网址
import urllib.request
# 引入bs4 用来解析源码，把读取的源码转成HTML
# 安装bs4：pip install bs4
from bs4 import BeautifulSoup

@app.route('/')
def hello():
    url = 'https://www.sina.com.cn/'
    # 通过urllib.request读取网址中的源码（字符串）
    html_code = urllib.request.urlopen(url)
    # 将读取的源码转成HTML格式
    # 应用xml格式需要安装lxml：pip install lxml
    bs4_info = BeautifulSoup( html_code  , 'lxml' )
    # bs4_info.select(CSS规则)可以获取指定CSS样式所对应的标签里面内容
    title_info = bs4_info.select('.list-a li a')

    # 定义一个新闻列表
    news_list = []
    for i in title_info:
        # 获取a标签中的文本
        title = i.text
        # 获取a标签中的href
        title_url = i.get('href')
        # 只取标题长度为6字以上的
        if len(title)>=6:
            news_list.append(
                {
                    'title':title,
                    'href':title_url
                }
            )

    # # 将新闻列表中的前十条赋值给show_news_list
    # show_news_list = [ news_list[i] for i in range(10) ]
    show_news_list = news_list

    return json.dumps(show_news_list)


# 网易新闻接口：直接复用 wangyi_news.py 里写好的抓取函数
# 网易走的是 JSON 数据接口（不是抓HTML），拿到的已经是结构化数据，不用再解析
from wangyi_news import fetch_wangyi_news, CHANNELS

@app.route('/wangyi')
def wangyi():
    # 四个频道各取10条，合并成一个列表（够分页用）
    all_news = []
    for channel in CHANNELS:
        all_news.extend(fetch_wangyi_news(channel, 10))

    # ensure_ascii=False 让中文不转义，和上面新浪接口保持同样的返回方式
    return json.dumps(all_news, ensure_ascii=False)




if __name__=='__main__':
    app.run(
        port=8000
    )
