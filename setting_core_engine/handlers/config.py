# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "jeffreyw"

import logging
import os
from typing import Any, Dict, List

import boto3

from ..models import utils


class Config:
    """
    Centralized Configuration Class
    Manages shared configuration variables across the application.
    """

    aws_lambda = None
    aws_s3 = None
    # schemas = {}
    module_bucket_name = None
    module_zip_path = None
    module_extract_path = None

    # Cache Configuration
    CACHE_TTL = 1800  # 30 minutes default TTL
    CACHE_ENABLED = True

    # Cache name patterns for different modules
    CACHE_NAMES = {
        "models": "setting_core_engine.models",
        "queries": "setting_core_engine.queries",
    }

    # Cache entity metadata (module paths, getters, cache key templates)
    CACHE_ENTITY_CONFIG = {
        "theme_setting": {
            "module": "setting_core_engine.models.theme_setting",
            "model_class": "ThemeSettingModel",
            "getter": "get_theme_setting",
            "list_resolver": "setting_core_engine.queries.theme_setting.resolve_theme_setting_list",
            "cache_keys": ["context:partition_key", "key:theme_uuid"],
        },
        "setting": {
            "module": "setting_core_engine.models.setting",
            "model_class": "SettingModel",
            "getter": "get_setting",
            "list_resolver": "setting_core_engine.queries.setting.resolve_setting_list",
            "cache_keys": ["context:partition_key", "key:setting_uuid"],
        },
    }

    # Entity cache dependency relationships
    CACHE_RELATIONSHIPS = {}

    @classmethod
    def initialize(cls, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initialize configuration setting.
        Args:
            logger (logging.Logger): Logger instance for logging.
            **setting (Dict[str, Any]): Configuration dictionary.
        """
        try:
            cls._set_parameters(setting)
            cls._initialize_aws_services(setting)
            if setting.get("initialize_tables"):
                cls._initialize_tables(logger)
            logger.info("Configuration initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize configuration.")
            raise e

    @classmethod
    def _set_parameters(cls, setting: Dict[str, Any]) -> None:
        """
        Set application-level parameters.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        pass

    @classmethod
    def _initialize_tables(cls, logger: logging.Logger) -> None:
        """
        Initialize database tables by calling the utils._initialize_tables() method.
        This is an internal method used during configuration setup.
        """
        utils._initialize_tables(logger)

    @classmethod
    def _initialize_aws_services(cls, setting: Dict[str, Any]) -> None:
        """
        Initialize AWS services, such as the S3 client.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        pass

    @classmethod
    def get_cache_entity_config(cls) -> Dict[str, Dict[str, Any]]:
        """Get cache configuration metadata for each entity type."""
        return cls.CACHE_ENTITY_CONFIG

    @classmethod
    def get_cache_name(cls, module_type: str, model_name: str) -> str:
        """
        Generate standardized cache names.

        Args:
            module_type: 'models' or 'queries'
            model_name: Name of the model (e.g., 'corporation_profile', 'place')

        Returns:
            Standardized cache name string
        """
        base_name = cls.CACHE_NAMES.get(
            module_type, f"setting_core_engine.{module_type}"
        )
        return f"{base_name}.{model_name}"

    @classmethod
    def get_cache_ttl(cls) -> int:
        """Get the configured cache TTL."""
        return cls.CACHE_TTL

    @classmethod
    def is_cache_enabled(cls) -> bool:
        """Check if caching is enabled."""
        return cls.CACHE_ENABLED

    @classmethod
    def get_cache_relationships(cls) -> Dict[str, List[Dict[str, str]]]:
        """Get entity cache dependency relationships."""
        return cls.CACHE_RELATIONSHIPS

    @classmethod
    def get_entity_children(cls, entity_type: str) -> List[Dict[str, str]]:
        """Get child entities for a specific entity type."""
        return cls.CACHE_RELATIONSHIPS.get(entity_type, [])
