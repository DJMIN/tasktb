WEB_HOST = '127.0.0.1'
WEB_PORT = 5127
TABLE_NAME_TASKINSTANCE = 'taskinstance'

"""
常用数据库的创建数据库连接方法
SQLAlchemy用一个字符串表示连接信息：

'数据库类型+数据库驱动名称://用户名:密码@IP地址:端口号/数据库名'


PostgreSQL数据库

from sqlalchemy import create_engine

# default, 连接串格式为 "数据库类型+数据库驱动://数据库用户名:数据库密码@IP地址:端口/数据库"
engine = create_engine('postgresql://username:password@127.0.0.1:9527/AiTestOps')
# psycopg2
engine = create_engine('postgresql+psycopg2://username:password@127.0.0.1:9527/AiTestOps')
# pg8000
engine = create_engine('postgresql+pg8000://username:password@127.0.0.1:9527/AiTestOps')


MySQL数据库

from sqlalchemy import create_engine

# default,连接串格式为 "数据库类型+数据库驱动://数据库用户名:数据库密码@IP地址:端口/数据库"
engine = create_engine('mysql://username:password@127.0.0.1:9527/AiTestOps')
# mysql-python
engine = create_engine('mysql+mysqldb://username:password@127.0.0.1:9527/AiTestOps')
# MySQL-connector-python
engine = create_engine('mysql+mysqlconnector://username:password@127.0.0.1:9527/AiTestOps')


Oracle数据库

from sqlalchemy import create_engine

# default,连接串格式为 "数据库类型+数据库驱动://数据库用户名:数据库密码@IP地址:端口/数据库"
engine = create_engine('oracle://username:password@127.0.0.1:9527/AiTestOps')
# cx_oracle
engine = create_engine('oracle+cx_oracle://username:password@127.0.0.1:9527/AiTestOps')


SQLite数据库
我们以在当前目录下创建为例，后续各步同使用此数据库。我们在create_engine方法中补充了两个参数。如下：

from sqlalchemy import create_engine

engine = create_engine('sqlite:///AiTestOps.db?check_same_thread=False', echo=True)


echo：echo默认为False，表示不打印执行的SQL语句等较详细的执行信息，改为Ture表示让其打印。
check_same_thread：check_same_thread默认为 False，sqlite默认建立的对象只能让建立该对象的线程使用，而sqlalchemy是多线程的，所以我们需要指定check_same_thread=False来让建立的对象任意线程都可使用。
"""
# SQLALCHEMY_DATABASE_URL: str = 'sqlite:///:memory:'
SQLALCHEMY_DATABASE_URL: str = 'sqlite:///tasktb.db'


def set_web_port(port):
    global WEB_PORT
    WEB_PORT = port


def set_url(url):
    global SQLALCHEMY_DATABASE_URL
    SQLALCHEMY_DATABASE_URL = url
