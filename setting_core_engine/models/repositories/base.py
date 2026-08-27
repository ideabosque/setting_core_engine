# -*- coding: utf-8 -*-
"""Repository abstraction boundary for dual-backend persistence."""
from __future__ import print_function

__author__ = "bibow"

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class EntityRepository(ABC):
    """Base contract implemented by backend-specific repositories."""

    @property
    @abstractmethod
    def entity_type(self) -> str:
        ...

    @abstractmethod
    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def count(self, **keys: Any) -> int:
        ...

    @abstractmethod
    def list(self, info: Any, **filters: Any) -> Any:
        ...

    @abstractmethod
    def insert_update(self, info: Any, **kwargs: Any) -> Any:
        ...

    @abstractmethod
    def delete(self, info: Any, **kwargs: Any) -> bool:
        ...
