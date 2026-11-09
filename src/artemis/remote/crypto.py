"""End-to-end encryption for the remote plane.

The edge (a relay in the cloud) carries bytes between a device and this computer. It must
not be able to read them, so the keys are made between the two ends and never pass through
the edge. The pairing code is mixed into the key and is never sent to the edge in a usable
form, so an edge that swaps the public keys in transit ends up with a key that does not match.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

#: No ambiguous characters (0/O, 1/I), so a code can be read out loud or typed from a screen.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class CryptoError(Exception):
    """A frame could not be opened: wrong key, damaged, or replayed."""


def new_pairing_code(length: int = 10) -> str:
    """About 50 bits. Long enough that the edge cannot guess it from what it sees."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def new_keypair() -> tuple[X25519PrivateKey, bytes]:
    private = X25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return private, public


def shared_secret(private: X25519PrivateKey, peer_public: bytes) -> bytes:
    return private.exchange(X25519PublicKey.from_public_bytes(peer_public))


def derive(secret: bytes, info: bytes, salt: bytes = b"", length: int = 32) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt or None, info=info).derive(
        secret
    )


def code_proof(code: str) -> str:
    """What a device shows the edge to prove it holds the code.

    It is derived one way from the code, so the edge can check it without learning the
    code, and cannot use it to build the key.
    """
    return hashlib.sha256(b"artemis-edge-proof|" + code.encode()).hexdigest()


def pairing_key(secret: bytes, code: str) -> bytes:
    """The key both ends reach at pairing. Needs the code as well as the key exchange."""
    return derive(secret, b"artemis-pairing", salt=code.encode())


def safety_number(secret: bytes, code: str) -> str:
    """Six digits both screens show, so the owner can see the two ends agree."""
    digest = derive(secret, b"artemis-safety-number", salt=code.encode(), length=4)
    return f"{int.from_bytes(digest, 'big') % 1_000_000:06d}"


def device_secret(pair_key: bytes) -> bytes:
    return derive(pair_key, b"artemis-device-secret")


def session_key(device_key: bytes, host_nonce: bytes, device_nonce: bytes) -> bytes:
    return derive(device_key, b"artemis-session", salt=host_nonce + device_nonce)


def session_proof(device_key: bytes, host_nonce: bytes, device_nonce: bytes) -> str:
    """A device shows this to the edge to open a session, without sending any key."""
    return hmac.new(device_key, b"edge|" + host_nonce + device_nonce, hashlib.sha256).hexdigest()


class Channel:
    """One direction pair of an encrypted link. Frames carry a counter, so none can be replayed.

    `send_side` and `recv_side` are single bytes that differ between the two ends, so a
    frame sent by one end can never be mistaken for one sent by the other.
    """

    def __init__(self, key: bytes, send_side: bytes, recv_side: bytes) -> None:
        self._aead = AESGCM(key)  # AES-256-GCM: also built into every browser
        self._send_side = send_side
        self._recv_side = recv_side
        self._sent = 0
        self._received = -1

    def seal(self, plaintext: bytes) -> bytes:
        counter = self._sent
        self._sent += 1
        nonce = self._send_side * 4 + struct.pack(">Q", counter)
        return struct.pack(">Q", counter) + self._aead.encrypt(nonce, plaintext, None)

    def open(self, frame: bytes) -> bytes:
        if len(frame) < 8 + 16:
            raise CryptoError("That message was damaged.")
        (counter,) = struct.unpack(">Q", frame[:8])
        if counter <= self._received:
            raise CryptoError("That message was already received.")
        nonce = self._recv_side * 4 + struct.pack(">Q", counter)
        try:
            plaintext = self._aead.decrypt(nonce, frame[8:], None)
        except InvalidTag as exc:
            raise CryptoError("That message could not be opened.") from exc
        self._received = counter
        return plaintext
