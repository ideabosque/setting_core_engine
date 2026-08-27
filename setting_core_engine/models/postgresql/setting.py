# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for Setting."""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import Column, Index, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class SettingModel(Base):
    """SQLAlchemy model for the Setting entity (table: sce_settings)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("settings")

    partition_key = Column(String(128), nullable=False, primary_key=True)
    setting_uuid = Column(String, nullable=False, primary_key=True)
    setting_type = Column(String, nullable=False)
    setting = Column(JSONB, nullable=True)
    updated_by = Column(String(64), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        Index(
            prefixed_index("ix_settings_partition_setting_type"),
            "partition_key",
            "setting_type",
        ),
    )


__all__ = ["SettingModel"]