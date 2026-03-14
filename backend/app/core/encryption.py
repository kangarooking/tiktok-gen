"""
Encryption utilities for sensitive configuration data

Uses Fernet symmetric encryption with a key derived from JWT_SECRET_KEY.
"""
import base64
import hashlib
import json
import re
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet

from app.config import settings


class EncryptionService:
    """
    Encryption service for sensitive configuration data

    Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
    The encryption key is derived from JWT_SECRET_KEY using SHA-256.
    """

    _instance: Optional['EncryptionService'] = None
    _fernet: Optional[Fernet] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the Fernet cipher with derived key"""
        # Derive a 32-byte key from JWT_SECRET_KEY using SHA-256
        key_material = settings.JWT_SECRET_KEY.encode('utf-8')
        derived_key = hashlib.sha256(key_material).digest()
        # Fernet requires base64-encoded 32-byte key
        fernet_key = base64.urlsafe_b64encode(derived_key)
        self._fernet = Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        encrypted = self._fernet.encrypt(plaintext.encode('utf-8'))
        return encrypted.decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string

        Args:
            ciphertext: The encrypted string to decrypt

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails
        """
        if not ciphertext:
            return ""
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")

    def encrypt_config(self, config: Dict[str, Any]) -> str:
        """
        Encrypt a configuration dictionary

        Args:
            config: Configuration dictionary to encrypt

        Returns:
            Encrypted JSON string
        """
        json_str = json.dumps(config, ensure_ascii=False)
        return self.encrypt(json_str)

    def decrypt_config(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt configuration data

        Args:
            encrypted_data: Encrypted configuration string

        Returns:
            Decrypted configuration dictionary
        """
        if not encrypted_data:
            return {}
        try:
            json_str = self.decrypt(encrypted_data)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse decrypted config: {str(e)}")

    @staticmethod
    def mask_value(value: str, show_length: int = 4) -> str:
        """
        Mask a sensitive value for display

        Args:
            value: The value to mask
            show_length: Number of characters to show at start and end

        Returns:
            Masked value like "sk-****abc123"
        """
        if not value:
            return ""

        if len(value) <= show_length * 2:
            return "*" * len(value)

        return f"{value[:show_length]}{'*' * 8}{value[-show_length:]}"

    @staticmethod
    def mask_config(config: Dict[str, Any], sensitive_fields: list) -> Dict[str, Any]:
        """
        Mask sensitive fields in a configuration dictionary

        Args:
            config: Configuration dictionary
            sensitive_fields: List of field names to mask

        Returns:
            Configuration with masked sensitive fields
        """
        masked = config.copy()
        for field in sensitive_fields:
            if field in masked and masked[field]:
                masked[field] = EncryptionService.mask_value(str(masked[field]))
        return masked


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get the singleton encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions
def encrypt_config(config: Dict[str, Any]) -> str:
    """Encrypt a configuration dictionary"""
    return get_encryption_service().encrypt_config(config)


def decrypt_config(encrypted_data: str) -> Dict[str, Any]:
    """Decrypt configuration data"""
    return get_encryption_service().decrypt_config(encrypted_data)


def mask_config(config: Dict[str, Any], sensitive_fields: list) -> Dict[str, Any]:
    """Mask sensitive fields in a configuration dictionary"""
    return EncryptionService.mask_config(config, sensitive_fields)


def mask_api_key(api_key: str) -> str:
    """Mask an API key for display"""
    return EncryptionService.mask_value(api_key)
