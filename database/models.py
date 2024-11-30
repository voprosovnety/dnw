from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database.db import Base

class User(Base):
    __tablename__ = 'users'

    telegram_id = Column(Integer, primary_key=True)

    progress = relationship('Progress', back_populates='user')

class Progress(Base):
    __tablename__ = 'progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    topic = Column(String)
    assignment_name = Column(String)
    is_completed = Column(Boolean, default=False)

    user = relationship('User', back_populates='progress')
