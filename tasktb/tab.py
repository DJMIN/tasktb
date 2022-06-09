from tasktb.function import get_task, set_task
from tasktb.default import WEB_HOST, WEB_PORT


class Tab:
    def __init__(
            self, manager_url=f"{WEB_HOST}:{WEB_PORT}", project='', tasktype=''):
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

    def get_one(self, default=None):
        res = get_task(project=self.project, tasktype=self.tasktype, default=default, manager_url=self.manager_url)
        return res

    def set(self, key, value):
        return set_task(tasktype=self.tasktype, key=key, value=value, manager_url=self.manager_url, project=self.project)
