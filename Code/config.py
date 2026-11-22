'''
统一配置中心：所有"会因机器而异"的参数（地址、端口、密码）都从这里读。
优先级：环境变量 > 项目根目录 .env 文件 > 代码里的默认值。

为什么这么做：
1. 硬编码密码进仓库 = 泄露事故；这里默认值只保留本机开发值，生产用环境变量覆盖。
2. 分布式部署时，Web / 爬虫接口 / WebSocket / 刷新守护进程可能跑在不同机器上，
   各自只需要改自己的 .env，代码一行不动——这是"配置与代码解耦"。
3. 面试讲法：12-Factor App 的第三条就是"配置存环境"，容器编排里更是唯一做法。
'''
import os

# ---------------------------------------------------------------------------
# 轻量 .env 加载器（不引入 python-dotenv 依赖）：项目根目录有 .env 就逐行读进来
# 格式：KEY=VALUE，支持 # 注释；已有同名环境变量的不覆盖（环境变量优先）
# ---------------------------------------------------------------------------
def load_env(path: str = None) -> None:
    if path is None:
        # config.py 在 Code/ 下，项目根目录是它的上一级
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if not os.path.isfile(path):
        return
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())

load_env()


def _get(key: str, default: str) -> str:
    return os.environ.get(key, default)


# ===== MySQL =====
MYSQL_HOST = _get('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(_get('MYSQL_PORT', '3306'))
MYSQL_USER = _get('MYSQL_USER', 'root')
MYSQL_PASSWORD = _get('MYSQL_PASSWORD', '123456')
MYSQL_DB = _get('MYSQL_DB', 'mydb2509')
MYSQL_MAX_CONNECTIONS = int(_get('MYSQL_MAX_CONNECTIONS', '100'))
MYSQL_MAX_CACHED = int(_get('MYSQL_MAX_CACHED', '20'))

# ===== Redis =====
REDIS_HOST = _get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(_get('REDIS_PORT', '6379'))

# ===== Flask =====
# session 签名密钥：生产必须用环境变量设置强随机值（os.urandom 每次重启都变，会导致登录态失效）
SECRET_KEY = _get('SECRET_KEY', '')

# ===== 各服务端口（分布式拆分后每个进程一个端口，可分别部署到不同机器）=====
WEB_HOST = _get('WEB_HOST', 'localhost')
WEB_PORT = int(_get('WEB_PORT', '5000'))       # 主站（waitress 托管）
API_HOST = _get('API_HOST', '127.0.0.1')       # 爬虫数据接口服务的地址（主站去调它）
API_PORT = int(_get('API_PORT', '8000'))
WS_HOST = _get('WS_HOST', 'localhost')
WS_PORT = int(_get('WS_PORT', '8888'))         # WebSocket 聊天服务

# ===== 缓存策略参数（配合 cache_utils.py，详见讲解手册"缓存三件套"）=====
CACHE_DEFAULT_TTL = int(_get('CACHE_DEFAULT_TTL', '300'))      # 缓存基础过期时间（秒）
CACHE_TTL_JITTER = int(_get('CACHE_TTL_JITTER', '60'))         # 过期时间随机抖动上限（防雪崩）
CACHE_EMPTY_TTL = int(_get('CACHE_EMPTY_TTL', '30'))           # 空值缓存 TTL（防穿透）
