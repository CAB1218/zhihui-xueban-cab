"""
智慧学伴 数据加密模块
AES-256-CBC 加密 + PBKDF2 密钥派生 + 敏感字段加密
"""
import base64
import hashlib
import os
import json
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from app.config import settings


# ============ PBKDF2 密钥派生 ============

PBKDF2_ITERATIONS = 600_000  # OWASP 2023 推荐
SALT_LENGTH = 32  # 盐值长度 32 字节
AES_KEY_LENGTH = 32  # AES-256 需要 32 字节密钥


def derive_key_pbkdf2(
    password: str,
    salt: Optional[bytes] = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> tuple[bytes, bytes]:
    """
    使用 PBKDF2-HMAC-SHA256 从密码派生密钥

    Args:
        password: 原始密码/密钥字符串
        salt: 盐值，None 时自动生成
        iterations: 迭代次数

    Returns:
        tuple[bytes, bytes]: (派生密钥32字节, 盐值)
    """
    if salt is None:
        salt = os.urandom(SALT_LENGTH)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_LENGTH,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    key = kdf.derive(password.encode("utf-8"))
    return key, salt


def hash_password_pbkdf2(password: str) -> str:
    """
    使用 PBKDF2 对密码进行哈希（用于非 bcrypt 场景的补充）

    Args:
        password: 明文密码

    Returns:
        str: 格式为 iterations$salt_base64$hash_base64
    """
    salt = os.urandom(SALT_LENGTH)
    key, _ = derive_key_pbkdf2(password, salt)

    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(key).decode("utf-8")

    return f"{PBKDF2_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password_pbkdf2(password: str, stored_hash: str) -> bool:
    """
    验证 PBKDF2 哈希的密码

    Args:
        password: 待验证的明文密码
        stored_hash: 存储的哈希值 (iterations$salt$hash)

    Returns:
        bool: 是否匹配
    """
    try:
        parts = stored_hash.split("$")
        if len(parts) != 3:
            return False

        iterations = int(parts[0])
        salt = base64.b64decode(parts[1])
        stored_key = base64.b64decode(parts[2])

        derived_key, _ = derive_key_pbkdf2(password, salt, iterations)
        return derived_key == stored_key
    except Exception:
        return False


# ============ AES-256-CBC 加密（PBKDF2 密钥派生） ============


def encrypt_field(plaintext: str, secret: Optional[str] = None) -> str:
    """
    使用 AES-256-CBC 加密敏感字段（如手机号、身份证等）

    加密流程：
    1. 使用 PBKDF2 从密钥字符串派生 32 字节密钥
    2. 生成随机 16 字节 IV
    3. AES-CBC 加密 + PKCS7 填充
    4. 返回 salt(32) + iv(16) + ciphertext 的 Base64 编码

    Args:
        plaintext: 明文
        secret: 加密密钥，默认使用应用 SECRET_KEY

    Returns:
        str: Base64 编码的密文
    """
    if not plaintext:
        return plaintext

    # PBKDF2 密钥派生
    key, salt = derive_key_pbkdf2(secret or settings.SECRET_KEY)

    # 生成随机 IV
    iv = os.urandom(16)

    # AES-CBC 加密
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # PKCS7 填充
    plaintext_bytes = plaintext.encode("utf-8")
    pad_length = 16 - (len(plaintext_bytes) % 16)
    padded = plaintext_bytes + bytes([pad_length] * pad_length)

    ciphertext = encryptor.update(padded) + encryptor.finalize()

    # 拼接 salt + iv + ciphertext
    combined = salt + iv + ciphertext
    return base64.b64encode(combined).decode("utf-8")


def decrypt_field(encrypted: str, secret: Optional[str] = None) -> str:
    """
    使用 AES-256-CBC 解密敏感字段

    Args:
        encrypted: Base64 编码的密文
        secret: 解密密钥，默认使用应用 SECRET_KEY

    Returns:
        str: 解密后的明文
    """
    if not encrypted:
        return encrypted

    raw = base64.b64decode(encrypted)

    # 提取 salt(32) + iv(16) + ciphertext
    salt = raw[:SALT_LENGTH]
    iv = raw[SALT_LENGTH:SALT_LENGTH + 16]
    ciphertext = raw[SALT_LENGTH + 16:]

    # PBKDF2 密钥派生（使用存储的 salt）
    key, _ = derive_key_pbkdf2(secret or settings.SECRET_KEY, salt)

    # AES-CBC 解密
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    padded = decryptor.update(ciphertext) + decryptor.finalize()

    # 移除 PKCS7 填充
    pad_length = padded[-1]
    plaintext_bytes = padded[:-pad_length]

    return plaintext_bytes.decode("utf-8")


# ============ 敏感数据加密工具 ============


class SensitiveFieldEncryptor:
    """
    敏感字段加密器

    用于自动加密/解解模型中的敏感字段（手机号、身份证等）
    在存储前加密，读取后解密
    """

    # 需要加密的字段名
    SENSITIVE_FIELDS = {"phone", "id_card", "address", "emergency_contact"}

    @classmethod
    def encrypt_model(cls, data: dict, fields: Optional[set[str]] = None) -> dict:
        """
        加密模型数据中的敏感字段

        Args:
            data: 原始数据字典
            fields: 要加密的字段集合，默认使用 SENSITIVE_FIELDS

        Returns:
            dict: 加密后的数据
        """
        target_fields = fields or cls.SENSITIVE_FIELDS
        result = data.copy()

        for field in target_fields:
            value = result.get(field)
            if value and isinstance(value, str):
                result[field] = encrypt_field(value)
                result[f"{field}_encrypted"] = True

        return result

    @classmethod
    def decrypt_model(cls, data: dict, fields: Optional[set[str]] = None) -> dict:
        """
        解密模型数据中的敏感字段

        Args:
            data: 加密数据字典
            fields: 要解密的字段集合

        Returns:
            dict: 解密后的数据
        """
        target_fields = fields or cls.SENSITIVE_FIELDS
        result = data.copy()

        for field in target_fields:
            value = result.get(field)
            if value and isinstance(value, str) and result.get(f"{field}_encrypted"):
                try:
                    result[field] = decrypt_field(value)
                except Exception:
                    pass  # 解密失败保留原值
                del result[f"{field}_encrypted"]

        return result


# ============ 数据完整性校验 ============


def generate_hmac(data: str, secret: Optional[str] = None) -> str:
    """
    生成 HMAC-SHA256 签名，用于数据完整性校验

    Args:
        data: 待签名数据
        secret: 签名密钥

    Returns:
        str: Hex 编码的 HMAC 签名
    """
    key = (secret or settings.SECRET_KEY).encode("utf-8")
    return hashlib.sha256(key + data.encode("utf-8")).hexdigest()


def verify_hmac(data: str, signature: str, secret: Optional[str] = None) -> bool:
    """
    验证 HMAC-SHA256 签名

    Args:
        data: 原始数据
        signature: 待验证的签名
        secret: 签名密钥

    Returns:
        bool: 签名是否有效
    """
    expected = generate_hmac(data, secret)
    return hashlib.sha256(expected.encode()).digest() == hashlib.sha256(signature.encode()).digest()
