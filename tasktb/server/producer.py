import datetime
# import json
import time
# import os
# import sys
import logging
from uuid import uuid1
import orjson
# import psycopg2
import walrus
import requests
# from d22d.model.mysqlmodel import PGController
from tasktb.model import get_db
from tasktb import default
from tasktb.server.base import main_manger_process
from tasktb.function import list_task, set_tasks_raw


# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(BASE_DIR + '/manager')


def task_publisher(host=default.REDIS_HOST, port=default.REDIS_PORT, db=default.REDIS_DB_TASK):
    dbq = walrus.Walrus(host=host, port=port, db=db)
    while True:
        try:
            tasks_info = list_task()
        except requests.exceptions.ConnectionError:
            logging.info(f'任务服务器端口[{default.WEB_PORT}]还未启动，取不到任务，5秒后自动重试')
            time.sleep(5)
            continue

        if tasks_info['code'] != 20000:
            logging.info(f'取不到任务，5秒后自动重试：{tasks_info}')
            time.sleep(5)
            continue
        tasks_info = tasks_info['message']
        tasks = tasks_info["data"]
        logging.info(f'剩余任务{tasks_info["total"]}个，取到任务：{len(tasks)}个')
        if tasks:
            set_tasks_raw(
                tasks,
                timelastproceed=time.time(),
            )
            for task in tasks:
                if not task.get('period'):
                    set_tasks_raw([task], status=1)
                else:
                    set_tasks_raw([task], timecanstart=int(time.time()) + int(task.get('period')))
                value = orjson.loads(task.get('value'))
                if not isinstance(value, dict):
                    value = {'data': value}
                tid = f"{task.get('qid')}_result:{uuid1()}"
                value["extra"] = {
                    "task_id": tid,
                    "uuid": task.get('uuid'),
                    "task_tag": task.get('tag'),
                    "handle": task.get('handle'),
                    "publish_time": round(time.time(), 6),
                    "publish_time_format": datetime.datetime.now().__str__().split('.')[0]

                }
                dbq.List(task.get('qid', 0) or 0).append(orjson.dumps(value))
        else:
            time.sleep(default.TIME_RETRY_DB_GET)
            logging.info(f'任务已经消费完毕，取不到任务，5秒后自动重试：{tasks_info}')
            continue


if __name__ == '__main__':
    main_manger_process.add_process(task_publisher)
    main_manger_process.join_all()
