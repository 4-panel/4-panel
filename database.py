from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./vpn.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    uuid = Column(String)
    expires = Column(String)
    traffic_limit = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)


Base.metadata.create_all(bind=engine)