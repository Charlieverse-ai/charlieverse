from starlette.responses import JSONResponse


class DeletedResponse(JSONResponse):
    """200 response signalling a successful deletion."""

    def __init__(self) -> None:
        super().__init__({"deleted": True}, 200)


class DeletedCountResponse(JSONResponse):
    """200 response carrying the count of rows removed by a bulk cleanup."""

    def __init__(self, count: int) -> None:
        super().__init__({"deleted": count}, 200)
