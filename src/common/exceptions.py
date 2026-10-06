class TemporaryError(Exception):
    """Временная ошибка (сеть, БД, внешний сервис) - операцию можно повторить."""


class DatabaseUnavailable(TemporaryError):
    pass
