"""Alembic environment. Uses the app's metadata and Settings (never os.getenv)."""

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import create_engine, pool

from app.models import Base
from app.models.base import StrEnumType

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    url = config.attributes.get("url")
    if url:
        return str(url)
    from app.core.settings import get_settings

    return get_settings().database_url


def _render_item(type_: str, obj: Any, autogen_context: Any) -> str | bool:
    # StrEnumType is an app-level decorator; migrations store plain strings.
    if type_ == "type" and isinstance(obj, StrEnumType):
        return f"sa.String(length={obj.impl_instance.length})"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_item=_render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=_render_item,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
