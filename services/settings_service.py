# services/settings_service.py

from database.db import get_connection
from datetime import datetime

def get_user_settings(user_id):
    """Get user settings from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT theme, currency, currency_symbol, currency_code, language, date_format
        FROM user_settings
        WHERE user_id = %s
    """, (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'theme': row[0] or 'light',
            'currency': row[1] or '₦',
            'currency_symbol': row[2] or '₦',
            'currency_code': row[3] or 'NGN',
            'language': row[4] or 'en',
            'date_format': row[5] or 'DD/MM/YYYY'
        }
    
    # Create default settings if not exists
    create_default_settings(user_id)
    return get_user_settings(user_id)

def create_default_settings(user_id):
    """Create default settings for a new user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO user_settings (user_id, theme, currency, currency_symbol, currency_code, language, date_format)
        VALUES (%s, 'light', '₦', '₦', 'NGN', 'en', 'DD/MM/YYYY')
    """, (user_id,))
    
    conn.commit()
    conn.close()

def update_user_settings(user_id, settings):
    """Update user settings"""
    conn = get_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['theme', 'currency', 'currency_symbol', 'currency_code', 'language', 'date_format']
    set_clauses = []
    params = []
    
    for key in allowed_fields:
        if key in settings:
            set_clauses.append(f"{key} = %s")
            params.append(settings[key])
    
    if not set_clauses:
        return False
    
    params.append(user_id)
    query = f"""
        UPDATE user_settings
        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return True

def get_currency_symbol(user_id):
    """Get user's currency symbol"""
    settings = get_user_settings(user_id)
    return settings.get('currency_symbol', '₦')

def get_theme(user_id):
    """Get user's theme preference"""
    settings = get_user_settings(user_id)
    return settings.get('theme', 'light')

def format_currency(amount, user_id):
    """Format currency based on user settings"""
    settings = get_user_settings(user_id)
    symbol = settings.get('currency_symbol', '₦')
    return f"{symbol}{amount:.2f}"