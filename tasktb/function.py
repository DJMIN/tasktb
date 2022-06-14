import time

import requests
from hashlib import md5
import builtins
from tasktb.default import WEB_HOST, WEB_PORT, TABLE_NAME_TASKINSTANCE


def get_task(tasktype, default=None, project='default', manager_url=f'{WEB_HOST}:{WEB_PORT}'):
    result = requests.get(f'http://{manager_url}/api/item/{TABLE_NAME_TASKINSTANCE}/one', data={
        'project': project,
        'tasktype': tasktype,
    }).json().get('data')
    if not result:
        result = default
    return result


def list_task(tasktype, size=10, status=None, project='default', timecanstart=0, manager_url=f'{WEB_HOST}:{WEB_PORT}'):
    result = requests.post(f'http://{manager_url}/api/item/{TABLE_NAME_TASKINSTANCE}/list', json={
        "filters": [
            {
                'key': 'project',
                "value": project,
                'like': False,
                'typematch': True,
            }, {
                'key': 'tasktype',
                "value": tasktype,
                'like': False,
                'typematch': True,
            },
        ] + ([{
                'key': 'status',
                "value": status,
                'like': False,
                'typematch': True,
            }] if status is not None else []),
        "range": {f"{TABLE_NAME_TASKINSTANCE}___timecanstart": {"lte": timecanstart}},
        "pageSize": size,
        "page": 1,
        "index": 'idx_get_task'
    }).json()
    return result


def set_task(tasktype, value, key='', project='default', priority=0b11110000,
             period=0, manager_url=f'{WEB_HOST}:{WEB_PORT}', **kwargs):
    if not key:
        _m = md5()
        _m.update(str(value).encode())
        key = str(_m.hexdigest())

    return requests.post(f'http://{manager_url}/api/item/{TABLE_NAME_TASKINSTANCE}', json={
        'uuid': f'{project}--{tasktype}--{key}',
        'project': project,
        'tasktype': tasktype,
        'key': key,
        'value': value,
        'valuetype': type(value).__name__,
        'priority': priority,
        'period': period, **kwargs
    }).json()


def set_tasks(tasktype, values, keys=None, project='default', priority=0b11110000,
              period=0, manager_url=f'{WEB_HOST}:{WEB_PORT}', **kwargs):
    print(f"正在计算MD5 {len(values)} 个")
    t0 = time.time()
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
                'key': key,
                'value': value,
                'valuetype': type(value).__name__,
                'priority': priority,
                'period': period,
                **kwargs
            } for key, value in zip(keys, values)
        ]}
    return requests.post(f'http://{manager_url}/api/items/{TABLE_NAME_TASKINSTANCE}', json=data).json()


if __name__ == '__main__':
    # print(get_task('p', "1"))
    # print(set_task('p', 1))
    # print(set_tasks('p', range(10000000,10000002)))
    for i in range(3,40):
        print(set_tasks('p', range(20000*i,20000*(i+1)), status=1))
    # print(get_task('p', 1))
    print(list_task('p'))
    # print(list_task('p', '1'))
