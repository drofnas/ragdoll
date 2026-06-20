from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from ragdoll.platform.db.engine import get_engine


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
