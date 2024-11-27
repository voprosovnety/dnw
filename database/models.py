from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database.db import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)

    progress = relationship('Progress', back_populates='user')


class Assignment(Base):
    __tablename__ = 'assignments'

    id = Column(Integer, primary_key=True)
    topic = Column(String)
    description = Column(String)
    tests_code = Column(String)

    progress = relationship('Progress', back_populates='assignment')


class Progress(Base):
    __tablename__ = 'progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    assignment_id = Column(Integer, ForeignKey('assignments.id'))
    is_completed = Column(Boolean, default=False)

    user = relationship('User', back_populates='progress')
    assignment = relationship('Assignment', back_populates='progress')
