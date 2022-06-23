from .base import main_manger_process
from .producer import task_publisher
from tasktb.default import WEB_PORT, REDIS_HOST, REDIS_PORT, REDIS_DB_TASK, set_url, SQLALCHEMY_DATABASE_URL, set_global
import os
import click
import socket


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
        host="0.0.0.0", port=WEB_PORT, redis_host=REDIS_HOST,
        redis_port=REDIS_PORT, redis_db_task=REDIS_DB_TASK, file='', url=''):
    """web manager runner"""
    if file:
        file_path = os.path.realpath(file)
        set_url(f'sqlite+aiosqlite:///{file_path}')
    elif url:
        set_url(url)

    click.echo(f'start manager: {host}:{port} db路径: {SQLALCHEMY_DATABASE_URL}')

    # _kill1(port)
    # sockobj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockobj.settimeout(3)
    # sockobj.bind((host, port))
    result = sockobj.connect_ex(('127.0.0.1', port))
    if result == 0:
        click.echo(result)
        raise SystemError('端口被占用了')

    set_global("REDIS_HOST", redis_host)
    set_global("REDIS_PORT", redis_port)
    set_global("REDIS_DB_TASK", redis_db_task)
    main_manger_process.add_process(task_publisher)
    # main_manger_process.join_all()
    set_global("WEB_HOST", host if host != '0.0.0.0' else '127.0.0.1')
    set_global("WEB_PORT", port)
    run_app(host, port)
