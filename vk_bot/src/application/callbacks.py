from typing import TypedDict


class RegionPayload(TypedDict):
    cmd: str
    region: str


class RetryRegionPayload(TypedDict):
    cmd: str
