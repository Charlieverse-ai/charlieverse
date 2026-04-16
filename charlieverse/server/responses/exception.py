from starlette.responses import JSONResponse


class ExceptionResponse(JSONResponse):
    def __init__(self, error: Exception) -> None:
        super().__init__({"error": str(error)}, 500)
