from wagtail.search.backends.database.postgres.postgres import Index, PostgresSearchBackend


class ONSPostgresSearchBackend(PostgresSearchBackend):
    """A custom search backend which ensures the index uses the correct database backend.

    TODO: Remove when https://github.com/wagtail/wagtail/pull/12508 ships (Wagtail 6.4).
    """

    def get_index_for_model(self, model: str, db_alias: str | None = None) -> Index:
        # Always defer to DB router for search backend
        return super().get_index_for_model(model, None)
