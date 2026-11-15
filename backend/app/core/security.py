"""
智慧学伴 安全工具模块
JWT Token 生成/验证、密码哈希、AES-256 加密
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    """
    对密码进行 bcrypt 哈希

    bcrypt 限制密码长度 <= 72 字节，超长密码自动截断

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    password_bytes = password.encode("utf-8")
    # bcrypt 限制 72 字节
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        bool: 是否匹配
    """
    plain_bytes = plain_password.encode("utf-8")
    if len(plain_bytes) > 72:
        plain_bytes = plain_bytes[:72]
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hash_bytes)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    生成 JWT Access Token

    Args:
        data: Token 载荷数据，通常包含 sub(用户ID)、role、tenant_id
        expires_delta: 自定义过期时间增量

    Returns:
        str: 编码后的 JWT Token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "type": "access",
    })
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    生成 JWT Refresh Token

    Args:
        data: Token 载荷数据，通常包含 sub(用户ID)
        expires_delta: 自定义过期时间增量

    Returns:
        str: 编码后的 JWT Refresh Token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({
        "exp": expire,
        "type": "refresh",
    })
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码并验证 JWT Access Token

    Args:
        token: JWT Token 字符串

    Returns:
        Optional[Dict]: Token 载荷数据，验证失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_sub": False},  # sub 可能是 int，跳过类型验证
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码并验证 JWT Refresh Token

    Args:
        token: JWT Refresh Token 字符串

    Returns:
        Optional[Dict]: Token 载荷数据，验证失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_sub": False},  # sub 可能是 int，跳过类型验证
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


# ============ AES-256 加密工具 ============

import base64
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def _derive_aes_key(secret: str) -> bytes:
    """
    从密钥字符串派生 AES-256 密钥（32字节）

    Args:
        secret: 密钥字符串

    Returns:
        bytes: 32字节 AES 密钥
    """
    return hashlib.sha256(secret.encode()).digest()


def aes_encrypt(plaintext: str, secret: Optional[str] = None) -> str:
    """
    AES-256-CBC 加密

    Args:
        plaintext: 明文
        secret: 加密密钥，默认使用应用 SECRET_KEY

    Returns:
        str: Base64 编码的密文（包含 IV 前缀）
    """
    import os

    key = _derive_aes_key(secret or settings.SECRET_KEY)
    iv = os.urandom(16)  # AES 块大小 16 字节

    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend(),
    )
    encryptor = cipher.encryptor()

    # PKCS7 填充
    plaintext_bytes = plaintext.encode("utf-8")
    pad_length = 16 - (len(plaintext_bytes) % 16)
    padded = plaintext_bytes + bytes([pad_length] * pad_length)

    ciphertext = encryptor.update(padded) + encryptor.finalize()

    # 返回 IV + 密文的 Base64 编码
    return base64.b64encode(iv + ciphertext).decode("utf-8")


def aes_decrypt(encrypted: str, secret: Optional[str] = None) -> str:
    """
    AES-256-CBC 解密

    Args:
        encrypted: Base64 编码的密文（包含 IV 前缀）
        secret: 解密密钥，默认使用应用 SECRET_KEY

    Returns:
        str: 解密后的明文
    """
    key = _derive_aes_key(secret or settings.SECRET_KEY)
    raw = base64.b64decode(encrypted)

    iv = raw[:16]
    ciphertext = raw[16:]

    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()

    padded = decryptor.update(ciphertext) + decryptor.finalize()

    # 移除 PKCS7 填充
    pad_length = padded[-1]
    plaintext_bytes = padded[:-pad_length]

    return plaintext_bytes.decode("utf-8")
