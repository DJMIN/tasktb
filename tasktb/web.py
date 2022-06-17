import builtins
import datetime
import json
import os.path
import time
import traceback
import typing
import guesstime
import fastapi
import re
import copy
import fastapi.responses
import logging
import collections
import sqlalchemy.engine.row
import d22d

from fastapi import Query, Body
from sqlalchemy.dialects.sqlite import TEXT
from sqlalchemy.sql.expression import func
from sqlalchemy.future import select

from tasktb.model import get_db, Session, IS_ASYNC
from tasktb import model
from tasktb.utils import get_req_data, format_to_table, format_to_form
from tasktb.default import SQLALCHEMY_DATABASE_URL, WEB_PORT
from tasktb.security import create_access_token, check_jwt_token, ACCESS_TOKEN_EXPIRE_MINUTES
from sqlalchemy import desc

from typing import List, Optional, Union, Any
from pydantic import BaseModel, Field

logger = logging.getLogger('tasktb.web')

item_clss = {cls.__tablename__: cls for cls in (
    model.Task,
    model.Taskinstance,
    model.Audit,
)}


def to_datetime(string):
    return guesstime.GuessTime(string, raise_err=False).to_datetime()


def to_int(string):
    try:
        res = int(string)
    except (ValueError, TypeError):
        res = None
    return res


def to_str(string):
    if string is None:
        res = None
    elif not string:
        res = ''
    else:
        res = str(string).strip()
    return res


change_type = {
    "BIGI": to_int,
    "INTE": to_int,
    "VARC": to_str,
    "TEXT": to_str,
    "DATE": to_datetime,
}

app = fastapi.FastAPI()

g = {}


class AuditWithExceptionContextManager:
    """
    用上下文管理器捕获异常，可对代码片段进行错误捕捉，比装饰器更细腻
    """

    def __init__(self, db, req, verbose=None, raise__exception=False, a_cls=model.Audit):
        """
           :param verbose: 打印错误的深度,对应traceback对象的limit，为正整数
        """
        self.db = db
        self.req = req
        self.res = 'ok'
        self.req_data = {}
        self._verbose = verbose
        self._raise__exception = raise__exception
        self.a_cls = a_cls

    async def __aenter__(self):
        self.req_data = await get_req_data(self.req)
        return self

    @staticmethod
    def format_res(message, detail: typing.Union[str, dict, None] = '', suc=True):
        return {
            'code': 20000 if suc else 50000,
            'status': '成功' if suc else "失败",
            'message': message,
            'detail': detail,
        }

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_tb is not None:
            ex_str = f'[{exc_type.__name__}] {str(exc_val)}'
            tb = '\n'.join(
                traceback.format_tb(exc_tb, self._verbose)
                if self._verbose else traceback.format_tb(exc_tb))
            exc_tb_str = f'{ex_str}\n{tb}'
            self.res = self.format_res(message=ex_str, detail=exc_tb_str, suc=False)
            if not self._raise__exception:
                logger.error(exc_tb_str)
        else:
            exc_tb_str = None
        await self.a_cls.add_self(self.db, self.req, exc_tb_str, self.res)

        return not self._raise__exception  # __exit__方法 return True 不重新抛出错误


@app.get('/')
async def html_index():
    return {
        "server": 'tasktb', "msg": f"hello! http://127.0.0.1:{WEB_PORT}/html/item",
        "db": SQLALCHEMY_DATABASE_URL,
        "task_publisher": g.get('task_publisher'),
        "remain_task": g.get('remain_task'),
        'server_time': time.time()
    }


@app.get('/api/getG/{key:str}/{default:str}')
async def get_g(key, default):
    return g.get(key, default)


@app.get('/api/setG/{key:str}/{value:str}')
async def set_g(key, value):
    g[key] = value
    return 'ok'


def guess_type(string: str):
    string = string.strip()
    if '.' in string and len(string.split('.')) == 2 and string.replace('.', '').isdigit():
        return 'float'
    elif string.isdigit():
        return 'int'
    elif string.lower() in ['false', 'true']:
        return 'bool'
    else:
        return 'string'


