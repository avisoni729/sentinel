"""Offline tests for the GitHub App's webhook signature verification."""
import hashlib
import hmac

from sentinel.github_app import verify_signature

SECRET = "topsecret"
BODY = b'{"action":"opened"}'


def _sig(secret, body):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_passes():
    assert verify_signature(SECRET, BODY, _sig(SECRET, BODY)) is True


def test_tampered_body_fails():
    assert verify_signature(SECRET, b'{"action":"closed"}', _sig(SECRET, BODY)) is False


def test_wrong_secret_fails():
    assert verify_signature("other", BODY, _sig(SECRET, BODY)) is False


def test_missing_signature_fails():
    assert verify_signature(SECRET, BODY, None) is False
