from typing import TYPE_CHECKING

from psycopg.conninfo import make_conninfo

if TYPE_CHECKING:
    from mypy_boto3_rds import RDSClient


def get_conninfo(client: RDSClient, host: str, port: int, user: str) -> str:
    """Generate an RDS connection string with a fresh IAM auth token.

    When using connection pool the standard config object gets frozen at pool init time,
    so any connection that attempts to open after the token has expired will fail.
    This ensures the pool can always get a fresh token.
    """
    password = client.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=user)

    return make_conninfo(password=password)