@app.get('/api/isCtrl')
async def is_ctrl(
        req: fastapi.Request,
        token_data: Union[str, Any] = fastapi.Depends(check_jwt_token)
):
    data = await get_req_data(req)
    db_path = SQLALCHEMY_DATABASE_URL.split('sqlite:///')[-1]
    db_status = 1 if os.path.exists(db_path) and open(db_path, 'rb').read().startswith(b'SQLite format') else 0
    return {
        "status": 1 if data.get('status') else db_status,
        "db_path": SQLALCHEMY_DATABASE_URL,
        "work_path": os.getcwd(),
        "user": token_data,
        'server_time': time.time()
    }


class UserInfo(BaseModel):
    username: str
    password: str


@app.post("/api/login/access-token", summary="用户登录认证")
async def login_access_token(
        *,
        req: fastapi.Request,
        db: Session = fastapi.Depends(get_db),
        user_info: UserInfo,
) -> Any:
    """
    用户登录
    """

    async with AuditWithExceptionContextManager(db, req, a_cls=model.Audit) as ctx:
        # 验证用户账号密码是否正确
        user = model.User.authenticate(db, username=user_info.username, password=user_info.password)

        if not user:
            logger.info(f"用户认证错误, username:{user_info.username} password:{user_info.password}")
            ctx.res = ctx.format_res("用户名或者密码错误", suc=False)
        elif not user.active:
            ctx.res = ctx.format_res("用户未激活", suc=False)

        # 如果用户正确通过 则生成token
        # 设置过期时间
        access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # 登录token 只存放了user.id
        ctx.res = ctx.format_res(
            create_access_token(user.username, expires_delta=access_token_expires),
        )

    return ctx.res


def get_format_type(string_type, string):
    def _bool(_string):
        return not str(_string).lower() in ['false', '0', 'undefined', 'none', 'nan', '0.0']

    func_format = {
        "str": str,
        "string": str,
        "bool": _bool,
        "int": int,
        "float": float,
        "object": json.loads,
        "dict": json.loads,
    }.get(string_type.lower(), str)
    return func_format(string)


@app.get('/api/item/{item_name}/one')
async def get_item(item_name, req: fastapi.Request, db: Session = fastapi.Depends(get_db)):
    async with AuditWithExceptionContextManager(db, req, a_cls=model.Audit) as ctx:
        data = await get_req_data(req)
        cls = item_clss[item_name]
        sql = db.query(cls).filter(*(getattr(cls, k) == v for k, v in data.items())).order_by(
            desc(cls.timeupdate)).limit(2)
        res = [_.to_dict() for _ in sql.all()]
        print(res)
        if len(res) == 1:
            ctx.res = {'data': getattr(builtins, res[0]['valuetype'])(
                res[0].get('value')) if res[0]['valuetype'] in dir(builtins) else res[0].value, "raw": res,
                       "res_raw": res[0]}
        elif len(res) > 1:
            ctx.res = {'data': None, 'err': '结果超过两个，请检查', "raw": res, "res_raw": res[0]}
        else:
            ctx.res = {'data': None, "raw": [], "res_raw": {}}
    return ctx.res


