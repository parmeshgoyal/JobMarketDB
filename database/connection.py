"""
JobMarketDB - MongoDB Connection Layer

Provides clean, secure, and strictly local MongoDB connectivity using PyMongo
and python-dotenv. Adheres to strict local-only deployment security rules:
- Strictly accepts local MongoDB Community Server (localhost:27017 or 127.0.0.1:27017).
- Rejects Atlas (mongodb+srv://), remote hosts, remote IP addresses, and non-local deployments.
- Strictly enforces the required database 'jobmarketdb'.
- Enforces directConnection=True to prevent replica-set discovery of remote peers.
- Validates configuration on EVERY call to get_mongo_client() before returning any cached client.
- Protects credentials from log and exception exposure across all code paths.
"""

import ipaddress
import os
import re
from typing import Any, Optional, Set, Tuple
from urllib.parse import urlsplit

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    ServerSelectionTimeoutError,
)
from pymongo.uri_parser import parse_uri

# Load environment variables
load_dotenv()

DEFAULT_DATABASE_NAME = "jobmarketdb"
DEFAULT_TIMEOUT_MS = 5000

# Loopback host identifiers permitted for local MongoDB Community Server
ALLOWED_LOOPBACK_HOSTS: Set[str] = {"localhost", "127.0.0.1", "::1", "[::1]"}
ALLOWED_PORTS: Set[int] = {27017}

_client_instance: Optional[MongoClient] = None
_cached_client_uri: Optional[str] = None


def mask_mongo_uri(text: str) -> str:
    """
    Masks credentials in a MongoDB URI or exception string to prevent exposure in logs or error messages.
    Example: mongodb://user:secret@localhost:27017/ -> mongodb://user:***@localhost:27017/
    """
    if not text:
        return "<EMPTY>"
    s = str(text)

    # 1. Match scheme:// + userinfo (all chars up to last @ before host) + @ + host/ip
    pattern = r"([a-zA-Z0-9+.-]+://)([^\s/]+)@((?:\[[0-9a-fA-F:]+\]|[^:/\s?#]+)(?::\d+)?(?:[/\\?][^\s]*)?)"

    def repl(m):
        scheme = m.group(1)
        full_userinfo = m.group(2)
        tail = m.group(3)
        if ":" in full_userinfo:
            user = full_userinfo.split(":", 1)[0]
            return f"{scheme}{user}:***@{tail}"
        return f"{scheme}***@{tail}"

    s = re.sub(pattern, repl, s)
    # 2. Secondary check for standalone user:password@, strictly excluding slashes
    s = re.sub(r":([^/@\s]+)@", r":***@", s)
    return s


def is_loopback_host(host: str) -> bool:
    """
    Validates whether a hostname or IP string represents a local loopback address.
    Accepts 'localhost', '127.0.0.1', IPv6 loopback '::1' / '[::1]', and any 127.0.0.0/8 loopback.
    Rejects remote hostnames, Atlas domains, and non-loopback IP addresses.
    """
    cleaned = host.strip("[]").lower()
    if cleaned in ALLOWED_LOOPBACK_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(cleaned)
        return ip.is_loopback
    except ValueError:
        return False


