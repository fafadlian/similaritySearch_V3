# from sqlalchemy import create_engine, MetaData
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from app.config import DATABASE_URL

# # Database setup
# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()
# metadata = MetaData()

# from app.models import Base
# Base.metadata.create_all(bind=engine)

# # To use database session in other files
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# if __name__ == "__main__":
#     Base.metadata.create_all(bind=engine)

import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from databases import Database
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('environment.env')

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"DATABASE_URL: {DATABASE_URL}")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = MetaData()

from app.models import Base
Base.metadata.create_all(bind=engine)

# To use database session in other files
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



