from sqlalchemy import UniqueConstraint, create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, mapper
from enum import Enum

Base = declarative_base()

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    reminder_text = Column(String, nullable=False)
    remind_at = Column(DateTime, nullable=False)
    messageid = Column(Integer, nullable=False)

class MessageData(Base):
    __tablename__ = 'message_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    sent_at = Column(DateTime, nullable=False)
    message_text = Column(String, nullable=False)
    full_payload = Column(String, nullable=False)
    __table_args__ = (
        # Composite unique constraint
        UniqueConstraint('chat_id', 'message_id', name='uix_chat_message'),
    )

class SmbUserStatus(Enum):
    ONLINE = 1
    OFFLINE = 2
    TYPING = 3
    SENDING_MEDIA = 4

class UserActivity(Base):
    __tablename__ = 'user_activity'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    activity_type = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)

engine = create_engine('sqlite:///ext-mount/persist.db')
Base.metadata.create_all(engine)
db_session = sessionmaker(bind=engine)


sesh = db_session()
def get_session(): 
    return sesh

def create_new_session():
    return db_session()