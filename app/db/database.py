import os

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base


# ----------------------------------------
# LOAD .ENV
# ----------------------------------------

load_dotenv()

# ----------------------------------------
# DATABASE URL
# ----------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./aura.db"
)

print("\n==============================")
print("DATABASE_URL =", DATABASE_URL)
print("==============================\n")

# ----------------------------------------
# ENGINE
# ----------------------------------------

engine = create_engine(
    DATABASE_URL
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

metadata = Base.metadata