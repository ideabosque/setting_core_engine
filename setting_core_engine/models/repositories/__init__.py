# -*- coding: utf-8 -*-
"""Repository abstraction boundary for dual-backend persistence."""
from __future__ import print_function

from .dispatch import clear_registry, get_repo, register_repo

__all__ = ["clear_registry", "get_repo", "register_repo"]
