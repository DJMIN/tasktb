from .base import main_manger_process
from .producer import task_publisher


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
