import tempfile
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _connect_args() -> dict:
    ca_pem = get_settings().database_ssl_ca.strip()
    if not ca_pem:
        return {}
    # PyMySQL espera um caminho de arquivo; o certificado chega por variável de ambiente.
    ca_file = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)  # noqa: SIM115
    ca_file.write(ca_pem.replace("\\n", "\n") + "\n")
    ca_file.close()
    return {"ssl": {"ca": ca_file.name}}


engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_recycle=280,  # bancos gratuitos derrubam conexões ociosas
    connect_args=_connect_args(),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
