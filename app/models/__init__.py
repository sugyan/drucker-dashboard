from flask_sqlalchemy import SQLAlchemy
from utils.env_loader import (
    DB_MODE,
    DB_MYSQL_HOST,
    DB_MYSQL_PORT,
    DB_MYSQL_DBNAME,
    DB_MYSQL_USER,
    DB_MYSQL_PASSWORD,
)

db = SQLAlchemy(
    session_options={
        "autocommit": False,
        "autoflush": False
    }
)

def db_url():
    """ Get full URL for DB

    :TODO: Make configuarable of template of URL and encoding
    :TODO: Use Enum for DB_MODE
    :TODO: Use an appropriate "Exception"
    """
    if DB_MODE == "sqlite":
        url = f'sqlite:///db.sqlite3'
    elif DB_MODE == "mysql":
        host = DB_MYSQL_HOST
        port = DB_MYSQL_PORT
        db_name = DB_MYSQL_DBNAME
        user = DB_MYSQL_USER
        password = DB_MYSQL_PASSWORD
        url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8'
    else:
        raise Exception("Invalid DB_MODE.")
    return url

from models.kubernetes import Kubernetes
from models.application import Application
from models.service import Service
from models.model import Model
