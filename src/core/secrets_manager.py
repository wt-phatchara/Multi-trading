"""Production-grade secrets management with encryption."""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class SecretsManager:
    """Secure secrets management with encryption at rest."""

    def __init__(self, master_password: Optional[str] = None):
        """
        Initialize secrets manager.

        Args:
            master_password: Master password for encryption (from env var if not provided)
        """
        self.master_password = master_password or os.getenv('MASTER_PASSWORD')
        if not self.master_password:
            raise ValueError("MASTER_PASSWORD environment variable must be set")

        self.secrets_file = Path('secrets.enc')
        self.cipher_suite = self._get_cipher_suite()

    def _get_cipher_suite(self) -> Fernet:
        """Generate encryption cipher from master password."""
        # Derive key from password
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'trading_agent_salt',  # In production, use random salt stored separately
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
        return Fernet(key)

    def encrypt_secrets(self, secrets: Dict[str, Any]) -> None:
        """
        Encrypt and store secrets.

        Args:
            secrets: Dictionary of secrets to encrypt
        """
        try:
            # Convert to JSON and encrypt
            json_data = json.dumps(secrets).encode()
            encrypted_data = self.cipher_suite.encrypt(json_data)

            # Write to file
            self.secrets_file.write_bytes(encrypted_data)
            # Set restrictive permissions
            os.chmod(self.secrets_file, 0o600)

            logger.info("Secrets encrypted and stored successfully")
        except Exception as e:
            logger.error(f"Failed to encrypt secrets: {e}")
            raise

    def decrypt_secrets(self) -> Dict[str, Any]:
        """
        Decrypt and retrieve secrets.

        Returns:
            Dictionary of decrypted secrets
        """
        try:
            if not self.secrets_file.exists():
                logger.warning("No encrypted secrets file found")
                return {}

            # Read and decrypt
            encrypted_data = self.secrets_file.read_bytes()
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)

            # Parse JSON
            secrets = json.loads(decrypted_data.decode())
            logger.info("Secrets decrypted successfully")
            return secrets

        except Exception as e:
            logger.error(f"Failed to decrypt secrets: {e}")
            raise

    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        Get a single secret value.

        Args:
            key: Secret key
            default: Default value if not found

        Returns:
            Secret value
        """
        secrets = self.decrypt_secrets()
        return secrets.get(key, default)

    def set_secret(self, key: str, value: Any) -> None:
        """
        Set a single secret value.

        Args:
            key: Secret key
            value: Secret value
        """
        secrets = self.decrypt_secrets() if self.secrets_file.exists() else {}
        secrets[key] = value
        self.encrypt_secrets(secrets)

    def rotate_api_keys(self, new_api_key: str, new_api_secret: str) -> None:
        """
        Rotate API keys with backup of old keys.

        Args:
            new_api_key: New API key
            new_api_secret: New API secret
        """
        secrets = self.decrypt_secrets()

        # Backup old keys
        if 'api_key' in secrets:
            secrets['api_key_backup'] = secrets['api_key']
        if 'api_secret' in secrets:
            secrets['api_secret_backup'] = secrets['api_secret']

        # Set new keys
        secrets['api_key'] = new_api_key
        secrets['api_secret'] = new_api_secret

        self.encrypt_secrets(secrets)
        logger.info("API keys rotated successfully")

    @staticmethod
    def setup_from_env() -> 'SecretsManager':
        """
        Create secrets manager and migrate from .env file.

        Returns:
            Configured SecretsManager instance
        """
        manager = SecretsManager()

        # Migrate from .env if secrets.enc doesn't exist
        if not manager.secrets_file.exists():
            from dotenv import load_dotenv
            load_dotenv()

            secrets = {
                'exchange_api_key': os.getenv('EXCHANGE_API_KEY', ''),
                'exchange_api_secret': os.getenv('EXCHANGE_API_SECRET', ''),
                'sentry_dsn': os.getenv('SENTRY_DSN', ''),
                'redis_password': os.getenv('REDIS_PASSWORD', ''),
                'db_password': os.getenv('DB_PASSWORD', '')
            }

            manager.encrypt_secrets(secrets)
            logger.info("Secrets migrated from .env to encrypted storage")

        return manager
