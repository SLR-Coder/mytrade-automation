#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup Twelve Data API key in Secret Manager
"""

import os
from google.cloud import secretmanager

def create_secret():
    """Create and populate TWELVE_DATA_API_KEY secret"""

    # Initialize client
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "mytrade-automation-2025"

    # Secret details
    secret_id = "TWELVE_DATA_API_KEY"
    api_key = "5dc774532eee4b2face0ef560e128713"

    parent = f"projects/{project_id}"

    # Step 1: Create the secret
    print(f"📦 Creating secret: {secret_id}")
    try:
        secret = client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        print(f"✅ Secret created: {secret.name}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"ℹ️  Secret already exists: {secret_id}")
        else:
            print(f"❌ Failed to create secret: {e}")
            raise

    # Step 2: Add the secret version with API key value
    print(f"🔑 Adding API key value...")
    try:
        secret_name = f"{parent}/secrets/{secret_id}"
        version = client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": api_key.encode("UTF-8")},
            }
        )
        print(f"✅ Secret version added: {version.name}")
    except Exception as e:
        print(f"❌ Failed to add secret version: {e}")
        raise

    # Step 3: Verify
    print(f"🔍 Verifying secret...")
    try:
        name = f"{parent}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        retrieved_value = response.payload.data.decode("UTF-8")

        if retrieved_value == api_key:
            print(f"✅ Secret verified successfully!")
            print(f"   Value: {retrieved_value[:10]}...{retrieved_value[-10:]}")
        else:
            print(f"❌ Secret value mismatch!")
    except Exception as e:
        print(f"❌ Failed to verify secret: {e}")
        raise

    print("\n" + "=" * 60)
    print("✅ TWELVE_DATA_API_KEY SETUP COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    create_secret()
