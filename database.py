from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, mapper

Base = declarative_base()

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    reminder_text = Column(String, nullable=False)
    remind_at = Column(DateTime, nullable=False)
    messageid = Column(Integer, nullable=False)

engine = create_engine('sqlite:///ext-mount/persist.db')
Base.metadata.create_all(engine)
db_session = sessionmaker(bind=engine)


sesh = db_session()
def get_session(): 
    return sesh
