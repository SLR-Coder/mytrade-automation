# utils/auth.py
# -*- coding: utf-8 -*-
"""
Google authentication utilities
"""

import os
import logging
import gspread
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from utils.secrets import get_secret

logger = logging.getLogger("Auth")

def get_gspread_client():
    """
    Get authenticated Google Sheets client

    Returns:
        gspread.Client: Authenticated client
    """
    logger.info("Authenticating with Google Sheets...")

    # Try service account credentials from environment
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if credentials_path and os.path.exists(credentials_path):
        logger.info(f"Using service account from: {credentials_path}")
        return gspread.service_account(filename=credentials_path)

    # Try to get credentials from secret manager (for production)
    try:
        import json
        credentials_json = get_secret("GOOGLE_SERVICE_ACCOUNT", required=False)
        if credentials_json:
            credentials = json.loads(credentials_json)
            return gspread.service_account_from_dict(credentials)
    except:
        pass

    # Default to ADC (Application Default Credentials) for Cloud Run
    logger.info("Using Application Default Credentials (Workload Identity)")
    from google.auth import default

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    credentials, project = default(scopes=scopes)
    return gspread.authorize(credentials)