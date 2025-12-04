#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Secret Manager erişimi ve Robot 4 & 5 hazırlığı
"""

import os
import sys

def test_secret_manager():
    """Test Google Cloud Secret Manager access"""
    print("=" * 80)
    print("🔐 SECRET MANAGER ERİŞİM TESTİ")
    print("=" * 80)

    # Check environment variables
    print("\n1️⃣ Environment Variables:")
    env_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "GCP_PROJECT",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY"
    ]

    found_vars = []
    missing_vars = []

    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "TOKEN" in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"  ✅ {var}: {display_value}")
            found_vars.append(var)
        else:
            print(f"  ❌ {var}: Not set")
            missing_vars.append(var)

    # Check Google Cloud Secret Manager
    print("\n2️⃣ Google Cloud Secret Manager:")
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()

        project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "mytrade-automation-2025"
        print(f"  📦 Project ID: {project_id}")

        # Try to access a secret
        try:
            secret_name = "GOOGLE_SHEETS_SPREADSHEET_ID"
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            value = response.payload.data.decode("UTF-8")
            print(f"  ✅ Secret Manager erişimi BAŞARILI!")
            print(f"  ✅ '{secret_name}' secret'ı okunabildi")
            return True
        except Exception as e:
            print(f"  ❌ Secret Manager erişimi BAŞARISIZ: {e}")
            return False

    except ImportError as e:
        print(f"  ❌ google-cloud-secret-manager kütüphanesi yüklü değil: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Secret Manager bağlantısı kurulamadı: {e}")
        return False


def test_google_sheets():
    """Test Google Sheets access"""
    print("\n3️⃣ Google Sheets Erişimi:")
    try:
        from utils.auth import get_gspread_client
        from utils.secrets import get_secret

        sheet_id = get_secret("GOOGLE_SHEETS_SPREADSHEET_ID", required=False)
        if not sheet_id:
            print("  ❌ GOOGLE_SHEETS_SPREADSHEET_ID bulunamadı")
            return False

        print(f"  📊 Sheet ID: {sheet_id[:20]}...")

        gc = get_gspread_client()
        ws = gc.open_by_key(sheet_id).worksheet("MarketData")

        # Read first row (header)
        header = ws.row_values(1)
        print(f"  ✅ Google Sheets bağlantısı BAŞARILI!")
        print(f"  ✅ Sütun sayısı: {len(header)}")
        return True

    except Exception as e:
        print(f"  ❌ Google Sheets erişimi BAŞARISIZ: {e}")
        return False


def test_telegram():
    """Test Telegram Bot access"""
    print("\n4️⃣ Telegram Bot Erişimi:")
    try:
        from utils.secrets import get_secret
        import asyncio
        from telegram import Bot

        bot_token = get_secret("TELEGRAM_BOT_TOKEN", required=False)
        chat_id = get_secret("TELEGRAM_CHAT_ID", required=False)

        if not bot_token:
            print("  ❌ TELEGRAM_BOT_TOKEN bulunamadı")
            return False

        if not chat_id:
            print("  ❌ TELEGRAM_CHAT_ID bulunamadı")
            return False

        print(f"  🤖 Bot Token: {bot_token[:20]}...")
        print(f"  💬 Chat ID: {chat_id}")

        # Test bot connection
        async def test_bot():
            bot = Bot(token=bot_token)
            me = await bot.get_me()
            print(f"  ✅ Telegram Bot bağlantısı BAŞARILI!")
            print(f"  ✅ Bot Username: @{me.username}")
            return True

        return asyncio.run(test_bot())

    except Exception as e:
        print(f"  ❌ Telegram Bot erişimi BAŞARISIZ: {e}")
        return False


def show_test_commands():
    """Show commands to test Robot 4 and Robot 5"""
    print("\n" + "=" * 80)
    print("🧪 ROBOT 4 & 5 TEST KOMUTLARI")
    print("=" * 80)

    print("\n📝 Manuel Test Komutları (Cloud Shell veya Cloud Run'da):")
    print("\n# Robot 4 - Chart Generator:")
    print("  PYTHONPATH=/home/user/mytrade-automation python3 robots/chart_generator.py")

    print("\n# Robot 5 - Telegram Publisher:")
    print("  PYTHONPATH=/home/user/mytrade-automation python3 robots/telegram_publisher.py")

    print("\n# Robot 6 - Performance Tracker (Pipeline):")
    print("  cd /home/user/mytrade-automation")
    print("  ./test_robot6_pipeline.sh")

    print("\n" + "=" * 80)
    print("📋 ÖNERİLER:")
    print("=" * 80)

    print("""
1. Bu script'i Cloud Shell'de çalıştırın:
   gcloud auth application-default login
   python3 test_secret_manager.py

2. Secret Manager'da olması gereken secret'lar:
   - GOOGLE_SHEETS_SPREADSHEET_ID
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
   - ANTHROPIC_API_KEY (Robot 7 için)
   - OPENAI_API_KEY (Robot 3 için)
   - GEMINI_API_KEY (Robot 3 ve 8 için)

3. Cloud Run'da test için:
   gcloud run jobs execute robot-4-chart-generator --region=us-central1
   gcloud run jobs execute robot-5-telegram-publisher --region=us-central1

4. Local test için (credentials varsa):
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   export GOOGLE_SHEETS_SPREADSHEET_ID=your-sheet-id
   export TELEGRAM_BOT_TOKEN=your-bot-token
   export TELEGRAM_CHAT_ID=your-chat-id
   python3 robots/chart_generator.py
    """)


if __name__ == "__main__":
    print("\n" + "🚀 MyTrade Robot Test Utility\n")

    # Add project root to path
    sys.path.insert(0, "/home/user/mytrade-automation")

    # Run tests
    sm_ok = test_secret_manager()

    if sm_ok:
        sheets_ok = test_google_sheets()
        telegram_ok = test_telegram()

        print("\n" + "=" * 80)
        print("📊 TEST SONUÇLARI:")
        print("=" * 80)
        print(f"  Secret Manager: {'✅ BAŞARILI' if sm_ok else '❌ BAŞARISIZ'}")
        print(f"  Google Sheets:  {'✅ BAŞARILI' if sheets_ok else '❌ BAŞARISIZ'}")
        print(f"  Telegram Bot:   {'✅ BAŞARILI' if telegram_ok else '❌ BAŞARISIZ'}")

        if sm_ok and sheets_ok and telegram_ok:
            print("\n🎉 TÜM TESTLER BAŞARILI! Robot 4 ve 5 çalıştırılabilir.")
        else:
            print("\n⚠️  Bazı testler başarısız. Yukarıdaki hataları kontrol edin.")
    else:
        print("\n⚠️  Secret Manager erişimi yok. Bu ortamda test edilemiyor.")
        print("     Cloud Shell veya Cloud Run ortamında test edin.")

    # Show test commands
    show_test_commands()