def validate_local_mongo_uri(uri: str) -> None:
    """
    Validates that a MongoDB URI conforms strictly to local MongoDB Community Server requirements.

    Accepts:
    - mongodb://localhost:27017/
    - mongodb://127.0.0.1:27017/
    - Equivalent localhost URI formatting with valid local connection options and standard port 27017.

    Rejects:
    - mongodb+srv:// URIs (Atlas SRV protocol).
    - Remote MongoDB hostnames (e.g. *.mongodb.net, remote DNS hostnames).
    - Remote IP addresses (LAN, WAN, cloud IPs).
    - Non-standard/non-local ports.
    - Database path other than 'jobmarketdb' if specified.
    - replicaSet options (to prevent replica-set peer discovery).
    - directConnection=false (which would allow replica-set discovery).

    Uses pure syntactic and PyMongo URI parsing without triggering remote DNS or network operations.
    """
    if not uri:
        raise ValueError(
            "MongoDB configuration error: 'MONGODB_URI' is missing or empty.\n"
            "JobMarketDB strictly requires a local MongoDB Community Server.\n"
            "Please configure MONGODB_URI in your .env file.\n"
            "Example: MONGODB_URI=mongodb://localhost:27017/\n"
            "     or: MONGODB_URI=mongodb://127.0.0.1:27017/"
        )

    masked_uri = mask_mongo_uri(uri)

    # 1. Syntactic scheme check via urllib.parse (pure in-memory, zero DNS lookups)
    try:
        split_res = urlsplit(uri)
    except Exception as err:
        clean_err = mask_mongo_uri(str(err))
        raise ValueError(
            f"MongoDB configuration error: Failed to parse URI syntax ({masked_uri}): {clean_err}"
        ) from None

    scheme = split_res.scheme.lower()
    if scheme == "mongodb+srv":
        raise ValueError(
            f"MongoDB configuration error: 'mongodb+srv://' protocol is prohibited ({masked_uri}).\n"
            "JobMarketDB strictly supports local MongoDB Community Server only.\n"
            "MongoDB Atlas and remote cloud clusters are not permitted.\n"
            "Please configure MONGODB_URI=mongodb://localhost:27017/ in your .env file."
        )
    if scheme != "mongodb":
        raise ValueError(
            f"MongoDB configuration error: URI scheme '{scheme}' is invalid ({masked_uri}).\n"
            "JobMarketDB strictly requires 'mongodb://localhost:27017/'."
        )

    # 2. Parse URI nodes and options using PyMongo uri_parser (safe for mongodb:// without DNS SRV lookups)
    try:
        parsed = parse_uri(uri)
    except ConfigurationError as err:
        clean_err = mask_mongo_uri(str(err))
        raise ValueError(
            f"MongoDB configuration error: Invalid MongoDB URI syntax ({masked_uri}): {clean_err}"
        ) from None
    except Exception as err:
        clean_err = mask_mongo_uri(str(err))
        raise ValueError(
            f"MongoDB configuration error: Could not parse MongoDB URI ({masked_uri}): {clean_err}"
        ) from None

    nodelist = parsed.get("nodelist", [])
    if not nodelist:
        raise ValueError(
            f"MongoDB configuration error: No host specified in URI ({masked_uri}).\n"
            "JobMarketDB requires 'mongodb://localhost:27017/'."
        )

    for host, port in nodelist:
        if not is_loopback_host(host):
            # Distinguish remote IP vs remote hostname for precise diagnostics
            try:
                ipaddress.ip_address(host.strip("[]"))
                is_ip = True
            except ValueError:
                is_ip = False

            entity_type = "Remote IP address" if is_ip else "Remote MongoDB host"
            raise ValueError(
                f"MongoDB configuration error: {entity_type} '{host}' is prohibited ({masked_uri}).\n"
                "JobMarketDB strictly supports local MongoDB Community Server only.\n"
                "Atlas, remote clusters, and non-local deployments are not permitted.\n"
                "Please configure MONGODB_URI=mongodb://localhost:27017/ in your .env file."
            )

        effective_port = port if port is not None else 27017
        if effective_port not in ALLOWED_PORTS:
            raise ValueError(
                f"MongoDB configuration error: Port {effective_port} on host '{host}' is not allowed ({masked_uri}).\n"
                "JobMarketDB requires the standard local MongoDB Community Server port 27017.\n"
                "Example: MONGODB_URI=mongodb://localhost:27017/"
            )

    # 3. Prevent replica-set configuration and require direct connection
    options = parsed.get("options", {})
    clean_options = {str(k).lower(): v for k, v in options.items()}
    if "replicaset" in clean_options or "replicaset=" in uri.lower():
        rs_name = clean_options.get("replicaset", "configured")
        raise ValueError(
            f"MongoDB configuration error: 'replicaSet={rs_name}' is prohibited ({masked_uri}).\n"
            "JobMarketDB requires a local standalone MongoDB Community Server.\n"
            "Replica-set configurations and peer discovery are not permitted."
        )

    if clean_options.get("directconnection") is False or "directconnection=false" in uri.lower():
        raise ValueError(
            f"MongoDB configuration error: 'directConnection=false' is prohibited ({masked_uri}).\n"
            "JobMarketDB strictly requires direct connection to the local standalone server."
        )

    # 4. Enforce database name in URI path if present
    uri_db = parsed.get("database")
    if uri_db is not None and uri_db != DEFAULT_DATABASE_NAME:
        raise ValueError(
            f"MongoDB configuration error: URI specifies database '{uri_db}' ({masked_uri}).\n"
            f"JobMarketDB strictly requires the '{DEFAULT_DATABASE_NAME}' database."
        )


