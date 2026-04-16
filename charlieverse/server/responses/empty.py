from starlette.responses import JSONResponse


class EmptyResponse(JSONResponse):
    def __init__(self) -> None:
        super().__init__({})
