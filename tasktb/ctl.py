# -*- coding:utf-8 -*-

import click
import uvicorn
import socket
import os
from tasktb.default import WEB_PORT, WEB_HOST, set_global
from tasktb.server import main_manger_process, task_publisher


def run_app(host, port):
    from uvicorn.config import LOGGING_CONFIG
    from tasktb.web import app

    # LOGGING_CONFIG['incremental'] = True
    # LOGGING_CONFIG['disable_existing_loggers'] = True
    # LOGGING_CONFIG["loggers"]["watchman"] = {"handlers": ["default"], "level": "INFO"}
    LOGGING_CONFIG["loggers"]["uvicorn"]["propagate"] = False
    LOGGING_CONFIG["formatters"]["default"][
        "fmt"] = '[%(levelprefix)s][%(asctime)s][%(name)s] "%(pathname)s:%(lineno)d" %(message)s'
    LOGGING_CONFIG["formatters"]["access"][
        "fmt"] = '[%(levelprefix)s][%(asctime)s][%(name)s] [%(client_addr)s] "%(request_line)s" %(status_code)s'
    set_global("WEB_PORT", port)
    uvicorn.run(app=app, host=host, port=port, workers=1, debug=True, log_config=LOGGING_CONFIG)


@click.group()
def ctl():
    pass


@click.command()
@click.option('-h', '--host', default="0.0.0.0", help='web管理端绑定host')
@click.option('-p', '--port', default=WEB_PORT, help='web管理端绑定端口号')
@click.option('-f', '--file', default="", help='web管理端sqlite数据库存储位置路径')
@click.option('-u', '--url', default="", help='web管理端数据库存储位置路径URL')
def run(host, port, file, url):
    """web manager runner"""
    from tasktb.default import set_url, SQLALCHEMY_DATABASE_URL
    if file:
        file_path = os.path.realpath(file)
        set_url(f'sqlite:///{file_path}')
    elif url:
        set_url(url)

    from tasktb.model import init_db
    init_db()

    click.echo(f'start manager: {host}:{port} db路径: {SQLALCHEMY_DATABASE_URL}')

    _kill(port)
    # sockobj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockobj.settimeout(3)
    # sockobj.bind((host, port))
    result = sockobj.connect_ex(('127.0.0.1', port))
    if result == 0:
        click.echo(result)
        raise SystemError('端口被占用了')

    main_manger_process.add_process(task_publisher)
    # main_manger_process.join_all()
    run_app(host, port)


def _kill(port):
    for line in os.popen(f'netstat -anop|grep {port}').readlines():
        if f':{port}' in line and '/python' in line:
            pid = int(line.split('/python')[0].split()[-1])
            for _line in os.popen(f'ps -ef|grep python|grep {pid}').readlines():
                click.echo(_line)
                if 'tasktb.ctl' in _line:
                    click.echo(os.popen(f'kill -7 {pid}').read())
                    # click.echo(os.popen(f'kill -7 {_line.split()[2]}').read())


@click.command()
@click.option('-p', '--port', default=WEB_PORT, help='web管理端绑定端口号')
def kill(port):
    _kill(port)


ctl.add_command(run)
ctl.add_command(kill)


if __name__ == '__main__':
    ctl()