def validate_local_mongo_client(client: Any) -> None:
    """
    Validates that an externally supplied MongoClient or client-like instance is demonstrably
    restricted to the approved local standalone MongoDB Community Server endpoint
    (localhost:27017 or loopback IP:27017) with directConnection=True and no replica sets.

    Raises ValueError if the client targets a remote host, remote IP, unauthorized port,
    or replica set. Never initiates network operations or server selection during validation.
    """
    if client is None:
        return

    # 1. Enforce directConnection=True (reject replica-set peer discovery)
    options = getattr(client, "options", None)
    direct_conn = getattr(options, "direct_connection", None)
    if direct_conn is not True:
        raise ValueError(
            "MongoDB configuration error: Supplied client must have directConnection=True "
            "to enforce standalone local connection."
        )

    replica_set = getattr(options, "replica_set_name", None)
    if replica_set is not None:
        raise ValueError(
            f"MongoDB configuration error: Supplied client has 'replicaSet={replica_set}'. "
            "Replica sets and remote member discovery are prohibited."
        )

    # 2. Extract server endpoints without initiating network operations or server selection
    endpoints: Set[Tuple[str, Optional[int]]] = set()

    td = getattr(client, "topology_description", None)
    if td is not None:
        sd = getattr(td, "server_descriptions", None)
        if callable(sd):
            try:
                res = sd()
                if isinstance(res, dict):
                    endpoints.update(res.keys())
            except Exception:
                pass
        elif isinstance(sd, dict):
            endpoints.update(sd.keys())

    ts = getattr(client, "_topology_settings", None)
    if ts is not None and hasattr(ts, "seeds"):
        seeds = getattr(ts, "seeds", None)
        if seeds and isinstance(seeds, (set, frozenset, list, tuple)):
            endpoints.update(seeds)

    nodes = getattr(client, "nodes", None)
    if nodes and isinstance(nodes, (set, frozenset, list, tuple)):
        endpoints.update(nodes)

    if not endpoints:
        raise ValueError(
            "MongoDB configuration error: Supplied client has no identifiable server endpoints. "
            "Cannot verify local Community Server restriction."
        )

    # 3. Validate every extracted endpoint is strictly loopback and port 27017
    for host, port in endpoints:
        if not is_loopback_host(str(host)):
            raise ValueError(
                f"MongoDB configuration error: Supplied client targets remote host '{host}'. "
                "JobMarketDB strictly requires local MongoDB Community Server only."
            )
        effective_port = port if port is not None else 27017
        if effective_port not in ALLOWED_PORTS:
            raise ValueError(
                f"MongoDB configuration error: Supplied client targets port {effective_port}. "
                "JobMarketDB strictly requires standard port 27017."
            )


def get_connection_config() -> Tuple[str, str]:
    """
    Retrieves and validates MongoDB connection configuration from environment variables.
    Strictly validates that the URI points to local MongoDB Community Server (localhost:27017
    or 127.0.0.1:27017) and targets the required 'jobmarketdb' database.

    Fails with a clear human-readable error if MONGODB_URI is invalid, remote, missing,
    or directs to any database other than 'jobmarketdb'.
    """
    load_dotenv()  # Refresh environment in case .env was modified at runtime
    uri = os.getenv("MONGODB_URI", "").strip()
    database_name = (
        os.getenv("MONGODB_DATABASE", DEFAULT_DATABASE_NAME).strip()
        or DEFAULT_DATABASE_NAME
    )

    if not uri:
        raise ValueError(
            "MongoDB configuration error: 'MONGODB_URI' is missing or empty.\n"
            "JobMarketDB strictly requires a local MongoDB Community Server.\n"
            "Please configure MONGODB_URI in your .env file.\n"
            "Example: MONGODB_URI=mongodb://localhost:27017/\n"
            "     or: MONGODB_URI=mongodb://127.0.0.1:27017/"
        )

    # Validate that URI targets local standalone MongoDB Community Server exclusively
    validate_local_mongo_uri(uri)

    # Validate that the database name is strictly 'jobmarketdb'
    if database_name != DEFAULT_DATABASE_NAME:
        raise ValueError(
            f"MongoDB configuration error: Database '{database_name}' is not permitted.\n"
            f"JobMarketDB strictly requires the '{DEFAULT_DATABASE_NAME}' database.\n"
            f"Please set MONGODB_DATABASE={DEFAULT_DATABASE_NAME} in your .env file."
        )

    return uri, database_name


