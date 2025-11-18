import secrets
import string

def generate_company_code(length=6):
    """Generates a random, secure company code."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_reset_token(length=32):
    """Generates a random, secure token for password reset."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
