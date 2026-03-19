"""
CapitalMind — S3 Upload Utility.
Uploads final reports and documents to AWS S3.
"""
from __future__ import annotations
import json
from typing import Any


async def upload_report(
    report: dict[str, Any],
    ticker: str,
    run_id: str,
) -> str:
    """
    Upload a final report to S3.
    Returns the S3 URI of the uploaded report.
    """
    # In production: use boto3 async to upload JSON to S3
    s3_key = f"reports/{ticker}/{run_id}.json"
    s3_uri = f"s3://capitalmind-reports/{s3_key}"
    return s3_uri
