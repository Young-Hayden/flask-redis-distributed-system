# 安装pymysql ： pip install pymysql
# 引用pymysql
import pymysql
import pymysql.cursors

# 创建连接对象
conn = pymysql.connect(
    # 必填项
    # 主机地址:127.0.0.1  localhost 表示本机地址
    host='localhost',
    # 用户名
    user='root',
    # 密码
    password='123456',
    # 数据库:默认要指定一个数据库（改用你自己的库 mydb2509）
    database='mydb2509',

    # 非必填项
    # port=3306
    # # 编码格式:解决中文乱码
    # charset='utf8'

    # 将游标读取的结果从元组类型改成字典类型
    cursorclass=pymysql.cursors.DictCursor
)

# 创建游标：用来执行SQL语句、获取操作结果
cursor = conn.cursor()

# 当前页独立运行会执行判断句里程序
if __name__=='__main__':

    # 操作数据库
    # 实例：查询数据表
    # cursor.execute(sql) 执行一条SQL语句
    # cursor.executemany(sql,data)  执行一条SQL语句，条件可以是多个
    # 基础查询
    # sql = 'select * from student'
    # # 执行SQL语句
    # cursor.execute(sql)
    # # 获取执行结果
    # # cursor.fetchall() 获取所有结果
    # # cursor.fetchone() 获取结果集中的第一条
    # # cursor.fetchmany(size=10) 从结果集中获取指定数据
    # res = cursor.fetchall()
    # for i in res:
    #     print(i['stu_name'],i['sex'],i['age'])

    # 向SQL语句传参数
    userid = 1
    # # 如下语句非常危险，不建议使用
    # # sql = f'select * from student where id={userid}'
    # sql = f'select * from student where id=%s'
    # cursor.execute(sql,(userid) ) # 带防SQL注入功能

    # cursor.execute(sql)
    # res = cursor.fetchall()
    # print(res)
    # SQL注入：通过非法操作，绕开SQL语句中的条件，实现验证功能
    # 例如：
    # # 正常语句：sql = "select * from user where username='admin' and pasword='123' "
    # sql = "select * from user where username='admin' and password='  ' or 1<2 or a='  ' "
    # # 如果用户在密码框输入：' or 1<2 or a=' 就可以伪装成登录

    # pymysql自带防SQL注入，传参时有要求
    stu_name = '张一二'
    sql = 'select * from student where id=%s and stu_name=%s'
    cursor.execute(sql,(userid,stu_name))
    res = cursor.fetchall()
    print(res)
    #
    # pymysql在执行SQL语句时默认是手动提交。
    # 所以，执行任何SQL语句必须手动提交数据
    # commit() 提交事务

    # cursor.executemany(sql,data)  执行一条SQL语句，条件可以是多个
    # data =[]
    # for i in range(10):
    #     data.append( ('张三',i) )
    #
    # # print(data)
    # conn.close() 关闭数据库连接