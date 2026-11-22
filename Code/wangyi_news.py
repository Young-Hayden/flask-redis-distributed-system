# 抓取网易新闻 —— 教学示例
# 思路：网易首页(news.163.com)大量内容是 JS 动态渲染的，直接抓 HTML 拿到的文章很少。
#      但网易手机版(3g.163.com)是通过 JSON 接口取数据的，我们直接调这个接口即可。
# 接口格式：
#   https://3g.163.com/touch/reconstruct/article/list/{频道ID}/{起始}-{条数}.html
#   返回的是 JSONP（外面包了一层 artiList(...)），要用正则把括号剥掉再 json.loads。
import urllib.request
import json
import re

# 实测可用的频道ID（2026-08-14 验证，数据都是当天的）：
#   BA8EE5GMwangning 财经
#   BA8E6OEOwangning 体育
#   BAI67OGGwangning 娱乐
#   BD2A86BEwangning 军事
# 注意：BA10EE81wangning(新闻头条) 目前已停用返回空，BAI6I0O5wangning(科技) 数据停留在2023年。
CHANNELS = {
    '财经': 'BA8EE5GMwangning',
    '体育': 'BA8E6OEOwangning',
    '娱乐': 'BAI67OGGwangning',
    '军事': 'BD2A86BEwangning',
}


def fetch_wangyi_news(channel='财经', count=10):
    """
    抓取网易指定频道的新闻列表
    :param channel: 频道名（CHANNELS 里的键）
    :param count:   要取的条数
    :return: [{'title','source','ptime','url','digest'}, ...]
    """
    tid = CHANNELS[channel]
    # 起始固定 0，条数按需要；网易这个接口最多一次返回的条数有限
    url = f'https://3g.163.com/touch/reconstruct/article/list/{tid}/0-{count}.html'

    # 必须带 User-Agent，否则容易被拒
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    raw = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')

    # 剥掉 JSONP 外壳：artiList({...}) -> {...}
    json_text = re.sub(r'^artiList\(|\)$', '', raw.strip())
    data = json.loads(json_text)

    # data 的结构：{频道ID: [文章字典, ...]}
    items = data.get(tid, [])

    # 只挑我们关心的字段，拼出文章详情页地址
    news_list = []
    for it in items:
        docid = it.get('docid', '')
        news_list.append({
            'title':  it.get('title'),                                  # 标题
            'source': it.get('source'),                                 # 来源（网易XX）
            'ptime':  it.get('ptime'),                                  # 发布时间
            'digest': it.get('digest'),                                 # 摘要
            'url':    f'https://www.163.com/dy/article/{docid}.html',   # PC版详情页
        })
    return news_list


if __name__ == '__main__':
    for channel in CHANNELS:
        print(f'===== {channel} =====')
        for n in fetch_wangyi_news(channel, 3):
            print(f"  {n['ptime']}  {n['title'][:30]}")
            print(f"     {n['url']}")
