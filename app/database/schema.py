import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    ForeignKey,
    Enum,
    DateTime,
    func,
    Boolean
)
from sqlalchemy.orm import relationship
from app.database.connection import Base

# Enum for User Roles
class UserRole(str, enum.Enum):
    COMPANY_ADMIN = "company_admin"
    EMPLOYEE = "employee"

# Company Table
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    company_code = Column(String, nullable=False, unique=True, index=True)
    company_secret = Column(String, nullable=False)
    encrypted_db_connection_string = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    users = relationship("User", back_populates="company")
    divisions = relationship("Division", back_populates="company")

# Division Table
class Division(Base):
    __tablename__ = "divisions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    company = relationship("Company", back_populates="divisions")
    users = relationship("User", back_populates="division")
    permissions = relationship("DivisionPermission", back_populates="division", cascade="all, delete-orphan")

# User Table (replaces old User model)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    division_id = Column(Integer, ForeignKey("divisions.id"), nullable=True)

    company = relationship("Company", back_populates="users")
    division = relationship("Division", back_populates="users")

# Table for managing division-level permissions on external databases
class DivisionPermission(Base):
    __tablename__ = "division_permissions"

    id = Column(Integer, primary_key=True, index=True)
    division_id = Column(Integer, ForeignKey("divisions.id"), nullable=False)
    table_name = Column(String, nullable=False)
    
    # Comma-separated list of column names, or "*" for all columns
    allowed_columns = Column(String, nullable=False)

    division = relationship("Division", back_populates="permissions")