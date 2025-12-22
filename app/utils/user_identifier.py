from typing import Optional, Any


def get_user_identifier(user: Optional[Any], company: Optional[Any] = None) -> str:
    """
    Returns the identifier used for logs/audit:
    - admin: company.company_email (fallback to user email/username)
    - other roles: username (fallback to user email)
    """
    if not user:
        return ""

    role = getattr(user, "role", None)
    if role == "admin":
        company_obj = getattr(user, "company", None) or company
        company_email = getattr(company_obj, "company_email", None) if company_obj else None
        if company_email:
            return company_email
        return getattr(user, "email", None) or getattr(user, "username", None) or ""

    return getattr(user, "username", None) or getattr(user, "email", None) or ""
