# tasktb

任务参数管理系统 （任务接受、生成、任务参数缓存过滤、排序、分发、频控等）  （生产者框架）


## RUN

1. 服务端： 启动web管理界面和接口
```shell script
pip install tasktb

# 运用sqlite数据库，-f指定数据的保存文件位置，方便备份和加密迁移，-p指定服务端的监听端口
python -m tasktb.ctl run -p 5127 -f './tasktb.db'

# 后台启动，日志写入tasktb.log
nohup python3.9 -m tasktb.ctl run -p 5127 -f './tasktb.db' > tasktb.log 2>&1 &

```
