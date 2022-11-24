import tasktb
import multiprocessing
import time
import os
os.environ['LD_LIBRARY_PATH']="/usr/local/lib"
# from pysqlite3 import dbapi2 as sqlite3
import sqlite3


print('sqlite version', sqlite3.sqlite_version_info, sqlite3.sqlite_version, sqlite3.__file__)

if __name__ == '__main__':

    main_manger_process = tasktb.run_all(block=False)
    print('等待初始化服务')
    # tasktb.run_all(
    #     host="0.0.0.0", port=5127, redis_host='127.0.0.1',
    #     redis_port=6379, redis_db_task=11, url='sqlite+aiosqlite:///:memory:')

    # 启动服务
    # multiprocessing.Process(target=tasktb.run_app, args=('0.0.0.0', 5127)).start()

    # 等待初始化服务
    time.sleep(5)

    # multiprocessing.Process(target=tasktb.task_publisher, args=('127.0.0.1', 6379, 11)).start()

    from tasktb import Tab

    tb = Tab('127.0.0.1:5127', project='p1', tasktype='t1')
    # print(tb.set("http://a.com", status=0))
    # 一条sqlite(websql)语句的参数不能超过999个。
    for j in range(20):
        print(tb.set_many([f"http://a.com?s={i}" for i in range(j*1000, (j+1)*1000)], status=0))
        print(tb.get(size=12))
    print(tb.update_tasks([
        {'value': i} for i in range(10000)
    ],
        status=1
    ))
    print(tb.info())
    # print(tb.get(size=12))
    # print(tb.update_tasks([
    #     {'value': 1},
    #     {'value': 2},
    # ],
    #     status=0
    # ))
    # print(tb.get(size=12))
