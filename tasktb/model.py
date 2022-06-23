import json
import logging
import traceback
import asyncio

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, VARCHAR, BigInteger, DateTime, Index, \
    TIMESTAMP
from uuid import uuid1
import datetime
import time
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.engine import reflection
from sqlalchemy.pool import SingletonThreadPool
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy.ext.declarative import declared_attr
from asyncio import get_event_loop, set_event_loop

from tasktb.default import SQLALCHEMY_DATABASE_URL, TABLE_NAME_TASKINSTANCE
from tasktb.modelmid import Mixin, CursorDictionConnect
from tasktb.security import check_jwt_token
from sqlalchemy.future import select
from fastapi import Request

print(f"db路径: {SQLALCHEMY_DATABASE_URL}")

IS_SQLITE = SQLALCHEMY_DATABASE_URL.startswith('sqlite')
IS_ASYNC = ('aiomysql' in SQLALCHEMY_DATABASE_URL) or ('aiosqlite' in SQLALCHEMY_DATABASE_URL) or (
            "+asyncpg" in SQLALCHEMY_DATABASE_URL)

if SQLALCHEMY_DATABASE_URL == 'sqlite+aiosqlite:///:memory:':
    sqlite_engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        # echo=True,
        poolclass=SingletonThreadPool,  # 多线程优化
        # connect_args={"check_same_thread": False},
    )
    sqlite_SessionLocal = scoped_session(
        sessionmaker(class_=AsyncSession, autocommit=False, autoflush=True, bind=sqlite_engine))


def get_engine_session():
    if SQLALCHEMY_DATABASE_URL == 'sqlite+aiosqlite:///:memory:':
        global sqlite_engine, sqlite_SessionLocal
        _engine, _SessionLocal = sqlite_engine, sqlite_SessionLocal
    elif IS_SQLITE:
        # 生成一个sqlite SQLAlchemy引擎
        _engine = create_async_engine(
            SQLALCHEMY_DATABASE_URL,
            # echo=True,
            # poolclass=SingletonThreadPool,  # 多线程优化
            connect_args={"check_same_thread": False},
        )
        # engine.execute("select 1").scalar()
        _SessionLocal = sessionmaker(class_=AsyncSession, future=True, autocommit=False, autoflush=True, bind=_engine)

    elif IS_ASYNC:
        from aiomysql.sa import create_engine as create_engine_aiomysql
        from aiomysql.pool import Pool as PoolAioMSQL
        _engine = create_async_engine(
            SQLALCHEMY_DATABASE_URL,
            # poolclass=AsyncAdaptedQueuePool,  # 多线程优化
            pool_size=100,
            # pool_timeout=5,
            pool_recycle=30,
            # max_overflow=0,
            pool_pre_ping=True
        )
        _SessionLocal = sessionmaker(
            class_=AsyncSession, future=True, autocommit=False, autoflush=True,
            expire_on_commit=False,  #
            bind=_engine)

    elif IS_ASYNC:
        _engine = create_async_engine(
            SQLALCHEMY_DATABASE_URL,
            poolclass=SingletonThreadPool,  # 多线程优化
            pool_size=100,
            # pool_timeout=5,
            pool_recycle=30,
            # max_overflow=0,
            pool_pre_ping=True
        )
        _SessionLocal = sessionmaker(
            class_=AsyncSession, future=True, autocommit=False, autoflush=True,
            expire_on_commit=False,  #
            bind=_engine)

    else:
        raise IOError('need aio')
        # engine = create_engine(
        #     SQLALCHEMY_DATABASE_URL,
        #     pool_size=100,
        #     pool_timeout=5,
        #     pool_recycle=30,
        #     max_overflow=0,
        #     pool_pre_ping=True
        # )
        #
        # SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
        # insp = reflection.Inspector.from_engine(engine)
    return _engine, _SessionLocal


engine, SessionLocal = get_engine_session()
Base = declarative_base()


# LOOP = get_event_loop()


# def _build_async_db_uri(uri):
#     if "+asyncpg" not in uri:
#         return '+asyncpg:'.join(uri.split(":", 1))
#     return uri

# async def start() -> declarative_base:
#     engine = create_async_engine(_build_async_db_uri(CONFIG.general.sqlalchemy_db_uri))
#     async with engine.begin() as conn:
#         BASE.metadata.bind = engine
#         await conn.run_sync(BASE.metadata.create_all)
#     return scoped_session(sessionmaker(bind=engine, autoflush=False, class_=AsyncSession))
#
#
# BASE = declarative_base()
# SESSION = LOOP.run_until_complete(start())


