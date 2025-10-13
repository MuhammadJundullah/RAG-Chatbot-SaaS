from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    DateTime,
    func
)
from sqlalchemy.orm import relationship
from app.database.connection import Base

# 1) Master: Company
class Company(Base):
    __tablename__ = "Company"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    code = Column(String(10))
    logo = Column(String(255))

    users = relationship("Users", back_populates="company")
    documents = relationship("Documents", back_populates="company")
    chatlogs = relationship("Chatlogs", back_populates="company")
    divisions = relationship("Division", back_populates="company")


# 2) Users (anggota perusahaan & memiliki role)
class Users(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    email = Column(String(255))
    password = Column(String(255))
    status = Column(String(100))
    role = Column(String(50), nullable=False)  # 'admin' or 'employee'
    Companyid = Column(Integer, ForeignKey("Company.id"), nullable=False)
    Divisionid = Column(Integer, ForeignKey("Division.id"), nullable=True)

    company = relationship("Company", back_populates="users")
    division = relationship("Division", back_populates="users")
    chatlogs = relationship("Chatlogs", back_populates="user")


# 3) Documents (dokumen milik perusahaan)
class Documents(Base):
    __tablename__ = "Documents"
    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    isi_dokumen = Column(String(255))
    Companyid = Column(Integer, ForeignKey("Company.id"), nullable=False)

    company = relationship("Company", back_populates="documents")
    embeddings = relationship("Embeddings", back_populates="document")


# 4) Chatlogs (riwayat tanya-jawab; milik user & company)
class Chatlogs(Base):
    __tablename__ = "Chatlogs"
    id = Column(Integer, primary_key=True)
    question = Column(String(255))
    answer = Column(String(255))
    UsersId = Column(Integer, ForeignKey("Users.id"), nullable=False)
    Companyid = Column(Integer, ForeignKey("Company.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("Users", back_populates="chatlogs")
    company = relationship("Company", back_populates="chatlogs")


# 5) Embeddings (vektor untuk dokumen)
class Embeddings(Base):
    __tablename__ = "Embeddings"
    id = Column(Integer, primary_key=True)
    vector_id = Column(String)
    DocumentsId = Column(Integer, ForeignKey("Documents.id"), nullable=False)

    document = relationship("Documents", back_populates="embeddings")

# 6) Division (divisi perusahaan)
class Division(Base):
    __tablename__ = "Division"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    Companyid = Column(Integer, ForeignKey("Company.id"), nullable=False)

    company = relationship("Company", back_populates="divisions")
    users = relationship("Users", back_populates="division")
