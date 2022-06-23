from tasktb.function import list_task, set_task, set_tasks, set_tasks_raw
from tasktb.default import SETTINGS


class Tab:
    def __init__(
            self, manager_url=f"{SETTINGS.WEB_HOST}:{SETTINGS.WEB_PORT}", project='', tasktype=''):
        if len(ms := manager_url.split(':')) < 2:
            self.host = ms[0]
            self.port = 7788
        else:
            self.host = ms[0]
            self.port = ms[-1]
        self.host = self.host.replace(r'http://', '')
        self.port = self.port.replace('/', '')
        self.manager_url = f"{self.host}:{self.port}"
        self.project = project
        self.tasktype = tasktype

    def get(self, size=10):
        res = list_task(size=size, project=self.project, tasktype=self.tasktype, manager_url=self.manager_url)
        return res

    def set(self, value, priority=0b11110000, period=0, qid=None, timecanstart=None, status=0):
        """ID冲突不会合并修改"""
        return set_task(
            tasktype=self.tasktype, value=value, manager_url=self.manager_url, project=self.project,
            priority=priority, period=period, qid=qid, timecanstart=timecanstart, status=status)

    def set_many(self, values, priority=0b11110000, period=0, qid=None, timecanstart=None, status=0):
        return set_tasks(
            tasktype=self.tasktype, values=values, manager_url=self.manager_url, project=self.project,
            priority=priority, period=period, qid=qid, timecanstart=timecanstart, status=status)

    def update_tasks(self, tasks, **kwargs):
        return set_tasks_raw(
            tasks,
            project=self.project, tasktype=self.tasktype,
            manager_url=self.manager_url, **kwargs)