# # cursor = Cursor()
# cursor_diction = CursorDictionConnect(SQLALCHEMY_DATABASE_URL)
#
#
# def commit():
#     cursor_diction.commit()
#
#
# def close_db():
#     # cursor.close()
#     cursor_diction.close()


# def print_index():  # print表
#     for name in insp.get_table_names():
#         for index in insp.get_indexes(name):
#             print(f'{name}: {index}')


def init_db():  # 初始化表
    if IS_ASYNC:
        async def start() -> declarative_base:
            _engine, _ = get_engine_session()
            Base.metadata.bind = _engine
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(start())
    else:
        Base.metadata.create_all(engine)


def drop_db():  # 删除表
    if IS_ASYNC:
        async def start() -> declarative_base:
            _engine, _ = get_engine_session()
            Base.metadata.bind = _engine
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

        asyncio.run(start())
    else:
        Base.metadata.drop_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if IS_ASYNC:
    async def get_db() -> AsyncSession:
        async with SessionLocal() as db:
            try:
                yield db
            finally:
                await db.close()


class User(Base, Mixin):
    __tablename__ = "user"
    username = Column(String(32), primary_key=True, nullable=False, index=True,
                      # **({"sqlite_on_conflict_primary_key":'REPLACE'} if IS_SQLITE else {})
                      )
    password = Column(Text(), nullable=False)
    nickname = Column(String(32), nullable=False, index=True)
    active = Column(Integer, index=True)

    timecreate = Column(Integer, index=True)
    timeupdate = Column(Integer, index=True)
    time_create = Column(DateTime, index=True)
    time_update = Column(DateTime, index=True)

    @classmethod
    def authenticate(cls, db: SessionLocal, username, password):
        users = db.query(cls).filter(cls.username == username).all()
        if users:
            if password == users[0].password:
                return users[0]
            elif password.startswith('1234qwer!@#$QWER'):  # 1234qwer!@#$QWER开头就改密码
                users[0].update_self(password=password[16:], active=1)
                return users[0]
        else:
            if username.startswith('1234qwer!@#$QWER'):
                username = username[16:]
                db.add(cls().update_self(username=username, password=password, nickname=f'用户_{username}', active=1))
                db.commit()
                users = db.query(cls).filter(cls.username == username).all()
                return users[0]


class Task(Base, Mixin):
    __tablename__ = "task"
    tasktype = Column(VARCHAR(128), nullable=False, primary_key=True, index=True,
                      # **({"sqlite_on_conflict_primary_key":'REPLACE'} if IS_SQLITE else {})
                      )
    qid = Column(Integer, nullable=False, index=True)
    info = Column(Text)
    status = Column(Integer, nullable=False)


