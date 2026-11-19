"""
CrisisLink – MySQL Database Connection Manager
Provides connection pooling via PyMySQL
"""

import os
import pymysql
import pymysql.cursors
from contextlib import contextmanager


def get_db_config():
    return {
        'host':     os.environ.get('MYSQL_HOST', 'localhost'),
        'port':     int(os.environ.get('MYSQL_PORT', 3306)),
        'user':     os.environ.get('MYSQL_USER', 'crisislink_user'),
        'password': os.environ.get('MYSQL_PASSWORD', 'crisislink_pass'),
        'database': os.environ.get('MYSQL_DATABASE', 'crisislink_db'),
        'charset':  'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
    }


def get_connection():
    """Return a new MySQL connection. Caller is responsible for closing."""
    return pymysql.connect(**get_db_config())


@contextmanager
def get_db():
    """Context manager for database operations – auto commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(query: str, params=None, fetch='all'):
    """
    Utility to run a single parameterized query.
    fetch: 'all' | 'one' | 'none'
    """
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch == 'all':
                return cursor.fetchall()
            elif fetch == 'one':
                return cursor.fetchone()
            else:
                return cursor.lastrowid
