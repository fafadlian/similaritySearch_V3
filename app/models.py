# models.py
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True, index=True)
    folder_path = Column(String)
    status = Column(String)
    flight_ids = Column(Text)  # Store flight IDs as a text field
    flight_count = Column(Integer)  # Store flight count
    created_at = Column(DateTime, default=datetime.utcnow)


    def __init__(self, id, folder_path, status):
        self.id = id
        self.folder_path = folder_path
        self.status = status
        self.flight_ids = ""
        self.flight_count = 0
        self.created_at = datetime.utcnow()
