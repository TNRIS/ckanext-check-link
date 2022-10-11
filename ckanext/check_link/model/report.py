from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

import ckan.model as model
from ckan.lib.dictization import table_dictize
from ckan.lib.dictization.model_dictize import package_dictize, resource_dictize
from ckan.model.types import make_uuid
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import backref, relationship
from typing_extensions import Self

from .base import Base


class Report(Base):
    __tablename__ = "check_link_report"

    id = Column(UnicodeText, primary_key=True, default=make_uuid)
    url = Column(UnicodeText, nullable=False)
    state = Column(String(20), nullable=False)

    last_checked = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_status_change = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_available = Column(DateTime, nullable=False, default=datetime.utcnow)

    resource_id = Column(
        UnicodeText, ForeignKey(model.Resource.id), nullable=True, unique=True
    )

    details = Column(JSONB, nullable=False, default=dict)

    package_id = association_proxy("resource", "package_id")
    package = association_proxy("resource", "package")

    resource = relationship(
        model.Resource,
        backref=backref(
            "check_link_report", cascade="all, delete-orphan", uselist=False
        ),
    )

    UniqueConstraint(url, resource_id)

    def touch(self):
        self.last_checked = datetime.utcnow()

    def dictize(self, context: dict[str, Any]) -> dict[str, Any]:
        result = table_dictize(self, context, package_id=self.package_id)

        if context.get("include_resource") and self.resource_id:
            result["details"]["resource"] = resource_dictize(self.resource, context)

        if context.get("include_package") and self.package_id:
            result["details"]["package"] = resource_dictize(self.package, context)

        return result

    @classmethod
    def by_resource_id(cls, id_: str) -> Optional[Self]:
        if not id_:
            return

        return model.Session.query(cls).filter(cls.resource_id == id_).one_or_none()

    @classmethod
    def by_url(cls, url: str) -> Optional[Self]:
        return (
            model.Session.query(cls)
            .filter(cls.resource_id.is_(None), cls.url == url)
            .one_or_none()
        )
