"""采集器基类"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class ResourceInfo:
    source: str
    external_id: str
    title: str
    url: str = ""
    local_path: str = ""
    metadata: dict = field(default_factory=dict)


class BaseCollector:
    source: str = "base"

    def collect(self) -> list[ResourceInfo]:
        raise NotImplementedError
