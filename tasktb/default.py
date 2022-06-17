WEB_HOST = '127.0.0.1'
WEB_PORT = 5127
TABLE_NAME_TASKINSTANCE = 'taskinstance'
TIME_RETRY_DB_GET = 5

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

"""
# 连接多个数据库
from sqlalchemy import create_engine, MetaData, Table,Column,Integer,select
from sqlalchemy.orm import mapper, sessionmaker
from sqlite3 import dbapi2 as sqlite
from sqlalchemy.engine.reflection import Inspector

class Bookmarks(object):
    pass

class BookmarksB(object):
    pass



def loadSession():
    engine = create_engine('sqlite://', echo=True)
    engine.execute("attach database 'database_b' as BB;")
    engine.execute("attach database 'database_a' as AA;")
    metadata = MetaData(engine)


    inspector = Inspector.from_engine(engine)
    print inspector.get_table_names()

    moz_bookmarks = Table('table_a', metadata,Column("id", Integer, primary_key=True),schema='AA', autoload=True)
    mapper(Bookmarks, moz_bookmarks)
    moz_bookmarksB = Table('table_b', metadata,Column("id", Integer, primary_key=True),schema='BB', autoload=True)
    mapper(BookmarksB, moz_bookmarksB)

    Session = sessionmaker(bind=engine)
    session = Session()
    return session

if __name__ =="__main__":
    session = loadSession()
    res = session.query(Bookmarks).all()
    for m in res:
        print m.msisdn,m.id

    #print list(select([moz_bookmarks, moz_bookmarksB], moz_bookmarks.c.b_id == moz_bookmarksB.c.id).execute())
"""

# SQLALCHEMY_DATABASE_URL: str = 'sqlite:///:memory:'
# SQLALCHEMY_DATABASE_URL: str = 'mysql+aiomysql://mq:1234qwer@127.0.0.1:3306/test'
SQLALCHEMY_DATABASE_URL: str = 'mysql+pymysql://mq:1234qwer@127.0.0.1:3306/test'
# SQLALCHEMY_DATABASE_URL: str = 'sqlite:///tasktb.db'

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB_TASK = 11


from functools import partial


def set_global(key, value):
    globals()[key] = value


set_web_port = partial(set_global, "WEB_PORT")
set_url = partial(set_global, "SQLALCHEMY_DATABASE_URL")
