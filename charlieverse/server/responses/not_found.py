from starlette.responses import JSONResponse


class NotFoundResponse(JSONResponse):
    def __init__(self, item: str) -> None:
        super().__init__({"error": f"{item} not found"}, 404)
