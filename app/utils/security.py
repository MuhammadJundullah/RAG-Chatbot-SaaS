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


# --- Query Validator ---
class QueryValidator:
    def __init__(self):
        # ... (rest of the class remains the same)
        self.dangerous_patterns = [
            r'\bDROP\b',
            r'\bDELETE\b',
            r'\bINSERT\b',
            r'\bUPDATE\b',
            r'\bALTER\b',
            r'\bCREATE\b',
            r'\bTRUNCATE\b',
            r'\bGRANT\b',
            r'\bREVOKE\b',
            r'\bEXECUTE\b',
            r'\bCALL\b',
            r'\bDO\b', # For anonymous code blocks in PostgreSQL
            r'\bUNION\s+ALL\b', # UNION can be used for data exfiltration
            r'\bUNION\b',
            r'\bINFORMATION_SCHEMA\b', # Accessing schema directly
            r'\bpg_sleep\b', # Time-based attacks
            r'\bpg_read_file\b', # File system access
            r';\s*(?!$)',  # Multiple statements, but allow trailing semicolon
            r'--.*',    # SQL comments (single line)
            r'/\*.*\*/',   # SQL block comments
            r'\bFROM\s+pg_catalog\b', # Accessing system catalogs
            r'\bCOPY\b', # Data export/import
            r'\bFILE\b', # File operations
            r'\bOUTFILE\b', # File operations
            r'\bINTO\s+OUTFILE\b', # File operations
            r'\bLOAD_FILE\b', # File operations
        ]
        # Regex to check for valid SELECT/WITH structure, allowing for CTEs
        self.valid_start_pattern = re.compile(r'^\s*(SELECT|WITH)\b', re.IGNORECASE)

    def is_safe_query(self, query: str) -> bool:
        """Validate SQL query for safety"""
        query_upper = query.upper().strip()

        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                print(f"Dangerous pattern detected: {pattern} in query: {query}") # For debugging
                return False

        # Basic structure validation: must start with SELECT or WITH
        if not self.valid_start_pattern.match(query):
                print(f"Query does not start with SELECT or WITH: {query}") # For debugging
                return False

        return True
