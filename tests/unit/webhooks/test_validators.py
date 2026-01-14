"""Tests for webhook validators."""

import hmac
import hashlib
import pytest

from mcp_k3s_monitor.webhooks.validators import validate_github_signature


def test_valid_signature():
    """Test validation of a valid GitHub signature."""
    secret = "test-secret"
    payload = b'{"test": "data"}'

    # Generate valid signature
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    signature = f"sha256={mac.hexdigest()}"

    # Validate
    assert validate_github_signature(payload, signature, secret) is True


def test_invalid_signature():
    """Test rejection of an invalid GitHub signature."""
    secret = "test-secret"
    payload = b'{"test": "data"}'

    # Generate invalid signature
    signature = "sha256=invalid_signature_here"

    # Validate
    assert validate_github_signature(payload, signature, secret) is False


def test_missing_signature():
    """Test rejection when signature is missing."""
    secret = "test-secret"
    payload = b'{"test": "data"}'

    assert validate_github_signature(payload, "", secret) is False
    assert validate_github_signature(payload, None, secret) is False


def test_wrong_secret():
    """Test rejection when wrong secret is used."""
    secret = "correct-secret"
    wrong_secret = "wrong-secret"
    payload = b'{"test": "data"}'

    # Generate signature with correct secret
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    signature = f"sha256={mac.hexdigest()}"

    # Validate with wrong secret
    assert validate_github_signature(payload, signature, wrong_secret) is False


def test_invalid_signature_format():
    """Test rejection of invalid signature format."""
    secret = "test-secret"
    payload = b'{"test": "data"}'

    # Signature without sha256= prefix
    signature = "invalid_format_here"

    assert validate_github_signature(payload, signature, secret) is False
