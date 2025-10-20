import re
import hashlib
import bcrypt as bcrypt_lib

# Use bcrypt directly instead of passlib to avoid initialization issues
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hashed password"""
    try:
        # Convert password to bytes
        password_bytes = plain_password.encode('utf-8')
        
        # Pre-hash if too long for bcrypt
        if len(password_bytes) > 72:
            password_bytes = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')
        
        # Convert stored hash to bytes if it's a string
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
            
        return bcrypt_lib.checkpw(password_bytes, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    # Convert to bytes
    password_bytes = password.encode('utf-8')
    
    # Pre-hash if too long for bcrypt (>72 bytes)
    if len(password_bytes) > 72:
        password_bytes = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')
    
    # Generate salt and hash
    salt = bcrypt_lib.gensalt(rounds=12)
    hashed = bcrypt_lib.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')
