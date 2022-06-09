import datetime
import sqlite3
import logging
import time
from queue import Queue
from threading import Thread


logger = logging.getLogger('modelmid')
logger.setLevel(logging.DEBUG)


def sqlite_escape(key_word):
    key_word = key_word.encode("utf-8")
    key_word = key_word.replace("'", "''")
    return key_word


class SelectConnect(object):
    """
    只能用来查询
    """

    def __init__(self, filepath):
        # isolation_level=None为智能提交模式，不需要commit
        self.conn = sqlite3.connect(filepath, check_same_thread=False, isolation_level=None)
        self.conn.execute('PRAGMA journal_mode = WAL')
        cursor = self.conn.cursor()
        cursor.execute('PRAGMA synchronous=OFF')
        self.conn.text_factory = str
        # 把结果用元祖的形式取出来
        self.cursor = self.conn.cursor()
        self.conn.row_factory = self.dict_factory
        # 把结果用字典的形式取出来
        self.cursor_diction = self.conn.cursor()

    def commit(self):
        self.conn.commit()

    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def close_db(self):
        # self.cursor.close()
        self.conn.close()


class SqliteMultithread(Thread):
    """
    Wrap sqlite connection in a way that allows concurrent requests from multiple threads.
    This is done by internally queueing the requests and processing them sequentially
    in a separate thread (in the same order they arrived).
    """

    def __init__(self, filename, autocommit, journal_mode):
        super(SqliteMultithread, self).__init__()
        self.filename = filename
        self.autocommit = autocommit
        self.journal_mode = journal_mode
        self.reqs = Queue()  # use request queue of unlimited size
        self.daemon = True  # python2.5-compatible
        # self.setDaemon(True)  # python2.5-compatible
        self.running = True
        self.start()

    @staticmethod
    def dict_factory(cursor, row):
        # field = [i[0] for i in cursor.description]
        # value = [dict(zip(field, i)) for i in records]
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def run(self):
        if self.autocommit:
            conn = sqlite3.connect(self.filename, isolation_level=None, check_same_thread=False)
        else:
            conn = sqlite3.connect(self.filename, check_same_thread=False)
        conn.execute('PRAGMA journal_mode = %s' % self.journal_mode)
        conn.text_factory = str
        cursor = conn.cursor()
        cursor.execute('PRAGMA synchronous=OFF')
        conn.row_factory = self.dict_factory
        _cursor_diction = conn.cursor()
        _cursor_diction.execute('PRAGMA synchronous=OFF')
        # 把结果用字典的形式取出来
        while self.running:
            req, arg, res = self.reqs.get()
            if req == '--close--':
                break
            elif req == '--commit--':
                conn.commit()
            else:
                # print(arg)
                _cursor_diction.execute(req, arg)
                # if res:
                #     for rec in cursor:
                #         res.put(rec)
                #     res.put('--no more--')
                if res:
                    res.put(_cursor_diction.fetchall())
                if self.autocommit:
                    conn.commit()
        conn.close()

    def execute(self, req, arg=None, res=None):
        """
        `execute` calls are non-blocking: just queue up the request and return immediately.
        """
        self.reqs.put((req, arg or tuple(), res))

    def executemany(self, req, items):
        for item in items:
            self.execute(req, item)

    def select_all_dict(self, req, arg=None):
        """
        直接返回一个list
        :param req:
        :param arg:
        :return:
        """
        res = Queue()  # results of the select will appear as items in this queue
        self.execute(req, arg, res)
        rec = res.get()
        return rec

    def select_one_dict(self, req, arg=None):
        """
        直接返回list里的第一个元素，并且以字典展示
        :param req:
        :param arg:
        :return:
        """
        res = Queue()  # results of the select will appear as items in this queue
        self.execute(req, arg, res)
        rec = res.get()
        if len(rec) != 0:
            rec = rec[0]
        else:
            rec = None
        return rec

    def commit(self):
        self.execute('--commit--')

    def close(self):
        self.execute('--close--')


