import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.db.models import Base
# Import models to ensure they are registered with Base

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh in-memory SQLite database session for a test.
    Attaches 'public' and 'auth' databases to simulate Postgres schema.
    """
    # Use in-memory SQLite
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # Attach 'public' and 'auth' database schemas for SQLite compatibility
    with engine.connect() as conn:
        conn.execute(text("ATTACH DATABASE ':memory:' AS public"))
        conn.execute(text("ATTACH DATABASE ':memory:' AS auth"))
        conn.commit()  # Important for ATTACH to take effect

    # Create all tables
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
