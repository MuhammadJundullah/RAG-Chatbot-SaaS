from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base
# Import related models to define relationships

class ActivityLog(Base):
    __tablename__ = "Activity_logs"
    __table_args__ = (
        Index("ix_activity_logs_company_type", "company_id", "activity_type_category"),
        Index("ix_activity_logs_company_timestamp", "company_id", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    
    # Foreign key to the users table
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=True) 
    
    activity_type_category = Column(String, nullable=False)
    
    # Foreign key to the companies table
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=True) 
    
    activity_description = Column(Text, nullable=False)

    # Define relationships
    user = relationship("Users", back_populates="activity_logs")
    company = relationship("Company", back_populates="activity_logs")