class CursorConnect(object):
    """
    以元祖的形式查询出数据
    """

    def __init__(self, filepath):
        old_con = SelectConnect(filepath)
        self.conn = old_con.conn
        self.cursor = old_con.cursor
        self.cursor2 = SqliteMultithread(filepath, autocommit=True, journal_mode="WAL")

    def execute(self, string, *args):
        retry = 0
        int_time = 0.1
        while True:
            try:
                if string.startswith('select'):
                    return self.cursor.execute(string, *args)
                else:
                    return self.cursor2.execute(string, *args)
            except Exception as ex:
                logger.warning(f"第{retry}次重试查询失败[{ex.__class__.__name__}] {ex}，{int_time}秒后重试：{string}")
                time.sleep(int_time)

    def executescript(self, string):
        return self.cursor.executescript(string)

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        self.cursor2.running = False
        self.cursor.close()
        self.conn.close()


class CursorDictionConnect(object):
    """
    以字典的形式查询出数据，建议全部用这种。
    """

    def __init__(self, filepath):
        old_con = SelectConnect(filepath)
        self.conn = old_con.conn
        self.cursor_diction = old_con.cursor_diction
        self.cursor2 = SqliteMultithread(filepath, autocommit=True, journal_mode="WAL")

    def execute(self, string, *args):
        retry = 0
        int_time = 0.1
        while True:
            try:
                if string.startswith('select'):
                    return self.cursor_diction.execute(string, *args)
                else:
                    return self.cursor2.execute(string, *args)
            except Exception as ex:
                logger.warning(f"第{retry}次重试查询失败[{ex.__class__.__name__}] {ex}，{int_time}秒后重试：{string}")
                time.sleep(int_time)

    def executescript(self, string):
        return self.cursor_diction.executescript(string)

    def fetchall(self):
        return self.cursor_diction.fetchall()

    def fetchone(self):
        return self.cursor_diction.fetchone()

    def rowcount(self):
        return self.cursor_diction.rowcount

    def select_all_dict(self, string, *args):
        return self.cursor2.select_all_dict(string, *args)

    def select_one_dict(self, string, *args):
        return self.cursor2.select_one_dict(string, *args)

    def close(self):
        self.cursor2.running = False
        self.cursor_diction.close()
        self.conn.close()

    def commit(self):
        self.conn.commit()
        self.cursor2.commit()


class Mixin:
    def __init__(self, **kwargs):
        self.update_self(**kwargs)

    def get_uuid_key(self):
        return 'uuid'

    def gen_uuid(self):
        return f''

    def set_uuid(self):
        uuid_key = self.get_uuid_key()
        if uuid_key in self.get_columns():
            setattr(self, uuid_key, self.gen_uuid())

    def set_time(self):
        time_now = datetime.datetime.now()
        if 'timecreate' in self.get_columns() and not getattr(self, 'timecreate', None):
            setattr(self, 'timecreate', time_now.timestamp())
            setattr(self, 'time_create', time_now)
        if 'timeupdate' in self.get_columns():
            setattr(self, 'timeupdate', time_now.timestamp())
            setattr(self, 'time_update', time_now)

    def update_self(self, **kwargs):
        cols = self.get_columns()
        for k, v in kwargs.items():
            if k in cols:
                setattr(self, k, v)

        self.set_uuid()
        self.set_time()
        return self

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in getattr(self, "__table__").columns}

    @classmethod
    def get_columns(cls):
        return [c.name for c in getattr(cls, "__table__").columns]

    @classmethod
    def get_primary_keys(cls):
        return [c.name for c in getattr(cls, "__table__").columns if c.primary_key]

    @classmethod
    def get_columns_infos(cls):
        return [{
            "name": c.name,
            "primary_key": c.primary_key,
            # "type": c.type,
            "type_str": str(c.type),
            "nullable": c.nullable,
            "comment": c.comment
        } for c in getattr(cls, "__table__").columns]

    @classmethod
    def get_columns_info(cls):
        return {c['name']: c for c in cls.get_columns_infos()}
