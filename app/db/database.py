import os

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# ==========================================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()

# ==========================================================
# DATABASE URL
# ==========================================================

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aura.db")

# ==========================================================
# ENGINE
# ==========================================================

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=not DATABASE_URL.startswith("sqlite"),
)

# ==========================================================
# SESSION FACTORY
# ==========================================================

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ==========================================================
# BASE / METADATA
# ==========================================================

Base = declarative_base()

metadata = Base.metadata
