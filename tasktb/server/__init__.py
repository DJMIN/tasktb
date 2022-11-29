from .base import MangerProcess
from .producer import task_publisher
from tasktb.default import SETTINGS
import os
import click
import multiprocessing
import socket
import time


def run_app(host, port):
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG
    from tasktb.web import app

    from tasktb.model import init_db
    init_db()
    # LOGGING_CONFIG['incremental'] = True
    # LOGGING_CONFIG['disable_existing_loggers'] = True
    # LOGGING_CONFIG["loggers"]["watchman"] = {"handlers": ["default"], "level": "INFO"}
    LOGGING_CONFIG["loggers"]["uvicorn"]["propagate"] = False
    LOGGING_CONFIG["formatters"]["default"][
        "fmt"] = '[%(levelprefix)s][%(asctime)s][%(name)s] "%(pathname)s:%(lineno)d" %(message)s'
    LOGGING_CONFIG["formatters"]["access"][
        "fmt"] = '[%(levelprefix)s][%(asctime)s][%(name)s] [%(client_addr)s] "%(request_line)s" %(status_code)s'
    uvicorn.run(app=app, host=host, port=port, workers=1, debug=True, log_config=LOGGING_CONFIG)


def run_all(
        host="0.0.0.0", port=SETTINGS.WEB_PORT, redis_host=SETTINGS.REDIS_HOST,
        redis_port=SETTINGS.REDIS_PORT, redis_db_task=SETTINGS.REDIS_DB_TASK, file='', url='',
        run_redis_produce=True, block=True):
    """web manager runner"""
    if file:
        file_path = os.path.realpath(file)
        SETTINGS.set_setting('SQLALCHEMY_DATABASE_URL', f'sqlite+aiosqlite:///{file_path}')
    elif url:
        SETTINGS.set_setting('SQLALCHEMY_DATABASE_URL', url)

    click.echo(f'start manager: {host}:{port} db路径: {SETTINGS.SQLALCHEMY_DATABASE_URL}')

    # _kill1(port)
    # sockobj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockobj.settimeout(3)
    # sockobj.bind((host, port))
    result = sockobj.connect_ex(('127.0.0.1', port))
    if result == 0:
        click.echo(result)
        raise SystemError('端口被占用了')

    SETTINGS.set_setting("REDIS_HOST", redis_host)
    SETTINGS.set_setting("REDIS_PORT", redis_port)
    SETTINGS.set_setting("REDIS_DB_TASK", redis_db_task)
    multiprocessing.freeze_support()
    main_manger_process = MangerProcess()
    if run_redis_produce:
        main_manger_process.add_process(task_publisher, kwargs=dict(
            host=SETTINGS.REDIS_HOST,
            port=SETTINGS.REDIS_PORT,
            db=SETTINGS.REDIS_DB_TASK, q_max=100
        ))
    # main_manger_process.join_all()
    SETTINGS.set_setting("WEB_HOST", host if host != '0.0.0.0' else '127.0.0.1')
    SETTINGS.set_setting("WEB_PORT", port)
    if block:
        from tasktb.model import update_engine_session
        update_engine_session()
        run_app(host, port)
    else:
        main_manger_process.add_process(run_app, kwargs=dict(
            host=host,
            port=port,
        ), max_times=1)
        time.sleep(10)  # 等待建表等操作
        return main_manger_process