def get_mongo_client(
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    force_new: bool = False,
) -> MongoClient:
    """
    Creates or returns a cached, reusable MongoClient instance for local MongoDB.
    Validates current environment URI and database configuration on EVERY invocation before
    returning any cached client.
    Uses directConnection=True to enforce standalone connection and prevent replica-set discovery.
    """
    global _client_instance, _cached_client_uri

    # 1. ALWAYS validate current configuration FIRST on every invocation
    uri, _ = get_connection_config()

    # 2. Return cached instance ONLY if already established for the exact validated URI
    if _client_instance is not None and not force_new and _cached_client_uri == uri:
        return _client_instance

    # 3. Clean up prior client if changing URI or forcing new
    if _client_instance is not None:
        try:
            _client_instance.close()
        except Exception:
            pass
        _client_instance = None
        _cached_client_uri = None

    try:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms,
            directConnection=True,
            retryWrites=True,
            appname="JobMarketDB",
        )
        if not force_new:
            _client_instance = client
            _cached_client_uri = uri
        return client
    except ConfigurationError as err:
        masked = mask_mongo_uri(uri)
        clean_err = mask_mongo_uri(str(err))
        raise ConnectionFailure(
            f"Invalid MongoDB connection configuration for {masked}: {clean_err}"
        ) from None
    except Exception as err:
        masked = mask_mongo_uri(uri)
        clean_err = mask_mongo_uri(str(err))
        raise ConnectionFailure(
            f"Failed to initialize MongoClient for {masked}: {clean_err}"
        ) from None


def get_database(database_name: Optional[str] = None) -> Database:
    """
    Returns the configured MongoDB Database instance.
    Does not issue network operations merely by returning the Database reference.
    Strictly restricts database access to 'jobmarketdb'.
    """
    _, default_db = get_connection_config()
    db_name = database_name or default_db

    if db_name != DEFAULT_DATABASE_NAME:
        raise ValueError(
            f"MongoDB configuration error: Database '{db_name}' is not permitted.\n"
            f"JobMarketDB strictly requires the '{DEFAULT_DATABASE_NAME}' database."
        )

    client = get_mongo_client()
    return client[db_name]


def verify_connection(
    client: Optional[MongoClient] = None, timeout_ms: int = DEFAULT_TIMEOUT_MS
) -> bool:
    """
    Verifies that the local MongoDB Community Server deployment is reachable using a low-overhead ping command.
    Returns True if healthy; raises ConnectionFailure with an informative message if unavailable.
    Guarantees credential masking across all exception paths.
    """
    uri, _ = get_connection_config()

    # 1. Strictly validate externally supplied client before executing any network ping
    if client is not None:
        validate_local_mongo_client(client)

    target_client = client or get_mongo_client(timeout_ms=timeout_ms)

    try:
        target_client.admin.command("ping")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as err:
        masked = mask_mongo_uri(uri)
        clean_err = mask_mongo_uri(str(err))
        raise ConnectionFailure(
            f"Failed to connect to local MongoDB Community Server ({masked}) within {timeout_ms}ms.\n"
            f"Ensure that local MongoDB Community Server is running on localhost:27017 (or 127.0.0.1:27017) "
            f"and reachable.\nDetails: {clean_err}"
        ) from None
    except Exception as err:
        masked = mask_mongo_uri(uri)
        clean_err = mask_mongo_uri(str(err))
        raise ConnectionFailure(
            f"Unexpected error connecting to local MongoDB Community Server ({masked}): {clean_err}"
        ) from None


def close_connection() -> None:
    """Closes the active cached MongoClient instance if open and resets cache state."""
    global _client_instance, _cached_client_uri
    if _client_instance is not None:
        try:
            _client_instance.close()
        except Exception:
            pass
        _client_instance = None
    _cached_client_uri = None
