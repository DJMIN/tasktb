import tasktb
import multiprocessing
import time

# 启动服务
multiprocessing.Process(target=tasktb.run_app, args=('0.0.0.0', 5127)).start()

# 等待初始化服务
time.sleep(5)

# multiprocessing.Process(target=tasktb.task_publisher, args=('127.0.0.1', 6379, 11)).start()

from tasktb import Tab

tb = Tab('127.0.0.1:5127', project='p1', tasktype='t1')
# print(tb.set("http://a.com", status=0))
# print(tb.set_many([f"http://a.com?s={i}" for i in range(10000)], status=0))
print(tb.get(size=12))
print(tb.update_tasks([
    {'value': 1},
    {'value': 2},
],
    status=1
))
