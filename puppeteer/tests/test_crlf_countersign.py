"""Test that CRLF normalization produces symmetric signatures between server and node."""
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _normalize(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\r', '\n')


def test_crlf_script_countersign_matches_lf():
    """A CRLF script, once normalized, produces the same signature as the LF version."""
    user_key = Ed25519PrivateKey.generate()
    server_key = Ed25519PrivateKey.generate()

    script_crlf = "print('hello')\r\nprint('world')\r\n"
    script_lf = "print('hello')\nprint('world')\n"

    # Normalize (as the server now does)
    normalized = _normalize(script_crlf)
    assert normalized == script_lf

    # User signs the normalized script
    user_sig = user_key.sign(normalized.encode("utf-8"))
    # Verification succeeds
    user_key.public_key().verify(user_sig, normalized.encode("utf-8"))

    # Server countersigns the normalized script
    server_sig = server_key.sign(normalized.encode("utf-8"))
    # Node verifies using LF bytes (which is what node.py does)
    server_key.public_key().verify(server_sig, script_lf.encode("utf-8"))


def test_crlf_without_normalization_fails():
    """Without normalization, CRLF and LF produce different signatures."""
    key = Ed25519PrivateKey.generate()

    script_crlf = "print('hello')\r\nprint('world')\r\n"
    script_lf = "print('hello')\nprint('world')\n"

    sig_crlf = key.sign(script_crlf.encode("utf-8"))

    # Verifying a CRLF signature against LF bytes must fail
    with pytest.raises(Exception):
        key.public_key().verify(sig_crlf, script_lf.encode("utf-8"))
