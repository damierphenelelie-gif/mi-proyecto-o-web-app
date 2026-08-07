import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# En Render, la DATABASE_URL te la da el servicio de PostgreSQL automáticamente.
# Para probar en tu compu, podés usar SQLite descomentando la segunda línea.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./phenex.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: abre y cierra la sesión de base de datos por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
