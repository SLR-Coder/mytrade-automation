#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add TWELVE_DATA_API_KEY to Secret Manager
"""

import os

try:
    from google.cloud import secretmanager

    # Initialize client
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "mytrade-automation-2025"

    parent = f"projects/{project_id}"
    secret_id = "TWELVE_DATA_API_KEY"
    api_key = "16b066a61ccd4d73817b01f78557a072"

    print(f"🔐 Creating secret: {secret_id}")
    print(f"📦 Project: {project_id}")

    # Step 1: Create secret (if not exists)
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
            print(f"ℹ️  Secret already exists, adding new version...")
        else:
            print(f"❌ Error creating secret: {e}")
            raise

    # Step 2: Add secret version
    secret_name = f"{parent}/secrets/{secret_id}"
    version = client.add_secret_version(
        request={
            "parent": secret_name,
            "payload": {"data": api_key.encode("UTF-8")},
        }
    )
    print(f"✅ API key saved: {version.name}")
    print(f"   Key: {api_key[:10]}...{api_key[-8:]}")

    # Step 3: Verify
    name = f"{parent}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    retrieved_value = response.payload.data.decode("UTF-8")

    if retrieved_value == api_key:
        print(f"✅ Verification successful!")
    else:
        print(f"❌ Verification failed!")

    print("\n" + "=" * 60)
    print("✅ TWELVE_DATA_API_KEY KAYIT EDİLDİ!")
    print("=" * 60)

except ImportError:
    print("❌ google-cloud-secretmanager modülü bulunamadı")
    print("Alternatif: Environment variable kullan:")
    print()
    print("export TWELVE_DATA_API_KEY='16b066a61ccd4d73817b01f78557a072'")

except Exception as e:
    print(f"❌ Hata: {e}")
    print()
    print("Alternatif: Environment variable kullan:")
    print()
    print("export TWELVE_DATA_API_KEY='16b066a61ccd4d73817b01f78557a072'")
