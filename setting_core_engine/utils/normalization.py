# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any

from silvaengine_utility.serializer import Serializer


def normalize_to_json(value: Any) -> Any:
    """Normalize model data into GraphQL/JSON-safe values."""
    return Serializer.json_normalize(value)


__all__ = ["normalize_to_json"]
