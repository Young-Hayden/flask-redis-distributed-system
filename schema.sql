-- ============================================================
-- 项目数据库初始化脚本
-- 库名：mydb2509（与 Code/config.py 中 DB_NAME 默认值保持一致）
-- 用法：mysql -uroot -p < schema.sql
-- 说明：教学项目把 student.class 字段当作"密码"使用（见 checkFunc.checkLogin），
--       所以种子数据里每个学生的 class 值就是他的登录密码。
--       想导出自己本机真实表结构和数据核对，可执行：
--       mysqldump -uroot -p mydb2509 student news > schema_dump.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS mydb2509 DEFAULT CHARACTER SET utf8mb4;
USE mydb2509;

-- 学生表（登录账号 + 首页展示）
CREATE TABLE IF NOT EXISTS student (
    id    INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键，缓存键 stu_info:{id} 用它',
    uname VARCHAR(50) NOT NULL COMMENT '用户名（登录账号）',
    sex   VARCHAR(10) NOT NULL COMMENT '性别',
    class VARCHAR(50) NOT NULL COMMENT '班级（教学中兼作登录密码）',
    UNIQUE KEY uk_uname_sex_class (uname, sex, class) COMMENT '配合 App.py 查重的业务唯一约束'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生表';

-- 新闻表（站内新闻 CRUD）
CREATE TABLE IF NOT EXISTS news (
    id      INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键，缓存键 news_info:{id} 用它',
    title   VARCHAR(200) NOT NULL COMMENT '新闻标题',
    content TEXT COMMENT '新闻内容',
    UNIQUE KEY uk_title_content (title(100), content(100)) COMMENT '配合 App.py 查重的业务唯一约束'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻表';

-- ============================================================
-- 种子数据（class 即登录密码，例如：李军 / 2511班）
-- ============================================================
INSERT INTO student (uname, sex, class) VALUES
('李军',   '男', '2511班'),
('王小美', '女', '2511班'),
('张三',   '男', '2509班'),
('李四',   '男', '2512班'),
('赵小六', '女', '2509班');

INSERT INTO news (title, content) VALUES
('Python 3.12 正式发布',      '性能提升与新的类型语法特性。'),
('Redis 7.0 新特性速览',      'Function、Multi-part AOF、Sharded Pub/Sub。'),
('Flask 3.x 迁移指南',        '从 Flask 2.x 升级到 3.x 的注意事项。'),
('协程在 Web 服务中的应用',    'gevent 猴子补丁让同步代码获得并发能力。'),
('连接池如何保护数据库',       '复用连接、限制上限、池满排队等待。');