class ListItemParam(BaseModel):
    # uuid: str = Field(..., description="表名称", example="task")
    page: int = Field(..., description="页码", example=1)
    pageSize: int = Field(..., description="页面大小", example=20)
    filters: Optional[list] = Field({}, description="过滤查询，完全匹配，K-V对list", example=[{
        'key': 'user',
        "value": "未登录",
        'like': True,
        'typematch': True,  # True匹配类型，不会自动转成str来搜索
    }])
    sort: Optional[list] = Field([], description="排序", example=[{
        'key': 'timecreate',
        'value': 'asc',
    }, {
        'key': 'time_update',
        'value': 'desc',
    }])

    tableInfo: Optional[bool] = Field(False, description="是否返回表信息", example=False)
    notIn: Optional[dict] = Field({}, description="audit.user not in ['']", example={"audit___user": [""]})
    notNull: Optional[list] = Field([], description="audit.user not null", example=["audit___user"])
    sourceIncludes: Optional[list] = Field([], description="返回表字段", example=["user"])
    join: Optional[dict] = Field({}, description="audit.user = user.username left join",
                                 example={"user": {"user": "username"}})
    ifOuterJoin: Optional[bool] = Field(False, description="是否外连接", example=False)
    range: Optional[dict] = Field(
        {},
        description="按照 2021-10-25 16:25:02 <= audit.time_create < 2021-11-25 16:25:02 过滤",
        example={"audit___timecreate": {"gte": "2021-10-24 16:25:02", "lt": "2023-11-25 16:25:02"}})
    group: Optional[list] = Field([], description="按照某一组字段 分组统计cnt", example=["url", "headers"])
    like: Optional[bool] = Field(True, description="模糊匹配", example=True)
    index: Optional[str] = Field('', description="强制索引", example='')


@app.post('/api/item/{item_name}/list')
async def list_item(
        body: ListItemParam,
        req: fastapi.Request,
        item_name: str = 'audit',
        db: Session = fastapi.Depends(get_db)):
    a_cls = model.Audit
    models = model
    async with AuditWithExceptionContextManager(db, req, a_cls=a_cls) as ctx:
        data = await get_req_data(req)
        if "pageSize" in data:
            limit = int(data.pop('pageSize'))
            if "page" in data:
                offset = max(0, int(data.pop('page')) - 1) * limit
            else:
                offset = 0
        else:
            limit, offset = 0, 0
        cls = item_clss[item_name]

        group = data.get('group', [])
        if not group:
            group_d = None
        else:
            group_d = [getattr(cls, k) for k in group]

        ftr_d = []

        for fd in data.get('filters', []):
            f_nk, f_v, like, typematch = fd['key'], fd['value'], fd.get('like'), fd.get('typematch')
            if "___" in f_nk:
                ftr_table_name, f_k = f_nk.split('___')
            else:
                ftr_table_name, f_k = item_name, f_nk
            ftr_table_cls = getattr(models, "".join(s.capitalize() for s in ftr_table_name.split('_')))
            if like:
                ftr_d.append(
                    func.cast(getattr(ftr_table_cls, f_k), TEXT()) == f_v if not isinstance(
                        f_v, str) else func.cast(getattr(ftr_table_cls, f_k), TEXT()).like(f"%{f_v}%"))
            elif typematch:
                ftr_d.append(getattr(ftr_table_cls, f_k) == f_v)
            else:
                ftr_d.append(func.cast(getattr(ftr_table_cls, f_k), TEXT()) == f_v)

        not_in = data.get('not_in', [])
        if not_in:
            for f_nk, vl in not_in.items():
                if "___" in f_nk:
                    ftr_table_name, f_k = f_nk.split('___')
                else:
                    ftr_table_name, f_k = item_name, f_nk
                ftr_table_cls = getattr(models, "".join(s.capitalize() for s in ftr_table_name.split('_')))
                ftr_d.append(getattr(ftr_table_cls, f_k).notin_(vl))

        not_null = data.get('not_null', [])
        if not_null:
            for f_nk in not_null:
                if "___" in f_nk:
                    ftr_table_name, f_k = f_nk.split('___')
                else:
                    ftr_table_name, f_k = item_name, f_nk
                ftr_table_cls = getattr(models, "".join(s.capitalize() for s in ftr_table_name.split('_')))
                ftr_d.append(getattr(ftr_table_cls, f_k) != None)

        ran = data.get('ran', [])
        if ran:
            ran_d = []
            for k, vd in ran.items():
                if '___' in k:
                    tmp_k = k.split('___')
                    tmp_t_cls = getattr(models, "".join(s.capitalize() for s in tmp_k[0].split('_')))
                    tmp_k = tmp_k[1]
                else:
                    tmp_t_cls = cls
                    tmp_k = k
                ran_k = getattr(tmp_t_cls, tmp_k)
                for d, val in vd.items():
                    if d == 'gt':
                        ran_d.append(ran_k > val)
                    elif d == 'gte':
                        ran_d.append(ran_k >= val)
                    elif d == 'lt':
                        ran_d.append(ran_k < val)
                    elif d == 'lte':
                        ran_d.append(ran_k <= val)
            ftr_d.extend(ran_d)

        join_d = None

        join = data.get('join', {})
        if join:
            for k, v in join.items():
                for join_tname, join_tkey in v.items():
                    join_table_cls = getattr(models, "".join(s.capitalize() for s in join_tname.split('_')))
                    join_table_key = getattr(join_table_cls, join_tkey)
                    join_d = [join_table_cls, getattr(cls, k) == join_table_key]

        param_list = [getattr(cls, k) for k in data.get('sourceIncludes', {})]
        if group_d:
            q_param_list = group_d + [func.count("*").label(f'_cnt')]
        elif not param_list:
            q_param_list = [cls] + ([join_d[0]] if join_d else [])
        else:
            q_param_list = param_list[:]

        q = db.query(*q_param_list)
        if data.get('index'):
            q = q.with_hint(
                cls, f"force index({data.get('index')})", 'mysql'
            ).with_hint(
                cls, f"INDEXED BY {data.get('index')}", 'sqlite'
            )
        if join_d:
            if data.get('ifOuterJoin'):
                q = q.outerjoin(*join_d)
            else:
                q = q.join(*join_d)
        if group_d:
            q = q.group_by(*group_d)
        if len(ftr_d) >= 0:
            q = q.filter(*ftr_d)
        sort = data.get('sort')
        if sort is not None and len(sort) > 0:
            q = q.order_by(
                *(getattr(getattr(cls, flr['key']), flr['value'])()
                  for flr in sort if flr['value'].lower() in ['desc', 'asc']))
        total = q.count()

        if offset and offset >= 0:
            q = q.offset(offset)
        if limit and limit > 0:
            q = q.limit(limit)

        sql_code = str(q)

        results = q.all()
        vres = []
        if join:
            for row, rowl in results:
                tmp = {}
                for d in [row, rowl]:
                    if not d:
                        continue
                    for k, v in d.to_dict().items():
                        tmp[f"{d.__tablename__}___{k}"] = v
                vres.append(tmp)

        else:
            st = [t.name for t in param_list]
            if group_d:
                st.extend([g.name for g in group_d])
                st.append('_cnt')
            for row in results:
                if st and isinstance(row, (tuple, list, sqlalchemy.engine.row.Row)):
                    vres.append({st[i]: r for i, r in enumerate(row)})
                else:
                    vres.append(row.to_dict())

        # res = [d.to_dict() for d in q.all()]
        resp = {
            "server_time": time.time(),
            "data": vres,
            "sql_code": sql_code,
            "total": total,
        }
        if data.get("tableInfo"):
            resp["table_info"] = cls.get_columns_infos()
        ctx.res = ctx.format_res(resp)
    return ctx.res


