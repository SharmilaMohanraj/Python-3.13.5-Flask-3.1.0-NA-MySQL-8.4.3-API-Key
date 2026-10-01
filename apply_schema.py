"""One-off schema-apply helper, run by start.sh/start.bat before the app
boots. Waits for MySQL to accept connections, then executes schema.sql's
statements (each is idempotent: CREATE DATABASE/TABLE IF NOT EXISTS).
"""
import logging
import sys
import time
from pathlib import Path

import pymysql

from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
MAX_ATTEMPTS = 30
RETRY_SECONDS = 2


def _wait_for_mysql() -> pymysql.connections.Connection:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return pymysql.connect(
                host=config.MYSQL_HOST,
                port=config.MYSQL_PORT,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD,
                autocommit=True,
            )
        except pymysql.MySQLError as exc:
            logger.info("MySQL not ready yet (attempt %s/%s): %s", attempt, MAX_ATTEMPTS, exc)
            time.sleep(RETRY_SECONDS)
    logger.error("MySQL never became reachable after %s attempts", MAX_ATTEMPTS)
    sys.exit(1)


def apply_schema() -> None:
    connection = _wait_for_mysql()
    try:
        raw_text = SCHEMA_PATH.read_text()
        # Strip full-line SQL comments before splitting on ';' — a naive
        # split-then-discard-if-the-whole-chunk-starts-with-'--' would drop
        # every statement that happens to be preceded by a comment line.
        sql_text = "\n".join(
            line for line in raw_text.splitlines() if not line.strip().startswith("--")
        )
        statements = [s.strip() for s in sql_text.split(";") if s.strip()]
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        logger.info("Schema applied successfully (%s statements)", len(statements))
    finally:
        connection.close()


if __name__ == "__main__":
    apply_schema()
