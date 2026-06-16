class ApiError(Exception):
    """Excepcion generica para errores controlados de la API."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
