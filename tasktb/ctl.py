# -*- coding:utf-8 -*-

import click
import socket
import os
import sys


from tasktb.default import WEB_PORT, set_global
from tasktb.server import main_manger_process, task_publisher, run_app
from tasktb.default import set_url, SQLALCHEMY_DATABASE_URL


@click.group()
def ctl():
    pass


def _run(host, port, file, url):
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

    main_manger_process.add_process(task_publisher)
    # main_manger_process.join_all()
    set_global("WEB_HOST", host if host != '0.0.0.0' else '127.0.0.1')
    set_global("WEB_PORT", port)
    run_app(host, port)


@click.command()
@click.option('-h', '--host', default="0.0.0.0", help='web管理端绑定host')
@click.option('-p', '--port', default=WEB_PORT, help='web管理端绑定端口号')
@click.option('-f', '--file', default="", help='web管理端sqlite数据库存储位置路径')
@click.option('-u', '--url', default="", help='web管理端数据库存储位置路径URL')
def run(host, port, file, url):
    _run(host, port, file, url)


def _kill1(port):
    if port:
        _port = f" | grep {port}"
    else:
        _port = ''
    for line in os.popen(f'netstat -anop{_port}').readlines():
        if f':{port}' in line and '/python' in line:
            pid = int(line.split('/python')[0].split()[-1])
            for idx, _line in enumerate(os.popen(f'ps -ef|grep python|grep {pid}').readlines()):
                if 'tasktb' in _line and "stop" not in _line:
                    click.echo(_line)
                    # click.echo(f"11111 {os.popen(f'kill -7 {pid}').read()}")
                    click.echo(os.popen(f'kill -7 {_line.split()[1]}').read())


def _kill(port):
    if port:
        _port = f" | grep {port}"
    else:
        _port = ''
    if sys.platform != 'win32':
        for idx, _line in enumerate(os.popen(f'ps -ef | grep python | grep "tasktb.ctl run"{_port}').readlines()):
            if ' ps -ef | grep' not in _line:
                click.echo(_line.strip())
                pid = int(_line.split()[1])
                click.echo(f"kill -7 {pid}: {os.popen(f'kill -7 {pid}').read()}")


@click.command()
@click.option('-py', '--python', default='python3', help='python版本，默认为：python')
@click.option('-h', '--host', default="0.0.0.0", help='web管理端绑定host')
@click.option('-p', '--port', default=WEB_PORT, help='web管理端绑定端口号')
@click.option('-f', '--file', default="", help='web管理端sqlite数据库存储位置路径')
@click.option('-u', '--url', default="", help='web管理端数据库存储位置路径URL')
@click.option('-l', '--logfile', default="tasktb.log", help='日志位置路径')
def start(python, host, port, file, url, logfile):
    # sockobj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockobj.settimeout(3)
    # sockobj.bind((host, port))
    result = sockobj.connect_ex(('127.0.0.1', port))
    if result == 0:
        click.echo(result)
        raise SystemError('端口被占用了')

    if file:
        file_path = os.path.realpath(file)
        url = f'sqlite+aiosqlite:///{file_path}'
    elif url:
        url = url
    else:
        url = SQLALCHEMY_DATABASE_URL

    cmd = f'nohup {python} -m tasktb.ctl run -u "{url}" -h {host} -p {port} > {logfile} 2>&1 &'
    click.echo(cmd)
    res = os.popen(cmd).read().strip()
    if not res:
        click.echo('started')
    else:
        click.echo(res)


@click.command()
@click.option('-p', '--port', default='', help='web管理端绑定端口号')
def stop(port):
    _kill(port)
    _kill1(port)


@click.command()
@click.option('-p', '--port', default='', help='web管理端绑定端口号')
def show(port):
    if sys.platform != 'win32':
        if port:
            _port = f" | grep {port}"
        else:
            _port = ''
        for idx, _line in enumerate(os.popen(f'ps -ef | grep python | grep "tasktb.ctl run"{_port}').readlines()):
            if ' ps -ef | grep' not in _line:
                click.echo(f"{idx}: {_line.strip()}")


ctl.add_command(run)
ctl.add_command(start)
ctl.add_command(stop)
ctl.add_command(show)


"""
/usr/local/python3.9/lib/python3.9/runpy.py:127: RuntimeWarning: 'tasktb.ctl' found in sys.modules after
 import of package 'tasktb', but prior to execution of 'tasktb.ctl'; this may result in unpredictable behaviour
  warn(RuntimeWarning(msg))
https://stackoverflow.com/questions/43393764/python-3-6-project-structure-leads-to-runtimewarning
"""
# if __name__ == '__main__':
ctl()
