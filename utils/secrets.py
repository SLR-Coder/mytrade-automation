# utils/secrets.py
# -*- coding: utf-8 -*-
"""
Secret management utilities
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("Secrets")

def get_secret(secret_name: str, required: bool = True) -> Optional[str]:
    """
    Get secret value from environment or Secret Manager

    Args:
        secret_name: Name of the secret
        required: Whether the secret is required

    Returns:
        Secret value or None
    """
    # First try environment variable
    value = os.getenv(secret_name)
    if value:
        return value

    # Try Google Secret Manager in production
    if os.getenv("ENVIRONMENT") == "production":
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT"))

            if project_id:
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                value = response.payload.data.decode("UTF-8")
                return value
        except Exception as e:
            logger.warning(f"Failed to get secret {secret_name} from Secret Manager: {e}")

    # Handle missing required secrets
    if required:
        raise ValueError(f"Required secret {secret_name} not found")

    return None