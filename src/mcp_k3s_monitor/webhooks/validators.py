"""GitHub webhook validation utilities."""

import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)


def validate_github_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Validate GitHub webhook signature.

    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret

    Returns:
        True if signature is valid
    """
    if not signature:
        logger.warning("No signature provided")
        return False

    # GitHub sends: sha256=<hex_digest>
    if not signature.startswith("sha256="):
        logger.warning("Invalid signature format")
        return False

    expected_signature = signature[7:]  # Remove "sha256=" prefix

    # Compute HMAC
    mac = hmac.new(
        secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    computed_signature = mac.hexdigest()

    # Constant-time comparison
    is_valid = hmac.compare_digest(computed_signature, expected_signature)

    if not is_valid:
        logger.warning("Signature validation failed")

    return is_valid
