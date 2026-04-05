from typing import TypeVar

from pydantic import BaseModel, TypeAdapter
from starlette.responses import Response


class ModelResponse(Response):
    def __init__(self, model: BaseModel) -> None:
        super().__init__(model.model_dump_json(), 200, media_type="application/json")


T = TypeVar("T", bound=BaseModel)


class ModelListResponse(Response):
    def __init__(self, models: list[T]) -> None:
        json = TypeAdapter(list[T]).dump_json(models)
        super().__init__(json, 200, media_type="application/json")
