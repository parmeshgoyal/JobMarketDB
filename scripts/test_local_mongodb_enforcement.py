"""
JobMarketDB - Local MongoDB Enforcement & Security Hardening Test Suite

Tests strict local MongoDB Community Server enforcement in database/connection.py:
1. mongodb://localhost:27017/ is accepted
2. mongodb://127.0.0.1:27017/ is accepted
3. Atlas mongodb+srv:// URI is rejected
4. Remote MongoDB hostname is rejected
5. Remote IP address is rejected
6. Incorrect database configuration is rejected
7. Credentials are never exposed in error messages
8. Existing connection helper functions remain compatible
9. Invalid configuration cannot trigger a remote connection attempt
10. Local MongoDB configuration still passes the connection ping when local server is available
11. Finding 1: Cached-client validation cannot be bypassed by changing environment URI
12. Finding 2: Replica-set options (replicaSet, directConnection=false) are rejected
13. Finding 2: directConnection=True enforces Single topology and prevents remote peer discovery
14. Finding 3: Comprehensive credential masking across all exception paths and error chains
15. Finding 4: Externally supplied client validation prevents remote MongoDB ping in verify_connection
"""

import os
import sys
import traceback
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import (
    DEFAULT_DATABASE_NAME,
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
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConfigurationError, ConnectionFailure, ServerSelectionTimeoutError
from pymongo.hello import Hello
from pymongo.server_description import ServerDescription
from pymongo.topology_description import TOPOLOGY_TYPE, TopologyDescription, updated_topology_description


class TestLocalMongoDBEnforcement(unittest.TestCase):
    """Test suite ensuring JobMarketDB strictly connects to local MongoDB Community Server only."""

    def setUp(self):
        close_connection()

    def tearDown(self):
        close_connection()

    # 1. mongodb://localhost:27017/ is accepted
    def test_01_localhost_uri_accepted(self):
        valid_localhost_uris = [
            "mongodb://localhost:27017/",
            "mongodb://localhost:27017",
            "mongodb://localhost:27017/jobmarketdb",
            "mongodb://localhost:27017/jobmarketdb?retryWrites=true",
            "mongodb://localhost:27017/?directConnection=true",
        ]
        for uri in valid_localhost_uris:
            with self.subTest(uri=uri):
                try:
                    validate_local_mongo_uri(uri)
                except Exception as e:
                    self.fail(f"Valid localhost URI '{uri}' was unexpectedly rejected: {e}")

    # 2. mongodb://127.0.0.1:27017/ is accepted
    def test_02_loopback_ip_uri_accepted(self):
        valid_loopback_uris = [
            "mongodb://127.0.0.1:27017/",
            "mongodb://127.0.0.1:27017",
            "mongodb://127.0.0.1:27017/jobmarketdb",
            "mongodb://127.0.0.1:27017/jobmarketdb?retryWrites=true",
            "mongodb://[::1]:27017/",
            "mongodb://[::1]:27017/jobmarketdb",
        ]
        for uri in valid_loopback_uris:
            with self.subTest(uri=uri):
                try:
                    validate_local_mongo_uri(uri)
                except Exception as e:
                    self.fail(f"Valid loopback URI '{uri}' was unexpectedly rejected: {e}")

    # 3. Atlas mongodb+srv:// URI is rejected
    def test_03_atlas_srv_uri_rejected(self):
        atlas_uris = [
            "mongodb+srv://cluster0.abcde.mongodb.net/",
            "mongodb+srv://cluster0.abcde.mongodb.net/jobmarketdb",
            "mongodb+srv://user:secret@cluster0.abcde.mongodb.net/?retryWrites=true",
            "mongodb+srv://app-cluster.mongodb.net/",
        ]
        for uri in atlas_uris:
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError) as ctx:
                    validate_local_mongo_uri(uri)
                err_msg = str(ctx.exception)
                self.assertIn("mongodb+srv://", err_msg)
                self.assertIn("prohibited", err_msg.lower())
                self.assertIn("local mongodb community server", err_msg.lower())

    # 4. Remote MongoDB hostname is rejected
    def test_04_remote_hostname_rejected(self):
        remote_hosts = [
            "mongodb://remote.example.com:27017/",
            "mongodb://cluster0.abcde.mongodb.net:27017/",
            "mongodb://db.corporate.lan:27017/",
            "mongodb://ec2-54-210-10-10.compute-1.amazonaws.com:27017/",
            "mongodb://mongo-prod.internal:27017/",
        ]
        for uri in remote_hosts:
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError) as ctx:
                    validate_local_mongo_uri(uri)
                err_msg = str(ctx.exception)
                self.assertIn("prohibited", err_msg.lower())
                self.assertIn("remote mongodb host", err_msg.lower())
                self.assertIn("local mongodb community server", err_msg.lower())

    # 5. Remote IP address is rejected
    def test_05_remote_ip_rejected(self):
        remote_ips = [
            "mongodb://192.168.1.100:27017/",
            "mongodb://10.0.0.5:27017/",
            "mongodb://172.16.0.2:27017/",
            "mongodb://8.8.8.8:27017/",
            "mongodb://54.210.10.10:27017/",
            "mongodb://0.0.0.0:27017/",
        ]
        for uri in remote_ips:
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError) as ctx:
                    validate_local_mongo_uri(uri)
                err_msg = str(ctx.exception)
                self.assertIn("remote ip address", err_msg.lower())
                self.assertIn("prohibited", err_msg.lower())
                self.assertIn("local mongodb community server", err_msg.lower())

    # 6. Incorrect database configuration is rejected
    def test_06_incorrect_database_rejected(self):
        # 6a. MONGODB_DATABASE env var set to another database
        with patch.dict(os.environ, {"MONGODB_URI": "mongodb://localhost:27017/", "MONGODB_DATABASE": "wrong_db"}):
            with self.assertRaises(ValueError) as ctx:
                get_connection_config()
            self.assertIn("wrong_db", str(ctx.exception))
            self.assertIn("jobmarketdb", str(ctx.exception))

        # 6b. URI specifies a different database in path
        with self.assertRaises(ValueError) as ctx:
            validate_local_mongo_uri("mongodb://localhost:27017/production_db")
        self.assertIn("production_db", str(ctx.exception))
        self.assertIn("jobmarketdb", str(ctx.exception))

        # 6c. get_database called with a non-jobmarketdb name
        with self.assertRaises(ValueError) as ctx:
            get_database("malicious_db")
        self.assertIn("malicious_db", str(ctx.exception))
        self.assertIn("jobmarketdb", str(ctx.exception))

    # 7. Credentials are never exposed in error messages
    def test_07_credentials_never_exposed_in_error_messages(self):
        secret_password = "SuperSecret_P@ssw0rd!_DoNotLeak"
        test_cases = [
            f"mongodb+srv://admin_user:{secret_password}@cluster0.abcde.mongodb.net/jobmarketdb",
            f"mongodb://db_admin:{secret_password}@remote-host.com:27017/",
            f"mongodb://sys_user:{secret_password}@192.168.1.50:27017/",
            f"mongodb://local_user:{secret_password}@localhost:27018/",  # invalid port
            f"mongodb://app_user:{secret_password}@localhost:27017/otherdb",  # wrong db
        ]

        for uri in test_cases:
            with self.subTest(uri=uri):
                try:
                    validate_local_mongo_uri(uri)
                    self.fail("Expected ValueError was not raised!")
                except ValueError as err:
                    err_msg = str(err)
                    self.assertNotIn(
                        secret_password,
                        err_msg,
                        f"CRITICAL LEAK: Password was found in error message: {err_msg}",
                    )
                    self.assertIn(":***", err_msg, "Masked placeholder ':***' should be present.")

    # 8. Existing connection helper functions remain compatible
    def test_08_connection_helpers_compatibility(self):
        # get_connection_config
        uri, db_name = get_connection_config()
        self.assertTrue(uri.startswith("mongodb://"))
        self.assertIn("27017", uri)
        self.assertEqual(db_name, DEFAULT_DATABASE_NAME)

        # get_mongo_client caching
        client1 = get_mongo_client()
        client2 = get_mongo_client()
        self.assertIs(client1, client2, "get_mongo_client() should return cached singleton.")

        # get_database returns Database instance
        db = get_database()
        self.assertIsInstance(db, Database)
        self.assertEqual(db.name, DEFAULT_DATABASE_NAME)

        # close_connection
        close_connection()
        # Verify next client call re-instantiates cleanly
        client3 = get_mongo_client()
        self.assertIsInstance(client3, MongoClient)

        # mask_mongo_uri compatibility
        masked = mask_mongo_uri("mongodb://usr:pwd@localhost:27017/")
        self.assertEqual(masked, "mongodb://usr:***@localhost:27017/")
        self.assertEqual(mask_mongo_uri(""), "<EMPTY>")

    # 9. Invalid configuration cannot trigger a remote connection attempt
    def test_09_invalid_config_prevents_remote_connection_attempt(self):
        # If an invalid URI is provided, MongoClient must never be initialized
        remote_uri = "mongodb+srv://user:pass@cluster0.mongodb.net/jobmarketdb"
        with patch.dict(os.environ, {"MONGODB_URI": remote_uri}):
            with patch("database.connection.MongoClient") as mock_client:
                with self.assertRaises(ValueError):
                    get_mongo_client(force_new=True)
                mock_client.assert_not_called()

        remote_ip_uri = "mongodb://192.168.1.200:27017/"
        with patch.dict(os.environ, {"MONGODB_URI": remote_ip_uri}):
            with patch("database.connection.MongoClient") as mock_client:
                with self.assertRaises(ValueError):
                    get_mongo_client(force_new=True)
                mock_client.assert_not_called()

    # 10. Local MongoDB configuration passes connection ping when local server is available
    def test_10_local_mongodb_ping_passes(self):
        # Ping the local MongoDB Community Server
        is_healthy = verify_connection(timeout_ms=5000)
        self.assertTrue(is_healthy, "verify_connection() should succeed on local MongoDB Community Server.")

        # Also verify database ping command directly
        db = get_database()
        ping_result = db.command("ping")
        self.assertEqual(ping_result.get("ok"), 1.0, "Database ping command returned ok != 1.0")

    # 11. Finding 1: Cached client validation cannot be bypassed by changing environment
    def test_11_cached_client_validation_cannot_be_bypassed(self):
        """
        Regression test for Finding 1:
        1. Establish and cache a valid local client.
        2. Change environment URI to an invalid remote URI.
        3. Call get_mongo_client() without force_new=True.
        4. Confirm that validation raises ValueError instead of returning cached client.
        5. Confirm MongoClient is not initialized for the invalid configuration.
        """
        # Step 1: Establish valid local client and verify it's cached
        client1 = get_mongo_client()
        self.assertIsInstance(client1, MongoClient)

        # Step 2: Change environment URI to an invalid remote URI
        remote_uri = "mongodb+srv://user:secret@cluster0.mongodb.net/jobmarketdb"
        with patch.dict(os.environ, {"MONGODB_URI": remote_uri}):
            # Step 3 & 4: Call get_mongo_client() without force_new=True, assert ValueError
            with patch("database.connection.MongoClient") as mock_client:
                with self.assertRaises(ValueError) as ctx:
                    get_mongo_client(force_new=False)

                err_msg = str(ctx.exception)
                self.assertIn("mongodb+srv://", err_msg)
                self.assertIn("prohibited", err_msg.lower())

                # Step 5: Confirm MongoClient was NOT initialized for the invalid configuration
                mock_client.assert_not_called()

    # 12. Finding 2: Replica-set options in URI are rejected
    def test_12_replica_set_options_rejected(self):
        """
        Regression test for Finding 2:
        Asserts that replicaSet and directConnection=false options are rejected to prevent
        remote replica-set member discovery.
        """
        # 12a. replicaSet in URI
        with self.assertRaises(ValueError) as ctx:
            validate_local_mongo_uri("mongodb://localhost:27017/?replicaSet=rs0")
        self.assertIn("replicaSet=rs0", str(ctx.exception))
        self.assertIn("prohibited", str(ctx.exception).lower())

        # 12b. directConnection=false in URI
        with self.assertRaises(ValueError) as ctx:
            validate_local_mongo_uri("mongodb://localhost:27017/?directConnection=false")
        self.assertIn("directConnection=false", str(ctx.exception))
        self.assertIn("prohibited", str(ctx.exception).lower())

        # 12c. directConnection=true in URI is permitted
        try:
            validate_local_mongo_uri("mongodb://localhost:27017/?directConnection=true")
        except Exception as e:
            self.fail(f"directConnection=true should be permitted: {e}")

    # 13. Finding 2: directConnection=True enforces Single topology and prevents remote peer discovery
    def test_13_direct_connection_prevents_remote_member_discovery(self):
        """
        Controlled topology test:
        1. Confirms MongoClient created by get_mongo_client() has direct_connection=True.
        2. Simulates an SDAM hello response containing remote replica-set peers.
        3. Proves that Single topology (as enforced by directConnection=True) strictly ignores remote peers.
        """
        # 1. Verify direct_connection option on client
        client = get_mongo_client()
        self.assertTrue(client.options.direct_connection, "direct_connection setting must be True.")

        # 2. Simulate SDAM Hello response claiming remote peer membership
        hello_doc = Hello({
            "ok": 1.0,
            "setName": "rs0",
            "hosts": ["localhost:27017", "remote-peer.example.com:27017", "192.168.1.100:27017"],
            "isWritablePrimary": True,
            "minWireVersion": 0,
            "maxWireVersion": 21,
        })
        server_desc = ServerDescription(("localhost", 27017), hello_doc, round_trip_time=0.001)

        # 3. Simulate TopologyDescription under Single mode (as established by directConnection=True)
        td_single = TopologyDescription(
            topology_type=TOPOLOGY_TYPE.Single,
            server_descriptions={("localhost", 27017): ServerDescription(("localhost", 27017))},
            replica_set_name=None,
            max_set_version=None,
            max_election_id=None,
            topology_settings=None,
        )

        # Process hello update
        updated_td = updated_topology_description(td_single, server_desc)

        # Confirm topology remains strictly Single and NO remote servers are discovered
        self.assertEqual(updated_td.topology_type_name, "Single")
        monitored_servers = list(updated_td.server_descriptions().keys())
        self.assertEqual(
            monitored_servers,
            [("localhost", 27017)],
            f"Remote servers leaked into Single topology! Found: {monitored_servers}",
        )
        self.assertNotIn(("remote-peer.example.com", 27017), monitored_servers)
        self.assertNotIn(("192.168.1.100", 27017), monitored_servers)

    # 14. Finding 3: Comprehensive credential masking across all exception paths and error chains
    def test_14_credential_masking_across_all_exception_paths(self):
        """
        Regression test for Finding 3:
        Validates that known secret passwords never appear in any exception message,
        traceback, or chained cause across validate_local_mongo_uri, get_connection_config,
        get_mongo_client, and verify_connection.
        """
        # 14. Finding 3: Comprehensive credential masking across all exception paths and error chains
        secret_pass = "UltraSecret_P$ssw0rd_987654321!"
        unescaped_at_pass = "UltraSecret_P@ssw0rd_987654321!"
        masked_placeholder = ":***@"

        # 14a. validate_local_mongo_uri with malformed syntax and unescaped credentials
        malformed_uri = f"mongodb://app_user:{secret_pass}@localhost:27017/??invalid_query"
        with self.assertRaises(ValueError) as ctx:
            validate_local_mongo_uri(malformed_uri)
        err_str = str(ctx.exception)
        tb_str = "".join(traceback.format_exception(ctx.exception))
        self.assertNotIn(secret_pass, err_str, "Password leaked in validate_local_mongo_uri malformed URI!")
        self.assertNotIn(secret_pass, tb_str, "Password leaked in traceback for malformed URI!")
        self.assertIn(masked_placeholder, err_str)
        self.assertIsNone(ctx.exception.__cause__, "Chained __cause__ must be suppressed with 'from None'")

        # Also verify unescaped @ in password is masked when parse_uri rejects it
        with self.assertRaises(ValueError) as ctx:
            validate_local_mongo_uri(f"mongodb://app_user:{unescaped_at_pass}@localhost:27017/jobmarketdb")
        err_str = str(ctx.exception)
        tb_str = "".join(traceback.format_exception(ctx.exception))
        self.assertNotIn(unescaped_at_pass, err_str, "Unescaped @ password leaked in parse_uri error!")
        self.assertNotIn(unescaped_at_pass, tb_str, "Unescaped @ password leaked in traceback!")
        self.assertIn(masked_placeholder, err_str)
        self.assertIsNone(ctx.exception.__cause__, "Chained __cause__ must be suppressed with 'from None'")

        # 14b. get_connection_config with remote credential URI
        remote_uri = f"mongodb://admin:{secret_pass}@remote-server.com:27017/"
        with patch.dict(os.environ, {"MONGODB_URI": remote_uri}):
            with self.assertRaises(ValueError) as ctx:
                get_connection_config()
            err_str = str(ctx.exception)
            tb_str = "".join(traceback.format_exception(ctx.exception))
            self.assertNotIn(secret_pass, err_str, "Password leaked in get_connection_config!")
            self.assertNotIn(secret_pass, tb_str, "Password leaked in traceback for get_connection_config!")
            self.assertIn(masked_placeholder, err_str)
            self.assertIsNone(ctx.exception.__cause__, "Chained __cause__ must be suppressed with 'from None'")

        # 14c. get_mongo_client when MongoClient raises ConfigurationError with credentials
        valid_local_uri = f"mongodb://local_user:{secret_pass}@localhost:27017/jobmarketdb"
        with patch.dict(os.environ, {"MONGODB_URI": valid_local_uri}):
            with patch("database.connection.MongoClient", side_effect=ConfigurationError(f"Bad configuration options in {valid_local_uri}")):
                with self.assertRaises(ConnectionFailure) as ctx:
                    get_mongo_client(force_new=True)
                err_str = str(ctx.exception)
                tb_str = "".join(traceback.format_exception(ctx.exception))
                self.assertNotIn(secret_pass, err_str, "Password leaked in get_mongo_client ConfigurationError!")
                self.assertNotIn(secret_pass, tb_str, "Password leaked in traceback for ConfigurationError!")
                self.assertIn(masked_placeholder, err_str)
                self.assertIsNone(ctx.exception.__cause__, "Chained __cause__ must be suppressed with 'from None'")

        # 14d. verify_connection when ping fails with connection timeout
        with patch.dict(os.environ, {"MONGODB_URI": valid_local_uri}):
            mock_client = MagicMock()
            mock_client.options.direct_connection = True
            mock_client.options.replica_set_name = None
            mock_client.nodes = {("localhost", 27017)}
            mock_client.admin.command.side_effect = ServerSelectionTimeoutError(f"ServerSelectionTimeoutError connecting to {valid_local_uri}: connection timed out")
            with self.assertRaises(ConnectionFailure) as ctx:
                verify_connection(client=mock_client)
            err_str = str(ctx.exception)
            tb_str = "".join(traceback.format_exception(ctx.exception))
            self.assertNotIn(secret_pass, err_str, "Password leaked in verify_connection timeout!")
            self.assertNotIn(secret_pass, tb_str, "Password leaked in traceback for timeout!")
            self.assertIn(masked_placeholder, err_str)
            self.assertIsNone(ctx.exception.__cause__, "Chained __cause__ must be suppressed with 'from None'")

    def test_15_externally_supplied_client_validation_prevents_remote_ping(self):
        """
        Regression test for Finding 4:
        Validates that verify_connection strictly validates any externally supplied client,
        preventing bypass of the local-only MongoDB policy and ensuring no ping is executed
        against remote hosts, remote IPs, replica sets, or disallowed ports.
        """
        # 1. Supplied client targeting remote hostname with directConnection=True is rejected specifically for remote hostname restriction
        remote_client = MongoClient(
            "mongodb://remote-db.corp.net:27017/?directConnection=true&connect=false",
            serverSelectionTimeoutMS=100,
        )
        with patch.object(Database, "command") as mock_cmd:
            with self.assertRaises(ValueError) as ctx:
                verify_connection(client=remote_client)
            self.assertIn("remote host 'remote-db.corp.net'", str(ctx.exception))
            mock_cmd.assert_not_called()

        # 2. Supplied client targeting remote IP is rejected before any ping
        remote_ip_client = MongoClient(
            "mongodb://192.168.1.100:27017/?directConnection=true&connect=false",
            serverSelectionTimeoutMS=100,
        )
        with patch.object(Database, "command") as mock_cmd:
            with self.assertRaises(ValueError) as ctx:
                verify_connection(client=remote_ip_client)
            self.assertIn("remote host '192.168.1.100'", str(ctx.exception))
            mock_cmd.assert_not_called()

        # 3. Supplied client with replicaSet is rejected specifically for replica-set restriction
        rs_client = MagicMock()
        rs_client.options.direct_connection = True
        rs_client.options.replica_set_name = "myrs"
        rs_client.nodes = {("localhost", 27017)}
        with patch.object(Database, "command") as mock_cmd:
            with self.assertRaises(ValueError) as ctx:
                verify_connection(client=rs_client)
            self.assertIn("replicaSet=myrs", str(ctx.exception))
            mock_cmd.assert_not_called()
            rs_client.admin.command.assert_not_called()

        # 4. Supplied client targeting unauthorized port is rejected before any ping
        port_client = MongoClient("mongodb://localhost:27018/?directConnection=true&connect=false")
        with patch.object(Database, "command") as mock_cmd:
            with self.assertRaises(ValueError) as ctx:
                verify_connection(client=port_client)
            self.assertIn("port 27018", str(ctx.exception))
            mock_cmd.assert_not_called()

        # 5. Supplied mock client targeting remote host is rejected and command() is never called
        mock_remote = MagicMock()
        mock_remote.options.direct_connection = True
        mock_remote.options.replica_set_name = None
        mock_remote.nodes = {("attacker.remote.net", 27017)}
        with patch.object(Database, "command") as mock_cmd:
            with self.assertRaises(ValueError) as ctx:
                verify_connection(client=mock_remote)
            self.assertIn("remote host 'attacker.remote.net'", str(ctx.exception))
            mock_cmd.assert_not_called()
            mock_remote.admin.command.assert_not_called()

        # 6. Supplied mock client with no identifiable endpoints is rejected
        mock_empty = MagicMock()
        mock_empty.options.direct_connection = True
        mock_empty.options.replica_set_name = None
        mock_empty.nodes = set()
        mock_empty.topology_description.server_descriptions.return_value = {}
        with patch.object(Database, "command") as mock_cmd:
            with self.assertRaises(ValueError) as ctx:
                verify_connection(client=mock_empty)
            self.assertIn("no identifiable server endpoints", str(ctx.exception))
            mock_cmd.assert_not_called()
            mock_empty.admin.command.assert_not_called()

        # 7. Valid local client passes validation and successfully executes ping
        local_client = MongoClient("mongodb://localhost:27017/?directConnection=true")
        try:
            self.assertTrue(verify_connection(client=local_client))
        finally:
            local_client.close()


if __name__ == "__main__":
    unittest.main()
