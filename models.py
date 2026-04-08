from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class Player(Base):
    __tablename__ = "players"
    id         = Column(Integer, primary_key=True)
    username   = Column(String, unique=True, index=True)
    pet_name   = Column(String, default="Byte")
    xp         = Column(Integer, default=0)
    sessions   = Column(Integer, default=0)
    streak     = Column(Integer, default=0)
    total_mins = Column(Integer, default=0)
    last_date  = Column(String, default="")
    pet_emoji  = Column(String, default="🥚")

class CodingSession(Base):
    __tablename__ = "sessions"
    id        = Column(Integer, primary_key=True)
    player_id = Column(Integer)
    duration  = Column(Integer)
    language  = Column(String)
    mood      = Column(String)
    xp_gained = Column(Integer)
    logged_at = Column(DateTime, server_default=func.now())