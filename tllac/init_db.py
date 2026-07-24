from __future__ import annotations

import sys
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import quote

from dotenv import load_dotenv
import psycopg
from psycopg import OperationalError
from psycopg import sql


REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(REPO_ROOT / ".env")


def _looks_placeholder_database_url(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return not normalized or "user:password@host" in normalized or normalized.endswith("@host:5432/legalaichat")


def _admin_url() -> str:
    explicit = os.getenv("POSTGRES_ADMIN_URL", "").strip()
    if explicit and not _looks_placeholder_database_url(explicit):
        return explicit

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url or _looks_placeholder_database_url(database_url):
        raise RuntimeError("DATABASE_URL or POSTGRES_ADMIN_URL is missing from tllac/.env.")

    parsed = urlparse(database_url)
    return parsed._replace(path="/postgres").geturl()


def _app_db_settings() -> tuple[str, str, str]:
    database_name = os.getenv("POSTGRES_DB", "").strip() or "legalaichat"
    app_user = os.getenv("POSTGRES_APP_USER", "").strip() or "legalaichat_app"
    app_password = os.getenv("POSTGRES_APP_PASSWORD", "").strip()
    if not app_password:
        raise RuntimeError("POSTGRES_APP_PASSWORD is missing from tllac/.env.")
    return database_name, app_user, app_password


def _ensure_role_exists() -> tuple[str, str]:
    app_user, app_password = _app_db_settings()[1], _app_db_settings()[2]
    with psycopg.connect(_admin_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(app_user),
                        sql.Literal(app_password),
                    )
                )
                print(f"Created Postgres role: {app_user}")
            else:
                cur.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(app_user),
                        sql.Literal(app_password),
                    )
                )
                print(f"Updated password for Postgres role: {app_user}")
    return app_user, app_password


def _ensure_database_exists() -> tuple[str, str, str]:
    database_name, app_user, app_password = _app_db_settings()
    with psycopg.connect(_admin_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(database_name),
                        sql.Identifier(app_user),
                    )
                )
                print(f"Created database: {database_name}")
            else:
                cur.execute(
                    sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                        sql.Identifier(database_name),
                        sql.Identifier(app_user),
                    )
                )

    return database_name, app_user, app_password


def _build_database_url(database_name: str, app_user: str, app_password: str) -> str:
    host = os.getenv("POSTGRES_HOST", "").strip() or "localhost"
    port = os.getenv("POSTGRES_PORT", "").strip() or "5432"
    return (
        f"postgresql://{quote(app_user)}:{quote(app_password)}"
        f"@{host}:{port}/{quote(database_name)}"
    )


def _app_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url and not _looks_placeholder_database_url(database_url):
        return database_url

    database_name, app_user, app_password = _app_db_settings()
    return _build_database_url(database_name, app_user, app_password)


def _can_connect(connection_url: str) -> bool:
    try:
        with psycopg.connect(connection_url, connect_timeout=5):
            return True
    except OperationalError:
        return False


def _admin_auth_hint(exc: Exception) -> RuntimeError:
    admin_url = _admin_url()
    return RuntimeError(
        "Could not connect with POSTGRES_ADMIN_URL. "
        "Update the admin username/password in tllac/.env to match your local Postgres superuser, "
        f"or pre-create the app database/user and make DATABASE_URL work directly. Current admin target: {admin_url}. "
        f"Original error: {exc}"
    )


def main() -> int:
    try:
        direct_database_url = _app_database_url()
        if _can_connect(direct_database_url):
            os.environ["DATABASE_URL"] = direct_database_url
            print("Connected with the application database user.")
        else:
            try:
                app_user, app_password = _ensure_role_exists()
                database_name, _, _ = _ensure_database_exists()
                os.environ["DATABASE_URL"] = _build_database_url(
                    database_name,
                    app_user,
                    app_password,
                )
            except (OperationalError, RuntimeError) as exc:
                print(
                    "Skipping Postgres bootstrap because the local admin connection is not available. "
                    "The app will use local fallback storage for this session.",
                    file=sys.stderr,
                )
                return 0

        from app.db.db_client import db_client

        print("Connected to Postgres and verified schema initialization.")
        print("Database bootstrap complete.")
        return 0
    except Exception as exc:
        print(f"Database initialization failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
