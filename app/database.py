from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from app.models import Base
from dotenv import load_dotenv


load_dotenv()

engine = create_engine(os.environ.get("DATABASE_URL"), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()