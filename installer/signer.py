"""Signer — SHA-256 checksums and RSA-PSS digital signatures.

Requires: pip install cryptography
"""
from __future__ import annotations

import hashlib
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa, utils

    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file (streaming, handles large files)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_keypair(output_dir: Path) -> tuple[Path, Path]:
    """
    Generate an RSA-4096 key pair and write PEM files to *output_dir*.

    Returns:
        (private_key_path, public_key_path)
    """
    _require_crypto()
    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    priv_path = output_dir / "private.pem"
    pub_path = output_dir / "public.pem"

    priv_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return priv_path, pub_path


def sign_file(file_path: Path, private_key_path: Path) -> bytes:
    """
    Compute an RSA-PSS signature over the SHA-256 digest of *file_path*.

    The digest is pre-computed so the full file is never loaded into memory.
    """
    _require_crypto()
    key_data = private_key_path.read_bytes()
    private_key = serialization.load_pem_private_key(key_data, password=None)

    digest_bytes = bytes.fromhex(sha256_file(file_path))
    return private_key.sign(  # type: ignore[union-attr]
        digest_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        utils.Prehashed(hashes.SHA256()),
    )


def verify_file(file_path: Path, signature: bytes, public_key_path: Path) -> bool:
    """
    Verify an RSA-PSS signature against the SHA-256 digest of *file_path*.

    Returns True if the signature is valid, False otherwise.
    """
    _require_crypto()
    key_data = public_key_path.read_bytes()
    public_key = serialization.load_pem_public_key(key_data)

    digest_bytes = bytes.fromhex(sha256_file(file_path))
    try:
        public_key.verify(  # type: ignore[union-attr]
            signature,
            digest_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            utils.Prehashed(hashes.SHA256()),
        )
        return True
    except Exception:
        return False


def _require_crypto() -> None:
    if not _CRYPTO_OK:
        raise RuntimeError(
            "The 'cryptography' package is required for RSA operations.\n"
            "Install it: pip install cryptography"
        )
