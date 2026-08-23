"""
Regression coverage for a real bug: SQLAlchemy's Enum type defaults to
persisting a Python enum member's NAME ("OWNER"), not its VALUE ("owner").
Our Postgres migration created the native enum types with lowercase VALUES,
so without `values_callable` on every enum column, every insert against real
Postgres fails with "invalid input value for enum ... : OWNER" — while SQLite
(what the rest of the test suite runs against) never catches it, because its
generic enum fallback validates names on both sides and "agrees with itself."

These tests compile against the actual postgresql dialect, so they catch the
mismatch without needing a live Postgres connection.
"""
from sqlalchemy.dialects import postgresql

from app.models.user import User, UserRole
from app.models.widget import Widget, WidgetStatus, WidgetType

_pg_dialect = postgresql.dialect()


def _bound_value(column_type, value):
    processor = column_type.bind_processor(_pg_dialect)
    return processor(value) if processor is not None else value


def test_user_role_enum_binds_lowercase_value_for_postgres():
    column_type = User.__table__.c.role.type
    assert _bound_value(column_type, UserRole.OWNER) == "owner"
    assert _bound_value(column_type, UserRole.MEMBER) == "member"


def test_widget_type_enum_binds_lowercase_value_for_postgres():
    column_type = Widget.__table__.c.type.type
    assert _bound_value(column_type, WidgetType.SIGNUP_FORM) == "signup_form"
    assert _bound_value(column_type, WidgetType.CTA) == "cta"
    assert _bound_value(column_type, WidgetType.POPOVER) == "popover"


def test_widget_status_enum_binds_lowercase_value_for_postgres():
    column_type = Widget.__table__.c.status.type
    assert _bound_value(column_type, WidgetStatus.ACTIVE) == "active"
    assert _bound_value(column_type, WidgetStatus.PAUSED) == "paused"
