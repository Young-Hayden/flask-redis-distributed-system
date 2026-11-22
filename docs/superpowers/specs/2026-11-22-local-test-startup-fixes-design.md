# 本地测试与启动兼容性最小修复设计

日期：2026-11-22

## 目标

修复已复现的三个局部问题，不改变缓存策略、依赖版本、数据库数据或部署架构：

1. TTL 单测受默认随机抖动上限影响，出现间歇性失败。
2. `requirements.txt` 的中文 UTF-8 注释在中文 Windows 的 pip 23.2 下触发 GBK 解码错误。
3. `checkFunc.py` 依赖当前工作目录寻找 `logging.conf`，导致 README 的根目录启动命令失败。

## 方案

### TTL 测试

在 `tests/test_cache_utils.py::test_ttl_has_jitter` 中使用 pytest `monkeypatch`，将 `cache_utils.config.CACHE_TTL_JITTER` 临时设为测试声明的 50。生产配置和业务代码保持不变，测试结束后自动恢复配置。

### 依赖文件编码

将 `requirements.txt` 的注释转换为纯 ASCII 英文，所有包名和固定版本保持原样。这样无需要求用户设置 `PYTHONUTF8`，也不引入新的安装工具或运行时依赖。

### 日志配置路径

在 `Code/checkFunc.py` 中根据当前模块的 `__file__` 构造 `logging.conf` 的绝对路径，再传给 `logging.config.fileConfig`。不改变 logger、日志级别或业务异常处理；根目录和 `Code/` 目录两种启动方式都应可用。

## 验证

1. 重复运行 TTL 用例，确认不再随机失败。
2. 不设置 `PYTHONUTF8`，执行 `pip install --dry-run --no-index -r requirements.txt`。
3. 在项目根目录运行完整 `pytest tests -q`，要求 16 项全部通过。
4. 从项目根目录启动两个 Web 实例，访问主要页面。
5. 使用数据库现有账号在实例 5000 登录，再携带同一 cookie 访问实例 5001，确认共享 Session；随后退出登录清理测试会话。
6. 检查最终 Git diff，确认变更仅限上述三个文件及本设计文档。

## 非目标

不修改数据库现有数据，不调整缓存默认 TTL/抖动，不重构登录或 Session，不提交或推送 Git。
