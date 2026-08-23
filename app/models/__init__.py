"""
Single import point for all models. Importing this module (rather than each
submodule separately) guarantees every model is registered on Base.metadata
before Alembic autogenerate or `Base.metadata.create_all` runs — a model
that's never imported never gets its table created, which is a classic
"works until you add the next table" bug.
"""
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.widget import Widget, WidgetStatus, WidgetType

__all__ = ["Tenant", "User", "UserRole", "Widget", "WidgetStatus", "WidgetType"]
