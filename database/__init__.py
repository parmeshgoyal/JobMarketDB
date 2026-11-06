"""
JobMarketDB - Database access, models, and connection management.
"""

from database.connection import (
    close_connection,
    get_connection_config,
    get_database,
    get_mongo_client,
    is_loopback_host,
    mask_mongo_uri,
    validate_local_mongo_client,
    validate_local_mongo_uri,
    verify_connection,
)

__all__ = [
    "get_mongo_client",
    "get_database",
    "verify_connection",
    "close_connection",
    "get_connection_config",
    "mask_mongo_uri",
    "validate_local_mongo_uri",
    "validate_local_mongo_client",
    "is_loopback_host",
]
