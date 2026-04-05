"""Returns a permalink to an entity in the dashboard."""

from charlieverse.types.id import ModelId


class PermalinkResponse:
    url: str

    # TODO: Make kind a type
    def __init__(self, kind: str, id: ModelId):
        from charlieverse.config import config

        self.url = f"{config.server.dashboard_url()}{kind}/{id}"
