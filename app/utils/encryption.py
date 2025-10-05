from cryptography.fernet import Fernet
from app.config.settings import settings
import base64

# We need a key that is 32 bytes and URL-safe. 
# We will derive it from the main SECRET_KEY for simplicity.
# In a production system, you might use a separate, dedicated key.
key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
fernet = Fernet(key)

def encrypt_string(text: str) -> str:
    """Encrypts a string."""
    if not text:
        return None
    return fernet.encrypt(text.encode()).decode()

def decrypt_string(encrypted_text: str) -> str:
    """Decrypts an encrypted string."""
    if not encrypted_text:
        return None
    return fernet.decrypt(encrypted_text.encode()).decode()
