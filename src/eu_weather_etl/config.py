"""Runtime configuration, sourced entirely from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load a local .env file if present. Real environment variables always win,
# because load_dotenv does not override values that are already set.
load_dotenv()

# The portal (SEAD CDS) injects the credentials of an attached shared Connection
# as {PREFIX}_HOST / _PORT / _DB / _USER / _PASSWORD / _URI, where PREFIX is
# chosen per attachment so one ETL can talk to several databases. CDS_DB_PREFIX
# names the attachment this ETL should use for its own target.
DEFAULT_DB_ENV_PREFIX = "DB"


def _prefix() -> str:
    return (os.environ.get("CDS_DB_PREFIX") or DEFAULT_DB_ENV_PREFIX).strip()


def _connection_kwargs_from_prefix(prefix: str) -> dict[str, object] | None:
    """Read a CDS shared Connection from the environment, or None if absent."""
    uri = os.environ.get(f"{prefix}_URI", "").strip()
    if uri:
        return {"conninfo": uri}

    host = os.environ.get(f"{prefix}_HOST", "").strip()
    dbname = os.environ.get(f"{prefix}_DB", "").strip()
    user = os.environ.get(f"{prefix}_USER", "").strip()
    if not (host and dbname and user):
        return None

    kwargs: dict[str, object] = {"host": host, "dbname": dbname, "user": user}
    if os.environ.get(f"{prefix}_PORT"):
        kwargs["port"] = int(os.environ[f"{prefix}_PORT"])
    if os.environ.get(f"{prefix}_PASSWORD"):
        kwargs["password"] = os.environ[f"{prefix}_PASSWORD"]
    return kwargs


def _legacy_connection_kwargs() -> dict[str, object] | None:
    """Pre-Connections configuration: DATABASE_URL, or the standard PG* vars."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return {"conninfo": url}

    if not all(os.environ.get(name) for name in ("PGHOST", "PGDATABASE", "PGUSER")):
        return None

    kwargs: dict[str, object] = {
        "host": os.environ["PGHOST"],
        "dbname": os.environ["PGDATABASE"],
        "user": os.environ["PGUSER"],
    }
    if os.environ.get("PGPORT"):
        kwargs["port"] = int(os.environ["PGPORT"])
    if os.environ.get("PGPASSWORD"):
        kwargs["password"] = os.environ["PGPASSWORD"]
    if os.environ.get("PGSSLMODE"):
        kwargs["sslmode"] = os.environ["PGSSLMODE"]
    return kwargs


def database_connection_kwargs() -> dict[str, object]:
    """Build the keyword arguments for psycopg.connect from the environment.

    An attached CDS Connection wins; DATABASE_URL / PG* are the fallback for
    local runs and for deployments that predate shared Connections.
    """
    prefix = _prefix()
    kwargs = _connection_kwargs_from_prefix(prefix) or _legacy_connection_kwargs()
    if kwargs is None:
        raise RuntimeError(
            "Missing database configuration. Attach a CDS Connection and set "
            f"CDS_DB_PREFIX (currently {prefix!r}, expecting {prefix}_URI or "
            f"{prefix}_HOST + {prefix}_DB + {prefix}_USER), or set DATABASE_URL "
            "/ PGHOST, PGDATABASE, PGUSER. See .env.example for the full list."
        )
    return kwargs
