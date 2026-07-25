"""
M-Pesa Daraja API integration — STK Push, callbacks, and auto-reconciliation.

Config is stored in the mpesa_config DB table (admin-configurable via UI).
Falls back to environment variables if no DB config is set.
"""
import os
import base64
import datetime
import logging
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MpesaConfig, MpesaTransaction, Member, ContributionCause, Contribution
from app.database import async_session

logger = logging.getLogger("mpesa")

# Base URLs
SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"

# Env fallbacks
ENV_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
ENV_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
ENV_PASSKEY = os.environ.get("MPESA_PASSKEY", "")
ENV_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "174379")
ENV_CALLBACK_BASE = os.environ.get("MPESA_CALLBACK_URL", "")
ENV_SANDBOX = os.environ.get("MPESA_SANDBOX", "true").lower() == "true"


class MpesaError(Exception):
    """M-Pesa API error."""


# ── Config helpers ──

async def _get_config() -> dict:
    """Load M-Pesa config from DB, falling back to env vars."""
    try:
        async with async_session() as session:
            cfg = await session.get(MpesaConfig, 1)
            if cfg and cfg.consumer_key:
                base = cfg.callback_url or f"https://kh07-welfare.spidmax.win"
                return {
                    "consumer_key": cfg.consumer_key,
                    "consumer_secret": cfg.consumer_secret,
                    "passkey": cfg.passkey,
                    "shortcode": cfg.shortcode or "174379",
                    "callback_url": base,
                    "api_base": SANDBOX_BASE if cfg.sandbox else PRODUCTION_BASE,
                }
    except Exception as e:
        logger.warning(f"Failed to load M-Pesa config from DB: {e}")

    # Fallback to env vars
    return {
        "consumer_key": ENV_CONSUMER_KEY,
        "consumer_secret": ENV_CONSUMER_SECRET,
        "passkey": ENV_PASSKEY,
        "shortcode": ENV_SHORTCODE,
        "callback_url": ENV_CALLBACK_BASE or "https://kh07-welfare.spidmax.win",
        "api_base": SANDBOX_BASE if ENV_SANDBOX else PRODUCTION_BASE,
    }


def _get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


def _generate_password(shortcode: str, passkey: str, timestamp: str) -> str:
    data = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(data.encode()).decode()


