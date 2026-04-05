from starlette.responses import JSONResponse


class DeletedResponse(JSONResponse):
    def __init__(self) -> None:
        super().__init__({"deleted": True}, 200)
