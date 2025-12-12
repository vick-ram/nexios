
from typing import Any, Optional

import aiomysql
import mysql
import mysql.connector
import pymysql

from nexios.orm.connection import SyncDatabaseConnection, AsyncDatabaseConnection


class MySQLConnection_:

    @staticmethod
    def connection(conn: Any) -> Optional["SyncDatabaseConnection"]:
        if isinstance(conn, mysql.connector.connection.MySQLConnection):
            from nexios.orm.dbapi.mysql.mysql_connector_ import MySQLConnectorConnection
            return MySQLConnectorConnection(conn)
        elif isinstance(conn, pymysql.Connection):
            from nexios.orm.dbapi.mysql.pymysql_ import PyMySQLConnection
            return PyMySQLConnection(conn)
        return None
    
    @staticmethod
    async def connection_async(conn: Any) -> Optional["AsyncDatabaseConnection"]:
        if isinstance(conn, aiomysql.Connection):
            from nexios.orm.dbapi.mysql.aiomysql_ import MySQLAioMySQLConnection
            return MySQLAioMySQLConnection(conn)
        return None