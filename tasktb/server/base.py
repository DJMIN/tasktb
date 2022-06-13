import time
import os
import logging
import multiprocessing


class MangerProcess:
    def __init__(self):
        self.workers = {}

    def __del__(self):
        self.join_all()

    def add_process(self, func, args=(), kwargs=None, replay_time=1, retry_time=10, max_times=0):
        if not isinstance(args, tuple):
            args = (args,)
        kwargs = kwargs if kwargs else {}
        # print(args, kwargs)

        def _run_always():
            times = 0
            while True:
                if max_times and times >= max_times:
                    logging.info(f'[PID:{os.getpid()}] 结束每{replay_time}秒执行，第{times}次执行函数 {func.__name__}')
                    break
                try:
                    times += 1
                    logging.info(f'[PID:{os.getpid()}] 每{replay_time}秒执行，第{times}次执行函数 {func.__name__}')
                    func(*args, **kwargs)
                    time.sleep(replay_time)
                except Exception as ex:
                    logging.exception(f'[PID:{os.getpid()}] 每{retry_time}秒重试，第{times}次执行函数 {func.__name__} {ex}')
                    time.sleep(retry_time)

        p = multiprocessing.Process(target=_run_always)
        p.start()
        self.workers[p.pid] = p

    def join_all(self):
        while self.workers:
            pids = list(self.workers.keys())
            for pid in pids:
                self.workers[pid].join()
                self.workers.pop(pid)


main_manger_process = MangerProcess()