@app.post('/api/itemNew/{item_name}')
async def set_item_new(
        item_name, req: fastapi.Request,
        db: Session = fastapi.Depends(get_db)):
    async with AuditWithExceptionContextManager(db, req, a_cls=model.Audit) as ctx:
        data = await get_req_data(req)
        cls = item_clss[item_name]
        cls_info = cls.get_columns_info()
        data_kvs = {k: change_type[cls_info[k]['type_str'][:4]](v) for k, v in data.items()}
        c = cls(**data_kvs).update_self(**data_kvs)
        db.add(c)
        db.commit()
        ctx.res = ctx.format_res(c.to_dict())
    return ctx.res


@app.post('/api/item/{item_name}')
async def set_item(
        item_name, req: fastapi.Request,
        db: Session = fastapi.Depends(get_db),
        db_log: Session = fastapi.Depends(get_db)):
    """merge"""
    async with AuditWithExceptionContextManager(db_log, req, a_cls=model.Audit) as ctx:
        data = await get_req_data(req)
        cls = item_clss[item_name]
        cls_info = cls.get_columns_info()
        data_kvs = {k: change_type[cls_info[k]['type_str'][:4]](v) for k, v in data.items()}
        c = cls(**data_kvs).update_self(**data_kvs)
        db.merge(c)
        db.commit()
        ctx.res = ctx.format_res(c.to_dict())
    return ctx.res


