def _needs_database_query(message: str) -> bool:
    """Simple heuristic to check if a question might need a database query."""
    db_keywords = [
        'berapa', 'jumlah', 'total', 'rata', 'average', 'sum',
        'pelanggan', 'customer', 'tagihan', 'bill', 'penjualan', 'sales',
        'data', 'tampilkan', 'show', 'list', 'find', 'get'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in db_keywords)