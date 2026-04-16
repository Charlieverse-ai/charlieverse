from starlette.responses import JSONResponse


class MissingRequired(JSONResponse):
    def __init__(self, fields: str) -> None:
        super().__init__({"error": f"Missing Required: {fields}"}, 400)
