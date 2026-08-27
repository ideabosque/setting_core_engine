# -*- coding: utf-8 -*-
"""Backend dispatch boundary for repository selection."""
from __future__ import print_function

__author__ = "bibow"

from typing import Dict

from ...handlers.config import Config
from .base import EntityRepository


_repo_registry: Dict[str, Dict[str, EntityRepository]] = {
    "dynamodb": {},
    "postgresql": {},
}

_dynamodb_repos_initialized = False
_postgresql_repos_initialized = False


def register_repo(backend: str, entity_type: str, repo: EntityRepository) -> None:
    if backend not in _repo_registry:
        raise ValueError(f"Unknown backend: {backend}")
    _repo_registry[backend][entity_type] = repo


def get_repo(entity_type: str) -> EntityRepository:
    backend = Config.DB_BACKEND
    repo = _repo_registry.get(backend, {}).get(entity_type)
    if repo is None:
        if backend == "dynamodb":
            _init_dynamodb_repos()
            repo = _repo_registry["dynamodb"].get(entity_type)
        elif backend == "postgresql":
            _init_postgresql_repos()
            repo = _repo_registry["postgresql"].get(entity_type)

    if repo is None:
        raise KeyError(
            f"No repository registered for entity '{entity_type}' "
            f"on backend '{backend}'"
        )
    return repo


def _init_dynamodb_repos() -> None:
    global _dynamodb_repos_initialized
    if _dynamodb_repos_initialized:
        return
    _dynamodb_repos_initialized = True

    from .dynamodb import register_all

    register_all(_repo_registry["dynamodb"])


def _init_postgresql_repos() -> None:
    global _postgresql_repos_initialized
    if _postgresql_repos_initialized:
        return
    _postgresql_repos_initialized = True

    from .postgresql import register_all

    register_all(_repo_registry["postgresql"])


def clear_registry() -> None:
    global _dynamodb_repos_initialized, _postgresql_repos_initialized
    _repo_registry["dynamodb"].clear()
    _repo_registry["postgresql"].clear()
    _dynamodb_repos_initialized = False
    _postgresql_repos_initialized = False