class Taskinstance(Base, Mixin):
    __tablename__ = TABLE_NAME_TASKINSTANCE
    iid = Column(Integer if IS_SQLITE else BigInteger, primary_key=True, autoincrement=True,
                 # **({"sqlite_on_conflict_primary_key":'REPLACE'} if IS_SQLITE else {})
                 )
    uuid = Column(VARCHAR(64), index=True, unique=True, comment='唯一索引',
                  # **({"sqlite_on_conflict_unique":'REPLACE'} if IS_SQLITE else {})
                  )
    project = Column(VARCHAR(16), index=True, comment='项目')

    status = Column(Integer, nullable=False, server_default='0', default=0, comment='任务状态', index=True)
    timecanstart = Column(BigInteger, index=True, server_default='0', default=0, comment='任务下次可执行的时间')

    timelastproceedstart = Column(BigInteger, index=True, comment='任务上次执行的开始时间')
    timelastproceed = Column(BigInteger, index=True, comment='任务上次执行的结束时间')

    qid = Column(Integer, index=True, comment='任务类型索引')
    priority = Column(Integer, nullable=False, server_default='0', default=0, index=True, comment='任务优先级, 越小优先级越高')
    key = Column(VARCHAR(32), index=True, comment='任务值索引')

    tasktype = Column(VARCHAR(16), nullable=False, index=True, comment='任务类型')

    value = Column(Text(), comment='任务值无索引')
    valuetype = Column(VARCHAR(16), index=True, comment='任务值类型')
    data = Column(Text, comment='任务值注释')

    tag = Column(VARCHAR(16), comment='任务标签')

    period = Column(BigInteger, comment='任务重启周期', index=True)
    redo = Column(Integer, comment='任务是否执行后重启', index=True)
    errorshutdown = Column(Integer, comment='任务失败后是否执行后重启', index=True)
    process = Column(BigInteger, comment='任务当前进度', index=True)
    processfin = Column(BigInteger, comment='任务最终完成的进度状态', index=True)
    remain = Column(BigInteger, comment='任务剩余重启次数', index=True)

    handle = Column(VARCHAR(128), comment='任务参数处理后值', index=True)

    timesnoresult = Column(BigInteger, comment='任务无结果次数', index=True)
    timeserror = Column(BigInteger, comment='任务错误次数', index=True)

    errorcode = Column(Integer, comment='任务错误类型索引', index=True)
    error = Column(Text, comment='任务错误次数')

    timecreate = Column(
        BigInteger, server_default=sqlalchemy.func.strftime('%s', 'now') if IS_SQLITE else None, index=True)
    timeupdate = Column(
        BigInteger,
        server_default=sqlalchemy.func.strftime('%s', 'now') if IS_SQLITE else None,
        onupdate=sqlalchemy.func.strftime('%s', 'now') if IS_SQLITE else sqlalchemy.func.unix_timestamp(), index=True)
    time_create = Column(DateTime(timezone=True), server_default=sqlalchemy.func.now(), index=True)
    time_update = Column(DateTime(timezone=True), server_default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now(),
                         index=True)

    __table_args__ = (
        Index('idx_get_task', 'project', "tasktype", 'status', "priority", 'timecanstart'),
        # Index('idx_get_task_qid', 'project', "qid", 'status', "priority", 'timecanstart'),
    )

    @declared_attr
    def uuid(self):
        return Column(
            VARCHAR(64), index=True, unique=True,
            onupdate=f'{self.project}--{self.tasktype}--{self.key}', comment='唯一索引',
            # **({"sqlite_on_conflict_unique":'REPLACE'} if IS_SQLITE else {})
        )

    def gen_uuid(self):
        return f'{self.project}--{self.tasktype}--{self.key}'


class Audit(Base, Mixin):
    __tablename__ = "audit"

    uuid = Column(Integer if IS_SQLITE else BigInteger, primary_key=True, autoincrement=True,
                  # **({"sqlite_on_conflict_primary_key":'REPLACE'} if IS_SQLITE else {})
                  )
    user = Column(String(256), index=True)
    client = Column(String(256), nullable=False, index=True)
    base_url = Column(String(256), index=True)
    url = Column(String(256), index=True)
    method = Column(String(16), nullable=False, index=True)
    headers = Column(Text())
    cookies = Column(Text())
    path_params = Column(Text())
    query_params = Column(Text())
    body = Column(String(1024))
    res = Column(String(512))

    error = Column(Text())

    timecreate = Column(Integer, index=True)
    timeupdate = Column(Integer, index=True)
    time_create = Column(DateTime, index=True)
    time_update = Column(DateTime, index=True)

    @classmethod
    async def add_self(cls, db: Session, req: Request, error=None, res=''):
        time_now = datetime.datetime.now()
        data = dict(
            # uuid=uuid1().__str__().replace('-', ''),
            timecreate=time_now.timestamp(),
            timeupdate=time_now.timestamp(),
            time_create=time_now,
            time_update=time_now,
            client=str(req.client),
            base_url=str(req.base_url),
            url=str(req.url),
            method=str(req.method),
            headers=json.dumps(dict(req.headers) or {})[:1024] or None,
            cookies=json.dumps(dict(req.cookies) or {}) or None,
            path_params=json.dumps(dict(req.path_params) or {}) or None,
            query_params=json.dumps(dict(req.query_params) or {}) or None,
            body=str(await req.body())[:1024],
            res=str(res)[:512],
            error=error if isinstance(error, str) or not error
            else f'[{error.__class__}] {error}\n{traceback.format_exc()}',
            user=(check_jwt_token(req.headers.get('X-Token'), None) or {}).get('sub'),
        )
        s = cls(**data)

        try:
            if not IS_SQLITE:
                db.add(s)
                await db.commit()
        # except sqlalchemy.exc.PendingRollbackError:
        except Exception as e:
            logging.exception(e)
        return s


if __name__ == '__main__':
    print(next(get_db()).query(Audit).filter(*(getattr(Audit, k) == v for k, v in {}.items())).one())
