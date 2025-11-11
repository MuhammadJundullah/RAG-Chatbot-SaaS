from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base
# Import related models to define relationships
from app.models.user_model import Users
from app.models.company_model import Company

class ActivityLog(Base):
    __tablename__ = "Activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Foreign key to the users table
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=True) 
    
    activity_type_category = Column(String, nullable=False)
    
    # Foreign key to the companies table
    company_id = Column(Integer, ForeignKey("Company.id"), nullable=True) 
    
    activity_description = Column(Text, nullable=False)

    # Define relationships
    user = relationship("Users", back_populates="activity_logs")
    company = relationship("Company", back_populates="activity_logs")
