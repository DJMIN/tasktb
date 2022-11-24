import time

import requests
from hashlib import md5
import builtins
from tasktb.default import SETTINGS


def list_item(item_name, size=10, range_filter=None, manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}', **kwargs):
    result = requests.post(f'http://{manager_url}/api/item/{item_name}/list', json={
        "filters": [
            {
                'key': k,
                "value": v,
                'like': False,
                'typematch': True,
            }
            for k, v in kwargs.items()
        ],
        "range": range_filter,
        "pageSize": size,
        "page": 1,
        "index": 'idx_get_task'
    }).json()
    return result


def get_item(default=None, manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}', **kwargs):
    result = requests.get(f'http://{manager_url}/api/item/{SETTINGS.TABLE_NAME_TASKINSTANCE}/one', data=kwargs).json().get(
        'data')
    if not result:
        result = default
    return result


def get_web_g(key, default='', manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}', **kwargs):
    result = requests.get(f'http://{manager_url}/api/getG/{key}/{default}', data=kwargs).text
    return result


def set_web_g(key, value, manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}', **kwargs):
    result = requests.get(f'http://{manager_url}/api/setG/{key}', data=str(value).encode('utf-8')).text
    return result


class GQ(dict):
    @classmethod
    def get(cls, item, default=''):
        return get_web_g(item, default)

    def __setitem__(self, key, value):
        return set_web_g(key, value)


G = GQ()


def list_task(tasktype=None, size=10, status=None, project='default', timecanstart=0,
              manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}'):
    result = requests.post(f'http://{manager_url}/api/item/{SETTINGS.TABLE_NAME_TASKINSTANCE}/list', json={
        "filters": ([
                        {
                            'key': 'project',
                            "value": project,
                            'like': False,
                            'typematch': True,
                        }
                    ] if project is not None else []) + ([{
            'key': 'tasktype',
            "value": tasktype,
            'like': False,
            'typematch': True,
        }] if tasktype is not None else []) + ([{
            'key': 'status',
            "value": status,
            'like': False,
            'typematch': True,
        }] if status is not None else []),
        "range": {f"{SETTINGS.TABLE_NAME_TASKINSTANCE}___timecanstart": {"lte": timecanstart}},
        "pageSize": size,
        "page": 1,
        "index": 'idx_get_task'
    }).json()
    return result


def list_task_info(tasktype=None, status=None, project='default', timecanstart=0, group=None,
              manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}'):
    result = requests.post(f'http://{manager_url}/api/item/{SETTINGS.TABLE_NAME_TASKINSTANCE}/list', json={
        "filters": ([
                        {
                            'key': 'project',
                            "value": project,
                            'like': False,
                            'typematch': True,
                        }
                    ] if project is not None else []) + ([{
            'key': 'tasktype',
            "value": tasktype,
            'like': False,
            'typematch': True,
        }] if tasktype is not None else []) + ([{
            'key': 'status',
            "value": status,
            'like': False,
            'typematch': True,
        }] if status is not None else []),
        "range": {f"{SETTINGS.TABLE_NAME_TASKINSTANCE}___timecanstart": {"lte": timecanstart}},
        "group": group or ['tasktype', 'status'],
        "pageSize": 1,
        "page": 1,
        "index": 'idx_get_task'
    }).json()
    return result


def set_task(tasktype, value, key='', project='default', priority=0b11110000,
             period=0, qid=None, timecanstart=None, status=0, manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}', **kwargs):
    if not key:
        _m = md5()
        _m.update(str(value).encode())
        key = str(_m.hexdigest())
    if not timecanstart:
        timecanstart = time.time()
    return requests.post(f'http://{manager_url}/api/item/{SETTINGS.TABLE_NAME_TASKINSTANCE}', json={
        'uuid': f'{project}--{tasktype}--{key}',
        'project': project,
        'tasktype': tasktype,
        'qid': qid,
        'key': key,
        'value': value,
        'valuetype': type(value).__name__,
        'priority': priority,
        'period': period,
        'timecanstart': timecanstart,
        'status': status,
        **kwargs
    }).json()


def set_tasks(tasktype, values, keys=None, project='default', priority=0b11110000,
              period=0, qid=None, timecanstart=None, status=0, manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}', **kwargs):
    print(f"正在计算MD5 {len(values)} 个")
    t0 = time.time()
    if not timecanstart:
        timecanstart = time.time()
    if not keys:
        keys = []
        for v in values:
            _m = md5()
            _m.update(str(v).encode())
            keys.append(str(_m.hexdigest()))
    print(f"计算MD5 {len(values)} 个耗时{time.time() - t0:2f}秒")
    data = {"data": [
        {
            'uuid': f'{project}--{tasktype}--{key}',
            'project': project,
            'tasktype': tasktype,
            'qid': qid,
            'key': key,
            'value': value,
            'valuetype': type(value).__name__,
            'priority': priority,
            'period': period,
            'timecanstart': timecanstart,
            'status': status,
            **kwargs
        } for key, value in zip(keys, values)
    ]}
    return requests.post(f'http://{manager_url}/api/items/{SETTINGS.TABLE_NAME_TASKINSTANCE}', json=data).json()


def set_tasks_raw(data, manager_url=f'{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}', **kwargs):
    ds_set = dict()
    for d in data:
        d = d | kwargs
        if not d.get("key"):
            _m = md5()
            _m.update(str(d.get("value")).encode())
            d['key'] = str(_m.hexdigest())
        d['uuid'] = f'{d.get("project")}--{d.get("tasktype")}--{d.get("key")}'
        ds_set[d['uuid']] = d
    return requests.post(f'http://{manager_url}/api/items/{SETTINGS.TABLE_NAME_TASKINSTANCE}', json={
        "data": list(ds_set.values())
    }).json()


if __name__ == '__main__':
    # print(get_task('p', "1"))
    # print(set_task('p', 1))
    # print(set_tasks('p', range(10000000,10000002)))
    for i in range(45, 46):
        print(set_tasks('p', range(2000 * i, 2000 * (i + 1)), status=0))
    # print(get_task('p', 1))
    print(list_task(tasktype='p'))
    # print(list_task('p', '1'))
