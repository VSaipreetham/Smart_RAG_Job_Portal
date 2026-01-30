from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Date, Enum as SqlEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import enum

Base = declarative_base()

class JobStatus(enum.Enum):
    NEW = "new"
    QUEUED = "queued"
    NOTIFIED = "notified" # Deprecated concept, now maps to "Inbox"
    APPLIED = "applied"   # CRM Status
    INTERVIEW = "interview" # CRM Status
    OFFER = "offer"       # CRM Status
    REJECTED = "rejected" # CRM Status
    ARCHIVED = "archived"

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    company = Column(String)
    url = Column(String, unique=True)
    source = Column(String)
    location = Column(String, nullable=True) # Added Location
    pay = Column(String, nullable=True)     # Added Pay
    notes = Column(String, nullable=True) # New: User notes
    posted_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(SqlEnum(JobStatus), default=JobStatus.NEW)
    match_score = Column(Integer, default=0)

class DailyLog(Base):
    __tablename__ = 'daily_logs'
    
    date = Column(Date, primary_key=True)
    count = Column(Integer, default=0)

# Database Setup
engine = create_engine('sqlite:///jobs_v4.db') # upgraded to v4
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
