"""
RationSmart - Centralized Secure Audit Logging Service
Provides server-side, tamper-resistant, append-only activity tracking
for authentication, administrative actions, dealer operations, and billing.
"""

import os
import re
import json
import uuid
import logging
from datetime import datetime
from flask import request, has_request_context
from flask_login import current_user
from models import db, AuditLog

logger = logging.getLogger('rationsmart.audit')

# Sensitive keys that must NEVER be written to the audit log
EXCLUDED_SENSITIVE_KEYS = {
    'password', 'password_hash', 'pass', 'pwd', 'secret', 'secret_key',
    'token', 'auth_token', 'session_id', 'cookie', 'api_key', 'private_key',
    'connection_string', 'database_uri', 'db_url', 'csrf_token'
}

def sanitize_value(key, value):
    """
    Sanitize values to ensure sensitive credentials, passwords, tokens,
    control characters, or raw payloads are never leaked into audit records.
    """
    key_str = str(key).lower()
    if any(sens in key_str for sens in EXCLUDED_SENSITIVE_KEYS):
        return "[REDACTED]"
    
    if isinstance(value, str):
        # Prevent log injection (newlines, null bytes, ASCII control codes)
        cleaned = re.sub(r'[\r\n\x00-\x1f\x7f]', ' ', value)
        return cleaned[:500]
    
    if isinstance(value, dict):
        return {k: sanitize_value(k, v) for k, v in value.items()}
    
    if isinstance(value, (list, tuple)):
        return [sanitize_value(key, item) if isinstance(item, (dict, list, tuple, str)) else item for item in value]
        
    return value

def escape_csv_value(val):
    """
    Prevent Spreadsheet Formula Injection (CSV injection).
    If a cell begins with '=', '+', '-', '@', tab, or carriage return,
    prefix with a single quote so spreadsheet applications treat it as safe text.
    """
    if val is None:
        return ""
    s = str(val).strip()
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s

def log_audit_event(
    action,
    entity_type,
    entity_id=None,
    shop_id=None,
    outcome='SUCCESS',
    reason=None,
    changes=None,
    actor_user=None,
    actor_user_id=None,
    actor_identifier=None,
    actor_role=None,
    request_id=None,
    commit=True
):
    """
    Record an append-only audit event.
    
    Parameters:
      - action (str): Standardized action code (e.g. 'AUTH_LOGIN_SUCCESS', 'BILL_CREATED')
      - entity_type (str): Type of record (e.g. 'Bill', 'Stock', 'Customer', 'Shop')
      - entity_id (str|int): Affected record ID
      - shop_id (int): Fair Price Shop ID context
      - outcome (str): 'SUCCESS', 'FAILURE', or 'DENIED'
      - reason (str): Safe description or rejection reason
      - changes (dict): Structured before/after diffs of approved non-sensitive fields
      - actor_user (User): Explicit user object (defaults to current_user if authenticated)
      - actor_user_id (int): Explicit actor user ID
      - actor_identifier (str): Safe username or identifier if actor is unauthenticated
      - actor_role (str): Safe role override (e.g. 'Anonymous')
      - commit (bool): If False, the record is added to db.session without committing,
                       enabling atomic commit/rollback with business transactions.
    """
    try:
        # 1. Resolve Actor Context from trusted server session
        resolved_actor_user_id = actor_user_id
        if actor_user:
            resolved_actor_user_id = actor_user.id
            actor_role = actor_role or actor_user.role
            actor_identifier = actor_identifier or actor_user.username
            if not shop_id and getattr(actor_user, 'shop_id', None):
                shop_id = actor_user.shop_id
        elif current_user and getattr(current_user, 'is_authenticated', False):
            resolved_actor_user_id = resolved_actor_user_id or current_user.id
            actor_role = actor_role or current_user.role
            actor_identifier = actor_identifier or current_user.username
            if not shop_id and getattr(current_user, 'shop_id', None):
                shop_id = current_user.shop_id
        else:
            actor_role = actor_role or 'Anonymous'
            actor_identifier = actor_identifier or 'Unauthenticated'

        actor_user_id = resolved_actor_user_id

        # 2. Extract network context safely if in Flask request
        ip_address = None
        if has_request_context():
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            if not request_id:
                request_id = request.headers.get('X-Request-ID')

        # 3. Server-generated event ID
        event_id = f"AUD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

        # 4. Safe serialization of before/after changes
        changes_json = None
        if changes:
            sanitized_changes = sanitize_value('changes', changes)
            changes_json = json.dumps(sanitized_changes)

        # 5. Sanitize reason string
        clean_reason = None
        if reason:
            clean_reason = re.sub(r'[\r\n\x00-\x1f\x7f]', ' ', str(reason))[:500]

        # 6. Instantiate AuditLog entry
        entry = AuditLog(
            event_id=event_id,
            actor_user_id=actor_user_id,
            actor_role=str(actor_role)[:32],
            actor_identifier=str(actor_identifier)[:128],
            action=str(action)[:64],
            entity_type=str(entity_type)[:64],
            entity_id=str(entity_id)[:64] if entity_id is not None else None,
            shop_id=shop_id,
            timestamp=datetime.utcnow(),
            outcome=str(outcome)[:16],
            reason=clean_reason,
            changes=changes_json,
            request_id=str(request_id)[:64] if request_id else None,
            ip_address=str(ip_address)[:64] if ip_address else None
        )

        db.session.add(entry)
        if commit:
            db.session.commit()
            
        return entry

    except Exception as exc:
        logger.error(f"Audit log recording error: {exc}", exc_info=True)
        if commit:
            try:
                db.session.rollback()
            except Exception:
                pass
        return None
