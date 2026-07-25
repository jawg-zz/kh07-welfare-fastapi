"""
M-Pesa Daraja API integration — STK Push, callbacks, and auto-reconciliation.

Requires:
- TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars (for sending
  payment success notifications to the admin)
"""
import os
import json
import base64
import hashlib
import datetime
from typing import Optional

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# ── Configuration ──
# These should be set via the admin settings UI (stored in mpesa_config table)
# or via environment variables
CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
PASSKEY = os.environ.get("MPESA_PASSKEY", "")
SHORTCODE = os.environ.get("MPESA_SHORTCODE", "174379")  # Default test shortcode
CALLBACK_BASE = os.environ.get("MPESA_CALLBACK_URL", "https://kh07-welfare.spidmax.win")

# Base URLs
SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"
USE_SANDBOX = os.environ.get("MPESA_SANDBOX", "true").lower() == "true"
API_BASE = SANDBOX_BASE if USE_SANDBOX else PRODUCTION_BASE


class MpesaError(Exception):
    """M-Pesa API error."""


def _get_timestamp() -> str:
    """Get timestamp in YYYYMMDDHHmmss format."""
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


def _generate_password(shortcode: str, passkey: str, timestamp: str) -> str:
    """Generate the base64-encoded password for STK Push."""
    data = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(data.encode()).decode()


async def get_access_token() -> str:
    """Get OAuth access token from M-Pesa API."""
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        raise MpesaError("M-Pesa consumer key/secret not configured. Set MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET.")

    auth_str = base64.b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_str}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/oauth/v1/generate?grant_type=client_credentials", headers=headers, timeout=15)
        if resp.status_code != 200:
            raise MpesaError(f"Failed to get access token: {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        return data.get("access_token", "")


async def stk_push(
    phone: str,
    amount: float,
    account_ref: str,
    transaction_desc: str = "KH07 Welfare Contribution",
) -> dict:
    """
    Initiate an STK Push (Lipa na M-Pesa Online) request.

    Args:
        phone: Phone number in format 2547XXXXXXXX
        amount: Amount to charge
        account_ref: Account reference (e.g. member number)
        transaction_desc: Description of the transaction

    Returns:
        Response dict from the API
    """
    token = await get_access_token()
    timestamp = _get_timestamp()
    password = _generate_password(SHORTCODE, PASSKEY, timestamp)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": str(int(amount)),
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": f"{CALLBACK_BASE}/api/mpesa/callback",
        "AccountReference": account_ref[:12],  # Max 12 chars
        "TransactionDesc": transaction_desc[:13],  # Max 13 chars
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/mpesa/stkpush/v1/processrequest",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            raise MpesaError(f"STK Push failed: {resp.status_code} {resp.text[:200]}")
        return resp.json()


async def query_status(checkout_request_id: str) -> dict:
    """Query the status of an STK Push request."""
    token = await get_access_token()
    timestamp = _get_timestamp()
    password = _generate_password(SHORTCODE, PASSKEY, timestamp)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/mpesa/stkpushquery/v1/query",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if resp.status_code != 200:
            raise MpesaError(f"Query failed: {resp.status_code} {resp.text[:200]}")
        return resp.json()
