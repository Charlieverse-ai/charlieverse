from pydantic import BaseModel
from starlette.responses import Response


class CreatedResponse(Response):
    def __init__(self, model: BaseModel) -> None:
        super().__init__(model.model_dump_json(by_alias=True), 201, media_type="application/json")
