import time
from uuid import uuid1
import orjson
import walrus
import functools
import datetime
import requests
import logging
from tasktb.default import SETTINGS
from tasktb.function import list_task, set_tasks_raw, G

# logging_info = logging.info
logging_info = functools.partial(print, 'task_publisher log:')


def now_str():
    return datetime.datetime.now().__str__().split('.')[0]


def task_publisher(host=SETTINGS.REDIS_HOST, port=SETTINGS.REDIS_PORT, db=SETTINGS.REDIS_DB_TASK, q_max=100):
    dbq = walrus.Walrus(host=host, port=port, db=db)

    while True:
        try:
            tasks_info = list_task(
                project=None,
                status=0,
                size=1000,
                timecanstart=time.time()
            )
        except requests.exceptions.ConnectionError:
            log = f'任务服务器端口[{SETTINGS.WEB_PORT}]还未启动，取不到任务，5秒后自动重试'
            logging_info(log)
            time.sleep(5)
            continue

        if tasks_info['code'] != 20000:
            log = f'取不到任务，5秒后自动重试：{tasks_info}'
            G['task_publisher'] = '取不到任务，5秒后自动重试'
            G["task_publisher_error"] = f'[{now_str()}] {log}'
            logging_info(log)
            time.sleep(5)
            continue
        tasks_info = tasks_info['message']
        tasks = tasks_info["data"]
        log = f'剩余任务{tasks_info["total"]}个，取到任务：{len(tasks)}个'
        G['task_publisher'] = log
        G["remain_task"] = tasks_info["total"]
        logging_info(log)
        if tasks:
            logging_info(
                set_tasks_raw(
                    tasks,
                    timelastproceed=time.time(),
                ))
            task_update = []
            for idx, task in enumerate(tasks):
                if not task.get('period'):
                    task['status'] = 1
                    # set_tasks_raw([task], status=1)
                else:
                    task['timecanstart'] = int(time.time()) + int(task.get('period'))
                    # set_tasks_raw([task], timecanstart=int(time.time()) + int(task.get('period')))
                task_update.append(task)
                value = task.get('value')
                try:
                    value = orjson.loads(value)
                    if not isinstance(value, dict):
                        value = {'data': value}
                except orjson.JSONDecodeError:
                    value = {'data': value}
                except Exception as ex:
                    value = {
                        'data': value,
                        'ex_type': str(ex.__class__.__name__),
                        'ex': str(ex),
                    }
                qid = task.get('qid', 0) or 0
                tid = f"{qid}_result:{uuid1()}"
                value["extra"] = {
                    "task_id": tid,
                    "uuid": task.get('uuid'),
                    "task_tag": task.get('tag'),
                    "handle": task.get('handle'),
                    "publish_time": round(time.time(), 6),
                    "publish_time_format": datetime.datetime.now().__str__().split('.')[0]

                }
                while len(dbq.List(qid)) > q_max:
                    time.sleep(1)
                    logging_info(f'[{now_str()}] [{qid}]队列已满 ...[{len(dbq.List(qid))}/{q_max}]  now task:[{idx + 1}/{len(tasks)}]')
                    G["task_publisher_error"] = f'[{now_str()}] [{qid}]队列已满 ...[{len(dbq.List(qid))}/{q_max}]  now task:[{idx + 1}/{len(tasks)}]'

                dbq.List(qid).append(orjson.dumps(value))
                res = set_tasks_raw(task_update)
                logging_info(f'{res} ...{idx + 1}/{len(tasks)}')
                task_update = []
        else:
            log = f'任务已经消费完毕，取不到任务，5秒后自动重试'
            G['task_publisher'] = log
            G["remain_task"] = len(tasks)
            logging_info(log)
            time.sleep(SETTINGS.TIME_RETRY_DB_GET)
            continue


if __name__ == '__main__':
    main_manger_process.add_process(task_publisher)
    main_manger_process.join_all()
