import datetime
import json
import time
import os
import sys
import logging
import uuid as uuidm
import orjson
import psycopg2
import walrus
# from d22d.model.mysqlmodel import PGController
from tasktb.model import get_db
from tasktb import default
from tasktb.server.base import main_manger_process
from tasktb.function import list_task

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR + '/manager')


dbq = walrus.Walrus(host=default.REDIS_HOST, port=default.REDIS_PORT, db=default.REDIS_DB_TASK)
dbq_retry = walrus.Walrus(host=default.REDIS_HOST, port=default.REDIS_PORT, db=default.REDIS_RETRY_DB)



def update_periodtaskinstance_timecanstart(period, uuid):
    cursor.execute("update {} set {}={} where {}='{}'".format(
        'taskinstance', 'timecanstart', int(time.time()) + period, 'uuid', uuid
    ))


def update_taskinstance_timecanstartAndStatus(period, uuid, status=1):
    cursor.execute("update {} set {}={}, {}={} where {}='{}'".format(
        'taskinstance', 'timecanstart', int(time.time()) + period, 'status', status, 'uuid', uuid
    ))


def task_group_url():
    while True:
        tasks = crud.get_taskinstance_tasks()
        logging.info(f'取到任务：{len(tasks)}个')
        if tasks:
            crud.update_task_by_pk(
                tasks,
                timeupdate=time.time(),
                timelastproceed=time.time(),
            )
            for task in tasks:
                # ite = copy.deepcopy(task)
                if task.get('period') == 0:
                    update_taskinstance_timecanstartAndStatus(task.get('period'), task.get('uuid'))
                else:
                    update_periodtaskinstance_timecanstart(task.get('period'), task.get('uuid'))
                # timecanstart = int(time.time())+task.get('period')
                # ctrl.mysql_update(table_name='taskinstance', where='''qid=task.get('qid')''', kwargs={'timecanstart':timecanstart})
                ite = orjson.loads(task.get('data'))
                tid = f"{task.get('qid')}_result:{uuidm.uuid1()}"
                ite["extra"] = {
                    "task_id": tid,
                    "uuid": task.get('uuid'),
                    "task_tag": task.get('tag'),
                    "handle": task.get('handle'),
                    "publish_time": round(time.time(), 6),
                    "publish_time_format": datetime.datetime.now().__str__().split('.')[0]

                }
                dbq.List(task.get('qid')).append(orjson.dumps(ite))
        else:
            time.sleep(default.TIME_RETRY_DB_GET)


def retry_taskinstances():
    if len(dbq_retry.keys()) != 0:
        keys = dbq_retry.keys()
        for key in keys:
            value = dbq_retry.lrange(key, 0, -1)
            value = [v.decode('utf-8') for v in value]
            value_str = str(value).replace('[', '').replace(']', '').replace('\'', '')
            value_dic = json.loads(value_str)
            value_json = json.dumps(value_dic, ensure_ascii=False)
            dbq.List(key).prepend(value_json)
            dbq_retry.List(key).bpopleft()
        logging.info("Add retry_taskinstance success!")
    else:
        logging.info("Redis[14] is empty!")


if __name__ == '__main__':
    main_manger_process.add_process(task_group_url)
    # main_manger_process.add_process(retry_taskinstances)
    main_manger_process.join_all()
