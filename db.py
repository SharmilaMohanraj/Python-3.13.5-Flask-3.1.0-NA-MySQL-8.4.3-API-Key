"""Database connection and query-helper layer (Data Access Layer).

All SQL in the application flows through these three functions. Every
function opens a fresh connection, uses parameterized queries exclusively
(never string-concatenated SQL), and closes the connection before
returning — simple and safe for a request-scoped workload.
"""
import logging

import pymysql
import pymysql.cursors

from config import config

logger = logging.getLogger(__name__)


def get_connection() -> pymysql.connections.Connection:
    """Open a new PyMySQL connection using DictCursor and autocommit."""
    try:
        return pymysql.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DB,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    except pymysql.MySQLError:
        logger.exception("Failed to connect to MySQL at %s:%s", config.MYSQL_HOST, config.MYSQL_PORT)
        raise


def execute(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE statement.

    Returns the last inserted row id for INSERT statements, otherwise the
    number of affected rows.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            affected = cursor.execute(sql, params)
            result = cursor.lastrowid or affected
            logger.debug("Executed statement, affected_rows=%s, lastrowid=%s", affected, cursor.lastrowid)
            return result
    except pymysql.MySQLError:
        logger.exception("Database execute failed")
        raise
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Execute a SELECT expected to return at most one row."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            logger.debug("query_one returned %s row", 1 if row else 0)
            return row
    except pymysql.MySQLError:
        logger.exception("Database query_one failed")
        raise
    finally:
        conn.close()


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT and return every matching row."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            logger.debug("query_all returned %s rows", len(rows))
            return rows
    except pymysql.MySQLError:
        logger.exception("Database query_all failed")
        raise
    finally:
        conn.close()
