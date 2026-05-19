# Currency Configuration for the entire project
# Default currency is INR (Indian Rupees), but supports multiple currencies

CURRENCIES = {
    'INR': {
        'symbol': '\u20b9',
        'name': 'Indian Rupee',
        'code': 'INR',
        'locale': 'en-IN',
        'decimal_places': 2
    },
    'USD': {
        'symbol': '$',
        'name': 'US Dollar',
        'code': 'USD',
        'locale': 'en-US',
        'decimal_places': 2
    },
    'EUR': {
        'symbol': '\u20ac',
        'name': 'Euro',
        'code': 'EUR',
        'locale': 'de-DE',
        'decimal_places': 2
    },
    'GBP': {
        'symbol': '\u00a3',
        'name': 'British Pound',
        'code': 'GBP',
        'locale': 'en-GB',
        'decimal_places': 2
    },
    'JPY': {
        'symbol': '\u00a5',
        'name': 'Japanese Yen',
        'code': 'JPY',
        'locale': 'ja-JP',
        'decimal_places': 0
    }
}

# Default currency for the application
DEFAULT_CURRENCY = 'INR'

def get_currency_symbol(currency_code=None):
    """Get currency symbol for given code or default"""
    code = currency_code or DEFAULT_CURRENCY
    return CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])['symbol']

def get_currency_info(currency_code=None):
    """Get full currency information"""
    code = currency_code or DEFAULT_CURRENCY
    return CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])

def format_amount(amount, currency_code=None):
    """Format amount with currency symbol"""
    currency = get_currency_info(currency_code)
    symbol = currency['symbol']
    
    # Format with proper decimal places
    if currency['decimal_places'] == 0:
        formatted = f"{symbol}{int(amount):,}"
    else:
        formatted = f"{symbol}{amount:,.{currency['decimal_places']}f}"
    
    return formatted
