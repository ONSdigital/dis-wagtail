from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper


class DatabaseWrapper(PostgresDatabaseWrapper):
    """A modified database backend which forces the connection to be read-only."""

    def init_connection_state(self) -> None:
        super().init_connection_state()
        # with self.connection.cursor() as c:
        #     c.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
        # self.connection.set_read_only(True)
