from starlette.responses import JSONResponse


class SavedResponse(JSONResponse):
    def __init__(self) -> None:
        super().__init__({"saved": True})
