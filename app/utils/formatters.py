# app/utils/formatters.py
# Utility functions untuk formatting data

from datetime import datetime, date
from typing import Union

def format_currency(value: float, prefix: str = "Rp ") -> str:
    """
    Format angka menjadi currency dengan separator ribuan.
    
    Example:
    format_currency(1000000) -> "Rp 1,000,000.00"
    format_currency(1000000.50) -> "Rp 1,000,000.50"
    """
    try:
        return f"{prefix}{value:,.2f}"
    except (ValueError, TypeError):
        return f"{prefix}0.00"

def format_currency_no_decimal(value: float, prefix: str = "Rp ") -> str:
    """
    Format angka menjadi currency tanpa decimal places.
    
    Example:
    format_currency_no_decimal(1000000) -> "Rp 1,000,000"
    """
    try:
        return f"{prefix}{int(value):,}".replace(',', '.')
    except (ValueError, TypeError):
        return f"{prefix}0"

def format_datetime(dt: Union[datetime, str], format: str = "%d/%m/%Y %H:%M") -> str:
    """
    Format datetime ke string dengan format yang konsisten.
    
    Default format: DD/MM/YYYY HH:MM (format Indonesia)
    
    Example:
    format_datetime(datetime.now()) -> "15/01/2026 14:30"
    """
    if isinstance(dt, str):
        # Try to parse string to datetime
        try:
            dt = datetime.fromisoformat(dt)
        except:
            return str(dt)
    
    try:
        return dt.strftime(format)
    except:
        return str(dt)

def format_date(d: Union[date, str], format: str = "%d/%m/%Y") -> str:
    """
    Format date ke string.
    
    Default format: DD/MM/YYYY (format Indonesia)
    
    Example:
    format_date(date.today()) -> "15/01/2026"
    """
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d).date()
        except:
            return str(d)
    
    try:
        if isinstance(d, datetime):
            d = d.date()
        return d.strftime(format)
    except:
        return str(d)

def format_time(t: Union[str], format: str = "%H:%M") -> str:
    """
    Format time ke string.
    
    Default format: HH:MM
    """
    if isinstance(t, str):
        try:
            t = datetime.fromisoformat(f"2000-01-01 {t}").time()
        except:
            return str(t)
    
    try:
        if isinstance(t, datetime):
            t = t.time()
        return t.strftime(format)
    except:
        return str(t)

def format_quantity(qty: float) -> str:
    """
    Format quantity dengan separator ribuan (tanpa decimal).
    
    Example:
    format_quantity(1000) -> "1,000"
    """
    try:
        return f"{int(qty):,}"
    except (ValueError, TypeError):
        return "0"

def format_percentage(value: float, decimal: int = 2) -> str:
    """
    Format number menjadi percentage.
    
    Example:
    format_percentage(0.1234) -> "12.34%"
    """
    try:
        return f"{value * 100:.{decimal}f}%"
    except (ValueError, TypeError):
        return "0.00%"

def format_indonesian_date(d: Union[date, str]) -> str:
    """
    Format date ke format Indonesia (nama bulan dalam bahasa Indonesia).
    
    Example:
    format_indonesian_date(date(2026, 1, 15)) -> "15 Januari 2026"
    """
    months_id = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d).date()
        except:
            return str(d)
    
    try:
        if isinstance(d, datetime):
            d = d.date()
        month_name = months_id[d.month - 1]
        return f"{d.day} {month_name} {d.year}"
    except:
        return str(d)

def format_account_type(account_type: str) -> str:
    """
    Format account type untuk display yang lebih readable.
    
    Example:
    format_account_type("cash") -> "Kas"
    format_account_type("bank") -> "Bank"
    """
    mapping = {
        "cash": "Kas",
        "bank": "Bank",
        "credit_card": "Kartu Kredit",
        "savings": "Tabungan",
        "investment": "Investasi",
    }
    return mapping.get(account_type.lower(), account_type)

def format_transaction_type(transaction_type: str) -> str:
    """
    Format transaction type untuk display.
    
    Example:
    format_transaction_type("add") -> "Penambahan"
    format_transaction_type("reduce") -> "Pengurangan"
    """
    mapping = {
        "add": "Penambahan",
        "reduce": "Pengurangan",
        "purchase": "Pembelian",
        "sale": "Penjualan",
        "adjustment": "Penyesuaian",
        "transfer": "Transfer",
    }
    return mapping.get(transaction_type.lower(), transaction_type)

def format_payment_type(payment_type: str) -> str:
    """
    Format payment type untuk display.
    
    Example:
    format_payment_type("cash") -> "Tunai"
    format_payment_type("credit") -> "Kredit"
    """
    mapping = {
        "cash": "Tunai",
        "credit": "Kredit",
        "check": "Cek",
        "transfer": "Transfer Bank",
    }
    return mapping.get(payment_type.lower(), payment_type)

def shorten_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Shorten text jika melebihi max_length.
    
    Example:
    shorten_text("Ini adalah text yang sangat panjang", 20) 
    -> "Ini adalah text yang..."
    """
    if len(text) > max_length:
        return text[:max_length - len(suffix)] + suffix
    return text

# Dictionary untuk easy import
FORMATTERS = {
    'currency': format_currency,
    'datetime': format_datetime,
    'date': format_date,
    'time': format_time,
    'quantity': format_quantity,
    'percentage': format_percentage,
}