@app.post('/api/items/{item_name}')
async def set_items(
        item_name, req: fastapi.Request,
        db: Session = fastapi.Depends(get_db),
        db_log: Session = fastapi.Depends(get_db)):
    """merge many"""
    async with AuditWithExceptionContextManager(db_log, req, a_cls=model.Audit) as ctx:
        data = await get_req_data(req)
        cls = item_clss[item_name]
        cls_info = cls.get_columns_info()

        # Find all customers that needs to be updated and build mappings
        pk = 'uuid'
        pkd = getattr(cls, pk)
        has_iid = 'iid' in cls_info
        # pk = cls.get_primary_keys()[0]
        # TODO pks
        # pks = cls.get_primary_keys()

        t0 = time.time()

        from sqlalchemy.dialects.postgresql import insert as insert_func_postgresql
        # from sqlalchemy.dialects.mysql import insert as insert_func_mysql

        values = [{k: change_type[cls_info[k]['type_str'][:4]](v) for k, v in d.items()} for d in data['data']]

        if (
                SQLALCHEMY_DATABASE_URL.startswith('mysql') or
                SQLALCHEMY_DATABASE_URL.startswith('sqlite')):
            def bulk_upsert_mappings(_data):
                entries_to_update = []
                entries_to_put = []
                _t0 = time.time()
                if has_iid:
                    has_in_db = {r[0]: r[1] for r in db.query(pkd, getattr(cls, 'iid')).filter(
                        getattr(cls, pk).in_(list(_d[pk] for _d in _data))).all()}
                else:
                    has_in_db = set(r[0] for r in db.query(pkd).filter(
                        getattr(cls, pk).in_(list(_d[pk] for _d in _data))).all())

                print(
                    "Total time for upsert with MAPPING select "
                    + str(len(_data))
                    + " records "
                    + str(time.time() - t0)
                    + " sec"
                )

                for _d in _data:
                    if _d[pk] in has_in_db:
                        if has_iid:
                            _d['iid'] = has_in_db[_d[pk]]
                        entries_to_update.append(_d)
                    else:
                        entries_to_put.append(_d)

                print(f'put:{len(entries_to_put)}')
                if entries_to_put:
                    _stmt = cls.__table__.insert()
                    model.engine.execute(
                        _stmt,
                        entries_to_put
                    )

                # db.bulk_insert_mappings(cls, entries_to_put)
                if entries_to_update:
                    db.bulk_update_mappings(cls, entries_to_update)
                    db.commit()

                print(
                    "Total time for upsert with MAPPING update "
                    + str(len(_data))
                    + " records "
                    + str(time.time() - t0)
                    + " sec"
                    + " inserted : "
                    + str(len(entries_to_put))
                    + " - updated : "
                    + str(len(entries_to_update))
                )

            bulk_upsert_mappings(values)
        elif SQLALCHEMY_DATABASE_URL.startswith('postgresql'):
            insert_func = insert_func_postgresql
            stmt = insert_func(cls).values(values)
            stmt = stmt.on_conflict_do_update(
                # Let's use the constraint name which was visible in the original posts error msg
                constraint=pk,

                # The columns that should be updated on conflict
                set_={
                    key: getattr(stmt.excluded, key)
                    for key in cls_info
                }
            )
            model.engine.execute(
                stmt
            )
        else:
            stmt = cls.__table__.insert()
            stmt = stmt.prefix_with("OR REPLACE")
            model.engine.execute(
                stmt,
                values
            )
        model.engine.execute("select 1").scalar()
        # db.execute("VACUUM")  # 清理已删除的文件空间
        # db.commit()
        res = f"SqlAlchemy Core Insert: Total time for {len(data['data'])} records " + str(time.time() - t0) + " secs"
        ctx.res = ctx.format_res(res)
    return ctx.res


