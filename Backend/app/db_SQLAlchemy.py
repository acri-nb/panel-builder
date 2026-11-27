import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]

#conncetion to postgresql
engine = create_engine(DATABASE_URL)

print("SQLAlchemy engine created successfully")

#foundation for models
Base = declarative_base()

#creates database sessions
SessionLocal = sessionmaker(bind=engine)


from sqlalchemy import text
db = SessionLocal()
try:
        database_name = db.execute(
            text("SELECT current_database();")
        ).scalar()

        print("Connected database:", database_name)

finally:
        db.close()