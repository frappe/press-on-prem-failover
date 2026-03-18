from typing import TypedDict


class BenchInfo(TypedDict):
    image: str
    web_port: int
    socketio_port: int


class BenchSiteMapping(TypedDict):
    sites: dict[str, int]