@app.delete('/api/item/{item_name}')
async def del_item(item_name, body: ListItemParam,
                   req: fastapi.Request, db: Session = fastapi.Depends(get_db)):
    async with AuditWithExceptionContextManager(db, req, a_cls=model.Audit) as ctx:
        data = await get_req_data(req)
        if "pageSize" in data:
            limit = int(data.pop('pageSize'))
            if "page" in data:
                offset = max(0, int(data.pop('page')) - 1) * limit
            else:
                offset = 0
        else:
            limit, offset = 0, 0
        cls = item_clss[item_name]
        query_d = db.query(cls).filter(
            *(getattr(cls, flr['key']) == flr['value']
              for flr in data.get('filters', []))
        )
        if offset:
            query_d = query_d.offset(offset)
        if limit:
            query_d = query_d.limit(limit)
        res = []
        for d in query_d.all():
            res.append(d.to_dict())
            db.delete(d)
            db.commit()
        ctx.res = {
            "server_time": time.time(),
            "data": res,
            "total": len(res)
        }
    return ctx.res


@app.get('/api/itemCleanByTable/{item_name}')
async def del_s_item_pk(
        item_name,
        req: fastapi.Request, db: Session = fastapi.Depends(get_db)):
    async with AuditWithExceptionContextManager(db, req, a_cls=model.Audit) as ctx:
        cls = item_clss[item_name]
        db.query(cls).delete()
        db.commit()
        db.execute("VACUUM")  # 清理已删除的文件空间
        db.commit()
        ctx.res = {
            "server_time": time.time(),
        }
    return ctx.res


@app.get('/api/itemCleanByTable/{item_name}')
async def del_item_pk(
        item_name,
        req: fastapi.Request, db: Session = fastapi.Depends(get_db)):
    async with AuditWithExceptionContextManager(db, req, a_cls=model.Audit) as ctx:
        cls = item_clss[item_name]
        db.query(cls).delete()
        db.commit()
        db.execute("VACUUM")
        db.commit()
        ctx.res = {
            "server_time": time.time(),
        }
    return ctx.res


class ListItemPKParam(BaseModel):
    # uuid: str = Field(..., description="表名称", example="task")
    pks: list = Field(..., description="过滤查询，完全匹配，K-V对list", example=[
        '1', 2, '3'
    ])


@app.delete('/api/itemByPK/{item_name}')
async def del_item_pk(
        item_name, body: ListItemPKParam,
        req: fastapi.Request, db: Session = fastapi.Depends(get_db)):
    async with AuditWithExceptionContextManager(db, req, a_cls=model.Audit) as ctx:
        cls = item_clss[item_name]
        res = []
        for pk in body.pks:
            pk_keys = cls.get_primary_keys()
            for d in db.query(cls).filter(
                    *(getattr(cls, pk_key) == pk
                      for pk_key in pk_keys)
            ).all():
                res.append(d.to_dict())
                db.delete(d)
                db.commit()
        ctx.res = {
            "server_time": time.time(),
            "data": res,
            "total": len(res)
        }
    return ctx.res


@app.get('/html/item/{item_name:path}', response_class=fastapi.responses.HTMLResponse)
async def html_list_secret(
        item_name,
        req: fastapi.Request,
        db: Session = fastapi.Depends(get_db)):
    data = await get_req_data(req)
    cls = item_clss.get(item_name)
    if not cls:
        return "无此表格，请在</br>{}</br>中选择".format(
            '</br>'.join(f'<a href="/html/item/{key}">{key}</a>' for key in item_clss.keys())
        )
    res = list(
        d.to_dict()
        for d in db.query(cls).filter(*(getattr(cls, k) == v for k, v in data.items())).limit(1000).all()
    )
    return format_to_form(f"/api/item/{item_name}", cls.get_columns_infos()) + f'''一共有{str(
        db.query(cls).filter(*(getattr(cls, k) == v for k, v in data.items())).count())}条数据''' + format_to_table(
        res, keys=cls.get_columns())
