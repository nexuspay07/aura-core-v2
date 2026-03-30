# app/db/database.py

import os
from sqlalchemy import create_engine, MetaData
from databases import Database
from dotenv import load_dotenv

# Load environment variables from .env (for local dev)
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables!")

# SQLAlchemy engine & metadata
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
metadata = MetaData()

# Async database connection
database = Database(DATABASE_URL)