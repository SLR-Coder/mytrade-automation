# -*- coding: utf-8 -*-
"""
Cloud Storage utilities for MyTrade
Handles chart uploads and URL generation
"""

import os
import logging
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MyTrade-Storage")


class StorageClient:
    """
    Cloud Storage client for uploading and managing chart files

    Falls back to local storage if Cloud Storage is not available
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        local_dir: str = "/tmp/charts"
    ):
        """
        Initialize storage client

        Args:
            bucket_name: GCS bucket name (if None, uses local storage)
            local_dir: Local directory for fallback
        """
        self.bucket_name = bucket_name
        self.local_dir = local_dir
        self.use_gcs = bucket_name and GCS_AVAILABLE

        if self.use_gcs:
            try:
                self.gcs_client = storage.Client()
                self.bucket = self.gcs_client.bucket(bucket_name)
                logger.info(f"✅ Cloud Storage initialized: gs://{bucket_name}")
            except Exception as e:
                logger.warning(f"Cloud Storage init failed: {e}, falling back to local")
                self.use_gcs = False

        if not self.use_gcs:
            # Ensure local directory exists
            Path(local_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Local storage initialized: {local_dir}")

    def upload_chart(
        self,
        local_path: str,
        market: str,
        make_public: bool = True
    ) -> Optional[str]:
        """
        Upload chart to Cloud Storage or copy to local storage

        Args:
            local_path: Path to local chart file
            market: Market symbol (e.g., "BTC/USDT")
            make_public: Make file publicly accessible

        Returns:
            Public URL to the chart or local path
        """
        if not os.path.exists(local_path):
            logger.error(f"Chart file not found: {local_path}")
            return None

        # Generate remote path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_market = market.replace("/", "_")
        remote_filename = f"charts/{timestamp}_{safe_market}.png"

        if self.use_gcs:
            try:
                # Upload to GCS
                blob = self.bucket.blob(remote_filename)
                blob.upload_from_filename(local_path, content_type="image/png")

                if make_public:
                    blob.make_public()
                    url = blob.public_url
                else:
                    # Generate signed URL (valid for 1 hour)
                    url = blob.generate_signed_url(
                        expiration=timedelta(hours=1),
                        method="GET"
                    )

                logger.info(f"✓ Chart uploaded to GCS: {remote_filename}")
                return url

            except Exception as e:
                logger.error(f"GCS upload failed: {e}")
                return None
        else:
            # Local storage - just return the local path
            logger.info(f"✓ Chart saved locally: {local_path}")
            return f"file://{local_path}"

    def delete_old_charts(self, days: int = 7):
        """
        Delete charts older than specified days

        Args:
            days: Delete files older than this many days
        """
        if self.use_gcs:
            try:
                cutoff_date = datetime.now() - timedelta(days=days)

                # List and delete old blobs
                blobs = self.bucket.list_blobs(prefix="charts/")
                deleted = 0

                for blob in blobs:
                    if blob.time_created < cutoff_date:
                        blob.delete()
                        deleted += 1

                logger.info(f"✓ Deleted {deleted} old charts from GCS")

            except Exception as e:
                logger.error(f"Failed to delete old charts: {e}")
        else:
            # Local cleanup
            try:
                local_path = Path(self.local_dir)
                cutoff_time = datetime.now().timestamp() - (days * 86400)
                deleted = 0

                for file_path in local_path.glob("*.png"):
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        deleted += 1

                logger.info(f"✓ Deleted {deleted} old charts from local storage")

            except Exception as e:
                logger.error(f"Failed to delete old local charts: {e}")

    def list_charts(self, limit: int = 100) -> list:
        """
        List recent charts

        Args:
            limit: Maximum number of charts to return

        Returns:
            List of chart URLs or paths
        """
        charts = []

        if self.use_gcs:
            try:
                blobs = self.bucket.list_blobs(prefix="charts/", max_results=limit)
                for blob in blobs:
                    if blob.public_url:
                        charts.append(blob.public_url)
            except Exception as e:
                logger.error(f"Failed to list GCS charts: {e}")
        else:
            # List local files
            try:
                local_path = Path(self.local_dir)
                for file_path in sorted(local_path.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
                    charts.append(f"file://{file_path}")
            except Exception as e:
                logger.error(f"Failed to list local charts: {e}")

        return charts


def get_storage_client(bucket_name: Optional[str] = None) -> StorageClient:
    """
    Get storage client instance

    Args:
        bucket_name: GCS bucket name (from env if not provided)

    Returns:
        StorageClient instance
    """
    if bucket_name is None:
        bucket_name = os.getenv("STORAGE_BUCKET")

    return StorageClient(bucket_name=bucket_name)


if __name__ == "__main__":
    # Test storage client
    import sys

    storage = get_storage_client()

    if len(sys.argv) > 1:
        # Test upload
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            url = storage.upload_chart(test_file, "TEST/MARKET")
            print(f"Uploaded: {url}")
        else:
            print(f"File not found: {test_file}")
    else:
        # List charts
        charts = storage.list_charts(limit=10)
        print(f"Found {len(charts)} charts:")
        for chart in charts:
            print(f"  - {chart}")