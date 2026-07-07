# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for ThemeSetting."""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import Column, Index, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class ThemeSettingModel(Base):
    """SQLAlchemy model for the ThemeSetting entity (table: sce_theme_settings)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("theme_settings")

    partition_key = Column(String(128), nullable=False, primary_key=True)
    theme_uuid = Column(String, nullable=False, primary_key=True)
    theme_type = Column(String, nullable=False)
    theme_title = Column(String, nullable=True)
    theme_description = Column(String, nullable=True)
    setting = Column(JSONB, nullable=True)
    updated_by = Column(String(64), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        Index(
            prefixed_index("ix_theme_settings_partition_theme_type"),
            "partition_key",
            "theme_type",
        ),
    )


__all__ = ["ThemeSettingModel"]