# app/models/topup_package_model.py
from sqlalchemy import Column, Integer, String, Boolean, Index

from .base import Base


class TopUpPackage(Base):
    __tablename__ = "topup_packages"
    __table_args__ = (
        Index("ix_topup_packages_type", "package_type"),
        Index("ix_topup_packages_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    package_type = Column(String, unique=True, nullable=False)  # e.g., small, large
    questions = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
