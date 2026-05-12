from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB


# Store UUIDs as plain strings for cross-database compatibility in local dev.
UUIDType = String(36)


def json_type():
    return JSON().with_variant(JSONB, "postgresql")
