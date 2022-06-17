# tasktb

任务参数管理系统 （任务接受、生成、任务参数缓存过滤、排序、分发、频控等）  （生产者框架）


## RUN

1. 服务端： 启动web管理界面和接口
```shell script
pip install tasktb


# 前台启动服务，方便调试
python -m tasktb.ctl run -p 5127 -u 'mysql+pymysql://mq:1234qwer@127.0.0.1:3306/test'

# 或者后台启动（只适用于Linux），运用sqlite数据库，-f指定数据的保存文件位置，方便备份和加密迁移，-p指定服务端的监听端口, -h指定服务绑定IP
python -m tasktb.ctl start -p 5127 -f './tasktb.db' -h '0.0.0.0'

# 或者后台启动（只适用于Linux），运用mysql，tidb等数据库，-u指定数据库的连接URL，-p指定服务端的监听端口, -h指定服务绑定IP
python -m tasktb.ctl start -p 5127 -u 'mysql+pymysql://mq:1234qwer@127.0.0.1:3306/test' -h '0.0.0.0' -l './tasktb.db'

# 然后就可以浏览器访问 http://127.0.0.1:5127 查看数据



# 停止程序，只适用于Linux
python -m tasktb.ctl stop -p 5127 

# 查看当前运行程序，只适用于Linux
python -m tasktb.ctl show

# 手动输入命令后台启动，日志写入tasktb.log
nohup python3.9 -m tasktb.ctl run -p 5127 -f './tasktb.db' > tasktb.log 2>&1 &

```

1. 服务端： 启动web管理界面和接口
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