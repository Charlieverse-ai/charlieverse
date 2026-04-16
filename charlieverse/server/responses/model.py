from pydantic import BaseModel, TypeAdapter
from starlette.responses import Response


class ModelResponse(Response):
    def __init__(self, model: BaseModel) -> None:
        super().__init__(model.model_dump_json(by_alias=True), 200, media_type="application/json")


class ModelListResponse(Response):
    def __init__[T: BaseModel](self, models: list[T]) -> None:
        json = TypeAdapter(list[T]).dump_json(models, by_alias=True)
        super().__init__(json, 200, media_type="application/json")
