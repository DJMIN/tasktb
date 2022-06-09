import tasktb
import multiprocessing
import time
import requests

# 启动服务
multiprocessing.Process(target=tasktb.run_app, args=('0.0.0.0', 7788)).start()

# 等待初始化服务
time.sleep(2)
