# tasktb

极简的任务管理系统 （两行代码实现任务接受、生成、任务参数缓存过滤、优先级排序、分布式分发、频控等），基于HTTP接口或者python SDK进行任务管理
两行代码即可快速实现生产者-消费者模型，并可控制优先级，开始暂停、周期任务、自动下发消息队列（redis）等

## START

1.  服务端：启动web管理界面和接口
```shell script
pip install tasktb
python -m tasktb.ctl start -p 5127 -u 'mysql+pymysql://mq:1234qwer@127.0.0.1:3306/test' -h '0.0.0.0' -l './tasktb.log'
```

2.  客户端：通过python sdk进行任务读写
```python

from tasktb import Tab

tb = Tab('127.0.0.1:5127', project='p1', tasktype='t1')
print(tb.set(value="http://a.com", status=0, priority=0b11110000, period=0, qid=None, timecanstart=None))
print(tb.get(size=1))
print(tb.update_tasks([
    {'value': "http://a.com"},
],
    status=1
))

```


## MORE

1. 更多服务端启动方式启动web管理界面和接口
```shell script
pip install tasktb


# 代码直接启动服务，方便调试
import tasktb
tasktb.run_all(
    host="0.0.0.0", port=5127, redis_host='127.0.0.1',
    redis_port=6379, redis_db_task=11, file='tasktb.db')
tasktb.run_all(
    host="0.0.0.0", port=5127, redis_host='127.0.0.1',
    redis_port=6379, redis_db_task=11, url='sqlite+aiosqlite:///:memory:')
tasktb.run_all(
    host="0.0.0.0", port=5127, redis_host='127.0.0.1',
    redis_port=6379, redis_db_task=11, url='mysql+pymysql://mq:1234qwer@127.0.0.1:3306/test')

# 前台启动服务，方便调试
python -m tasktb.ctl run -p 5127 -u 'mysql+pymysql://mq:1234qwer@127.0.0.1:3306/test'

# 或者后台启动（只适用于Linux），运用sqlite数据库，-f指定数据的保存文件位置，方便备份和加密迁移，-p指定服务端的监听端口, -h指定服务绑定IP
python -m tasktb.ctl start -p 5127 -f './tasktb.db' -h '0.0.0.0'

# 或者后台启动（只适用于Linux），运用mysql，tidb等数据库，-u指定数据库的连接URL，-p指定服务端的监听端口, -h指定服务绑定IP
python -m tasktb.ctl start -p 5127 -u 'mysql+pymysql://mq:1234qwer@127.0.0.1:3306/test' -h '0.0.0.0' -l './tasktb.log'

# 然后就可以浏览器访问 http://127.0.0.1:5127 查看数据

# 目前支持4种关系型数据库
'sqlite+aiosqlite:///:memory:'
'mysql+aiomysql://mq:1234qwer@127.0.0.1:3306/test'
'sqlite+aiosqlite:///tasktb.db'
'postgresql+asyncpg://user:pass@hostname/dbname'


# 停止程序，只适用于Linux
python -m tasktb.ctl stop -p 5127 

# 查看当前运行程序，只适用于Linux
python -m tasktb.ctl show

# 手动输入命令后台启动，日志写入tasktb.log
nohup python3.9 -m tasktb.ctl run -p 5127 -f './tasktb.db' > tasktb.log 2>&1 &

```

2.  更多客户端任务管理
```python

from tasktb import Tab

tb = Tab('127.0.0.1:5127', project='p1', tasktype='t1')
print(tb.set("http://a.com", status=0))
print(tb.set_many([f"http://a.com?s={i}" for i in range(10000)], status=0))
print(tb.get(size=100))
print(tb.update_tasks([
    {'value': 1},
    {'value': 2},
],
    status=1
))

```

## sqlite upgrade
如果使用sqlite作为任务管理数据库而且版本过低，需要更新
```shell script
1.查看软连接版本
/usr/bin/sqlite3 --version
2.备份旧的sqlite3
sudo mv /usr/bin/sqlite3 /usr/bin/sqlite3_old
3.将新的sqlite3软连接到原来sqlite3位置
cp tasktb/sqlite/sqlite3 ~/sqlite3
#ln -s /usr/local/sqlite/bin/sqlite3 /usr/bin/sqlite3
sudo ln -s ~/sqlite3 /usr/bin/sqlite3
原文链接：https://blog.csdn.net/Meteor31/article/details/109557703

* 编译最新版本的 sqlite3
# https://charlesleifer.com/blog/compiling-sqlite-for-use-with-python-applications/

wget https://www.sqlite.org/src/tarball/sqlite.tar.gz
tar xzf sqlite.tar.gz
cd sqlite/
#./configure
export CFLAGS="-DSQLITE_ENABLE_FTS3 \
    -DSQLITE_ENABLE_FTS3_PARENTHESIS \
    -DSQLITE_ENABLE_FTS4 \
    -DSQLITE_ENABLE_FTS5 \
    -DSQLITE_ENABLE_JSON1 \
    -DSQLITE_ENABLE_LOAD_EXTENSION \
    -DSQLITE_ENABLE_RTREE \
    -DSQLITE_ENABLE_STAT4 \
    -DSQLITE_ENABLE_UPDATE_DELETE_LIMIT \
    -DSQLITE_SOUNDEX \
    -DSQLITE_TEMP_STORE=3 \
    -DSQLITE_USE_URI \
    -O2 \
    -fPIC"
export PREFIX="/usr/local"
LIBS="-lm" ./configure --disable-tcl --enable-shared --enable-tempstore=always --prefix="$PREFIX"
make
sudo make install 
* 备份文件 /usr/lib/x86_64-linux-gnu/libsqlite3.so.0.8.6
* 从编译目录复制文件~/sqlite-autoconf-3310100/.libs/libsqlite3.so.0.8.6 到/usr/lib/x86_64-linux-gnu/
* 安装编译版本（sudo make install）
https://sqlite.org/forum/forumpost/4691e7792b62dca4


sqlite3 --version

```