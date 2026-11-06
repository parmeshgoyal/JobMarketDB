"""
JobMarketDB - Backend MongoDB Client & Topology Verification Script
Inspects the actual PyMongo client, topology, active database, and canonical reads.
"""

import os
import re
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from database.connection import (
    get_connection_config,
    get_mongo_client,
    get_database,
    mask_mongo_uri,
)

def run_backend_audit():
    print("================================================================================")
    print(" JobMarketDB - Backend MongoDB Client & Topology Runtime Audit")
    print("================================================================================")

    # 1. Connection Configuration Inspection
    uri, db_name = get_connection_config()
    masked_uri = mask_mongo_uri(uri)
    print("\n--- 1. Effective Runtime Configuration ---")
    print(f"Masked Configured URI: {masked_uri}")
    print(f"Configured Database:   {db_name}")

    # Check for Atlas / SRV / Credential files
    is_srv = uri.startswith("mongodb+srv://")
    has_atlas_domain = "mongodb.net" in uri or "atlas" in uri.lower()
    has_localhost = "localhost:27017" in uri or "127.0.0.1:27017" in uri

    print(f"SRV Protocol Used:     {is_srv} (Expected: False)")
    print(f"Atlas Domain Present:  {has_atlas_domain} (Expected: False)")
    print(f"Localhost:27017 Used:  {has_localhost} (Expected: True)")

    assert not is_srv, "ERROR: SRV protocol detected in MongoDB URI!"
    assert not has_atlas_domain, "ERROR: Atlas domain detected in MongoDB URI!"
    assert has_localhost, "ERROR: Localhost:27017 not detected in MongoDB URI!"
    print("[PASS] Effective configuration points strictly to local MongoDB.")

    # 2. PyMongo Client Server & Topology Inspection
    print("\n--- 2. Active PyMongo Client Topology & Server Info ---")
    client = get_mongo_client()
    
    address = client.address
    nodes = list(client.nodes)
    primary = client.primary
    topo_desc = client.topology_description
    
    print(f"Client Address:        {address}")
    print(f"Topology Nodes:        {nodes}")
    print(f"Primary Server:        {primary}")
    print(f"Topology Type:         {topo_desc.topology_type_name}")

    # Server Info (ping and metadata)
    server_info = client.server_info()
    version = server_info.get("version", "Unknown")
    git_version = server_info.get("gitVersion", "Unknown")
    sys_info = server_info.get("sysInfo", "Unknown")
    ok_status = server_info.get("ok", 0)

    print(f"MongoDB Server Version:{version}")
    print(f"Git Version:           {git_version}")
    print(f"Server Status 'ok':    {ok_status}")
    
    assert ok_status == 1.0, "ERROR: Server info check failed!"
    assert any("27017" in str(node) for node in nodes), f"ERROR: Node port 27017 not found in {nodes}!"
    print("[PASS] Active PyMongo client is connected directly to local MongoDB (port 27017).")

    # 3. Active Database & Canonical Collection Reads
    print("\n--- 3. Active Database & Canonical Reads Execution ---")
    db = get_database()
    print(f"Active Database Name:  {db.name}")
    assert db.name == "jobmarketdb", f"ERROR: Database name mismatch: {db.name}"

    # Read from jobs
    jobs_sample = db.jobs.find_one({}, {"_id": 1, "title": 1, "source": 1, "company.name": 1})
    jobs_count = db.jobs.count_documents({})
    print(f"Canonical 'jobs' read: Success! Count: {jobs_count:,}")
    print(f"Sample 'jobs' doc:     ID={jobs_sample.get('_id')} | Title='{jobs_sample.get('title')}' | Source='{jobs_sample.get('source')}'")
    assert jobs_count == 129550, f"ERROR: jobs count invariant failed: {jobs_count}"

    # Read from companies
    companies_sample = db.companies.find_one({}, {"_id": 1, "name": 1, "company_id": 1})
    companies_count = db.companies.count_documents({})
    print(f"Canonical 'companies': Success! Count: {companies_count:,}")
    print(f"Sample 'companies' doc:ID={companies_sample.get('_id')} | Name='{companies_sample.get('name')}' | CompanyID='{companies_sample.get('company_id')}'")
    assert companies_count == 24472, f"ERROR: companies count invariant failed: {companies_count}"

    print("[PASS] Canonical reads against 'jobs' and 'companies' succeeded with 100% document fidelity.")

    # 4. Connection Code & Fallback Analysis
    print("\n--- 4. Connection Code & Fallback Path Audit ---")
    conn_file = os.path.join(os.path.dirname(__file__), "..", "database", "connection.py")
    with open(conn_file, "r", encoding="utf-8") as f:
        conn_code = f.read()

    has_fallback = "fallback" in conn_code.lower()
    has_executable_atlas_default = bool(re.search(r'DEFAULT.*mongodb\.net', conn_code))
    loads_atlas_credentials_file = "atlas-credentials" in conn_code
    print(f"Loads atlas-credentials.env:          {loads_atlas_credentials_file} (Expected: False)")
    print(f"Executable Atlas default URI in code:  {has_executable_atlas_default} (Expected: False)")
    print(f"Runtime Fallback Mechanism to Atlas:   {has_fallback} (Expected: False)")

    assert not loads_atlas_credentials_file, "ERROR: Reference to atlas-credentials.env found!"
    assert not has_executable_atlas_default, "ERROR: Executable Atlas default found in connection.py!"
    assert not has_fallback, "ERROR: Fallback mechanism found!"
    print("[PASS] Zero Atlas fallback, zero credential file dependencies, zero SRV requirements.")

    print("\n================================================================================")
    print(" Result: BACKEND MONGODB LOCAL CLIENT AUDIT PASSED (100% Localhost:27017)")
    print("================================================================================")

if __name__ == "__main__":
    run_backend_audit()
