import requests
from hashlib import md5
import builtins
from tasktb.default import WEB_HOST, WEB_PORT, TABLE_NAME_TASKINSTANCE


def get_task(project, tasktype, default=None, manager_url=f'{WEB_HOST}:{WEB_PORT}'):
    result = requests.get(f'http://{manager_url}/api/item/{TABLE_NAME_TASKINSTANCE}/one', data={
        'project': project,
        'tasktype': tasktype,
    }).json().get('data')
    if not result:
        result = default
    return result


def list_task(project, tasktype, size=10, manager_url=f'{WEB_HOST}:{WEB_PORT}'):
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
            }
        ],
        "pageSize": size,
        "page": 1
    }).json()
    return result


def set_task(project, tasktype, value, key='', manager_url=f'{WEB_HOST}:{WEB_PORT}'):
    if not key:
        _m = md5()
        _m.update(str(value).encode())
        key = _m.hexdigest().encode()

    return requests.post(f'http://{manager_url}/api/item/{TABLE_NAME_TASKINSTANCE}', data={
        'project': project,
        'tasktype': tasktype,
        'key': key,
        'value': value,
        'valuetype': type(value).__name__,
    }).json()


if __name__ == '__main__':
    # print(get_task('p', "1"))
    # print(set_task('p', 1, 'test1'))
    # print(get_task('p', 1))
    print(list_task('p', 1))
    print(list_task('p', '1'))