def _format_phone(phone: str) -> str:
    """Normalize phone to 2547XXXXXXXX format."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if phone.startswith("2547") and len(phone) == 12:
        return phone
    raise MpesaError(f"Invalid phone: use 0712345678 or 254712345678")


# ── API Calls ──

async def get_access_token(cfg: dict) -> str:
    """Get OAuth access token from M-Pesa API."""
    ck = cfg.get("consumer_key", "")
    cs = cfg.get("consumer_secret", "")
    if not ck or not cs:
        raise MpesaError("M-Pesa consumer key/secret not configured. Configure them in Admin > M-Pesa Settings.")
    auth_str = base64.b64encode(f"{ck}:{cs}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{cfg['api_base']}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth_str}"},
            timeout=15,
        )
        if resp.status_code != 200:
            raise MpesaError(f"Token request failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json().get("access_token", "")


async def stk_push(phone: str, amount: float, account_ref: str,
                   transaction_desc: str = "KH07 Welfare", cfg: Optional[dict] = None) -> dict:
    """Initiate STK Push (Lipa na M-Pesa Online)."""
    if cfg is None:
        cfg = await _get_config()
    token = await get_access_token(cfg)
    ts = _get_timestamp()
    pw = _generate_password(cfg["shortcode"], cfg["passkey"], ts)

    payload = {
        "BusinessShortCode": cfg["shortcode"],
        "Password": pw,
        "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": str(int(amount)),
        "PartyA": phone,
        "PartyB": cfg["shortcode"],
        "PhoneNumber": phone,
        "CallBackURL": f"{cfg['callback_url'].rstrip('/')}/api/mpesa/callback",
        "AccountReference": account_ref[:12],
        "TransactionDesc": transaction_desc[:13],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{cfg['api_base']}/mpesa/stkpush/v1/processrequest",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            raise MpesaError(f"STK Push failed ({resp.status_code}): {resp.text[:200]}")
        return resp.json()


async def query_status(checkout_request_id: str, cfg: Optional[dict] = None) -> dict:
    """Query the status of an STK Push.
    
    Daraja 3.0 query behavior:
    - Pending (user hasn't acted): HTTP 500 'transaction does not Exist'
    - Completed: HTTP 200 with ResultCode (0=success, other=failure)
    - Network error: connection/read timeout
    
    Returns dict with at minimum {'status': ...} plus result fields.
    Status values: 'pending', 'completed', 'failed', 'retryable_error'
    """
    if cfg is None:
        cfg = await _get_config()
    
    try:
        token = await get_access_token(cfg)
    except MpesaError:
        raise  # config missing — propagate up
    except Exception as e:
        return {"status": "retryable_error", "error": f"Auth failed: {str(e)}"}

    ts = _get_timestamp()
    pw = _generate_password(cfg["shortcode"], cfg["passkey"], ts)

    payload = {
        "BusinessShortCode": cfg["shortcode"],
        "Password": pw,
        "Timestamp": ts,
        "CheckoutRequestID": checkout_request_id,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{cfg['api_base']}/mpesa/stkpushquery/v1/query",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=15,
            )
    except httpx.TimeoutException:
        return {"status": "retryable_error", "error": "Query timed out — network issue"}
    except Exception as e:
        return {"status": "retryable_error", "error": f"Request failed: {str(e)}"}

    # HTTP 500 with "does not exist" = transaction still pending
    if resp.status_code == 500:
        body = resp.text[:300]
        if "does not exist" in body.lower() or "does not Exist" in body:
            return {"status": "pending", "ResultCode": None, "ResultDesc": "Waiting for user to enter PIN"}
        # Other 500 = real error
        return {"status": "retryable_error", "error": f"API error (500): {body}"}

    if resp.status_code != 200:
        return {"status": "retryable_error", "error": f"Unexpected HTTP {resp.status_code}"}

    # HTTP 200 — parse result
    try:
        data = resp.json()
    except Exception:
        return {"status": "retryable_error", "error": "Invalid JSON response"}

    rc = data.get("ResultCode")
    if rc is None:
        return {"status": "retryable_error", "error": "Missing ResultCode in response"}

    # Determine status from Daraja 3.0 ResultCode
    rc_str = str(rc)
    
    # Map Daraja 3.0 result codes to our status
    if rc_str == "0":
        data["_status"] = "completed"
    elif rc_str == "1032":
        data["_status"] = "cancelled"     # User cancelled on phone
    elif rc_str == "1037":
        data["_status"] = "timeout"       # STK Push timed out
    elif rc_str == "4999":
        data["_status"] = "pending"       # Still processing, keep polling
    else:
        data["_status"] = "failed"        # 1, 2, 17, 26, 2001, etc.
    
    data["ResultCode"] = rc_str
    return data


# ── DB transaction logging ──

async def log_transaction(session: AsyncSession, checkout_id: str, merchant_id: str,
                          member_id: int, cause_id: int, amount: float,
                          phone: str, account_ref: str) -> MpesaTransaction:
    """Create a pending transaction record."""
    tx = MpesaTransaction(
        checkout_request_id=checkout_id,
        merchant_request_id=merchant_id,
        member_id=member_id,
        cause_id=cause_id,
        amount=amount,
        phone=phone,
        account_ref=account_ref,
        status="pending",
    )
    session.add(tx)
    await session.commit()
    return tx


async def update_transaction(session: AsyncSession, checkout_id: str, *,
                             status: str = "", result_code: str = "",
                             result_desc: str = "", receipt: str = ""):
    """Update a transaction record from callback data."""
    tx = await session.execute(
        select(MpesaTransaction).where(MpesaTransaction.checkout_request_id == checkout_id)
    )
    tx = tx.scalar_one_or_none()
    if not tx:
        logger.warning(f"Transaction not found: {checkout_id}")
        return
    if status:
        tx.status = status
    if result_code:
        tx.result_code = result_code
    if result_desc:
        tx.result_desc = result_desc[:500]
    if receipt:
        tx.receipt = receipt
    await session.commit()


async def reconcile_from_callback(session: AsyncSession, checkout_id: str,
                                  amount: float, receipt: str, phone: str):
    """Auto-record a Contribution when M-Pesa callback confirms payment."""
    tx = await session.execute(
        select(MpesaTransaction).where(MpesaTransaction.checkout_request_id == checkout_id)
    )
    tx = tx.scalar_one_or_none()
    if not tx:
        return

    # Guard: only reconcile if still pending (prevents race-condition duplicates)
    if tx.status != "pending":
        logger.info(f"Transaction {checkout_id} already reconciled (status={tx.status})")
        return

    # Mark as processing to block concurrent callbacks
    tx.status = "success"
    tx.receipt = receipt
    tx.result_code = "0"
    await session.flush()  # persist status change so concurrent callbacks see it

    # Check if contribution was already recorded for this receipt
    existing = await session.execute(
        select(Contribution).where(Contribution.transaction_ref == receipt)
    )
    if existing.scalar_one_or_none():
        logger.info(f"Contribution already recorded for receipt {receipt}")
        await session.commit()
        return

    # Auto-record contribution
    member_id = tx.member_id
    cause_id = tx.cause_id

    if member_id and cause_id:
        contrib = Contribution(
            member_id=member_id,
            cause_id=cause_id,
            amount=amount,
            payment_method="mpesa",
            transaction_ref=receipt,
        )
        session.add(contrib)

    await session.commit()
