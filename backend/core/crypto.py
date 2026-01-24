import base64, secrets, struct
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

PBKDF2_ITERATIONS = 390000


def derive_fernet_key_from_password(password: str, salt: bytes):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERATIONS
    )
    key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def fernet_from_password(password: str, salt: bytes):
    return Fernet(derive_fernet_key_from_password(password, salt))


def encrypt_and_make_payload(
    message_bytes: bytes, password: str, magic: bytes
) -> bytes:

    salt = secrets.token_bytes(16)
    f = fernet_from_password(password, salt)
    encrypted = f.encrypt(message_bytes)
    return magic + salt + struct.pack(">I", len(encrypted)) + encrypted
