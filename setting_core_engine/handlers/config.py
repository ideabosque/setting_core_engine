# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import os
from typing import Any, Dict, List
from urllib.parse import quote_plus

import boto3

from ..models import utils


class Config:
    """
    Centralized Configuration Class
    Manages shared configuration variables across the application.
    """

    _initialized: bool = False

    # Backend selection: "dynamodb" (default) or "postgresql".
    DB_BACKEND: str = "dynamodb"
    db_session = None

    # Table prefix for shared PostgreSQL databases
    PG_TABLE_PREFIX: str = "sce_"

    aws_lambda = None
    aws_s3 = None
    module_bucket_name = None
    module_zip_path = None
    module_extract_path = None
    logger = None
    _setting: Dict[str, Any] = {}

    # Cache Configuration
    CACHE_TTL = 1800  # 30 minutes default TTL
    CACHE_ENABLED = True

    CACHE_NAMES = {
        "models": "setting_core_engine.models",
        "queries": "setting_core_engine.queries",
    }

    # DynamoDB cache config — populated; PG repos don't use @method_cache
    CACHE_ENTITY_CONFIG_DYNAMODB = {
        "theme_setting": {
            "module": "setting_core_engine.models.dynamodb.theme_setting",
            "model_class": "ThemeSettingModel",
            "getter": "get_theme_setting",
            "list_resolver": "setting_core_engine.queries.theme_setting.resolve_theme_setting_list",
            "cache_keys": ["context:partition_key", "key:theme_uuid"],
        },
        "setting": {
            "module": "setting_core_engine.models.dynamodb.setting",
            "model_class": "SettingModel",
            "getter": "get_setting",
            "list_resolver": "setting_core_engine.queries.setting.resolve_setting_list",
            "cache_keys": ["context:partition_key", "key:setting_uuid"],
        },
    }

    CACHE_RELATIONSHIPS_DYNAMODB = {}

    # PostgreSQL cache config — empty (PG repos don't use @method_cache)
    CACHE_ENTITY_CONFIG_POSTGRESQL: Dict[str, Dict[str, Any]] = {}
    CACHE_RELATIONSHIPS_POSTGRESQL: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def initialize(cls, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """Initialize configuration for the selected persistence backend."""
        if cls._initialized:
            return
        try:
            cls.logger = logger
            cls._setting = setting
            cls._set_parameters(setting)

            cls.DB_BACKEND = str(setting.get("db_backend", "dynamodb")).lower()
            if cls.DB_BACKEND == "dynamodb":
                cls._initialize_aws_services(setting)
            elif cls.DB_BACKEND == "postgresql":
                cls._initialize_db_session(setting)
                cls._initialize_optional_aws_services(setting)
            else:
                raise ValueError(f"Unknown db_backend: {cls.DB_BACKEND}")

            if setting.get("initialize_tables"):
                cls._initialize_tables(logger)
            cls._initialized = True
            logger.info(
                f"Configuration initialized successfully (db_backend={cls.DB_BACKEND})."
            )
        except Exception as e:
            logger.exception("Failed to initialize configuration.")
            raise e

    @classmethod
    def get_setting(cls) -> Dict[str, Any]:
        return cls._setting

    @classmethod
    def _set_parameters(cls, setting: Dict[str, Any]) -> None:
        if "cache_enabled" in setting:
            cls.CACHE_ENABLED = setting.get("cache_enabled", True)
        if "cache_ttl" in setting:
            cls.CACHE_TTL = int(setting.get("cache_ttl", cls.CACHE_TTL))

        cls.module_bucket_name = setting.get("module_bucket_name")
        cls.module_zip_path = setting.get("module_zip_path") or os.path.join(
            os.getenv("TMP", "/tmp"), "setting_module_zips"
        )
        cls.module_extract_path = setting.get("module_extract_path") or os.path.join(
            os.getenv("TMP", "/tmp"), "setting_modules"
        )
        os.makedirs(cls.module_zip_path, exist_ok=True)
        os.makedirs(cls.module_extract_path, exist_ok=True)

    @classmethod
    def _initialize_tables(cls, logger: logging.Logger) -> None:
        """Initialize database tables for the selected backend."""
        utils._initialize_tables(logger)

    @classmethod
    def _aws_credentials(cls, setting: Dict[str, Any]) -> Dict[str, Any]:
        if all(
            setting.get(k)
            for k in ["region_name", "aws_access_key_id", "aws_secret_access_key"]
        ):
            return {
                "region_name": setting["region_name"],
                "aws_access_key_id": setting["aws_access_key_id"],
                "aws_secret_access_key": setting["aws_secret_access_key"],
            }
        return {}

    @classmethod
    def _initialize_aws_services(cls, setting: Dict[str, Any]) -> None:
        """Initialize AWS services used by DynamoDB deployments."""
        credentials = cls._aws_credentials(setting)
        if cls.module_bucket_name or credentials:
            cls.aws_s3 = boto3.client(
                "s3",
                **credentials,
                config=boto3.session.Config(signature_version="s3v4"),
            )

    @classmethod
    def _initialize_optional_aws_services(cls, setting: Dict[str, Any]) -> None:
        """Initialize optional AWS services that are still usable in PG mode."""
        if cls.module_bucket_name:
            cls._initialize_aws_services(setting)

    @classmethod
    def _initialize_db_session(cls, setting: Dict[str, Any]) -> None:
        """Initialize a SQLAlchemy scoped session for the PostgreSQL backend."""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import scoped_session, sessionmaker
        except ImportError as exc:  # pragma: no cover - DynamoDB-only installs
            raise ImportError(
                "SQLAlchemy is required for PostgreSQL backend. "
                "Install with: pip install setting-core-engine[postgresql]"
            ) from exc

        # Set Base.table_prefix before any models are imported so that
        # declared_attr __tablename__ resolves with the correct prefix.
        cls.PG_TABLE_PREFIX = str(setting.get("pg_table_prefix", "sce_")).strip()
        from ..models.postgresql.base import Base

        Base.table_prefix = cls.PG_TABLE_PREFIX

        connection_string = setting.get("database_url") or os.getenv("DATABASE_URL")
        if not connection_string:
            required = ["db_user", "db_password", "db_host", "db_port", "db_schema"]
            missing = [key for key in required if not setting.get(key)]
            if missing:
                raise ValueError(
                    "PostgreSQL backend requires database_url or settings: "
                    + ", ".join(required)
                )
            password = quote_plus(setting["db_password"])
            connection_string = (
                f"postgresql+psycopg2://{setting['db_user']}:{password}"
                f"@{setting['db_host']}:{setting['db_port']}/{setting['db_schema']}"
            )

        engine = create_engine(
            connection_string,
            pool_recycle=7200,
            pool_size=int(setting.get("db_pool_size", 30)),
            max_overflow=int(setting.get("db_max_overflow", 20)),
            pool_timeout=int(setting.get("db_pool_timeout", 60)),
            pool_pre_ping=True,
            echo=bool(setting.get("db_echo", False)),
        )
        cls.db_session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=engine)
        )

    @classmethod
    def get_cache_entity_config(cls) -> Dict[str, Dict[str, Any]]:
        """Get cache configuration metadata for each entity type."""
        if cls.DB_BACKEND == "postgresql":
            return cls.CACHE_ENTITY_CONFIG_POSTGRESQL
        return cls.CACHE_ENTITY_CONFIG_DYNAMODB

    @classmethod
    def get_cache_name(cls, module_type: str, model_name: str) -> str:
        base_name = cls.CACHE_NAMES.get(
            module_type, f"setting_core_engine.{module_type}"
        )
        return f"{base_name}.{model_name}"

    @classmethod
    def get_cache_ttl(cls) -> int:
        return cls.CACHE_TTL

    @classmethod
    def is_cache_enabled(cls) -> bool:
        return cls.CACHE_ENABLED

    @classmethod
    def get_cache_relationships(cls) -> Dict[str, List[Dict[str, str]]]:
        """Get entity cache dependency relationships."""
        if cls.DB_BACKEND == "postgresql":
            return cls.CACHE_RELATIONSHIPS_POSTGRESQL
        return cls.CACHE_RELATIONSHIPS_DYNAMODB

    @classmethod
    def get_entity_children(cls, entity_type: str) -> List[Dict[str, str]]:
        return cls.get_cache_relationships().get(entity_type, [])