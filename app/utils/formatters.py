from datetime import datetime, date
from typing import Union

def format_currency(value: float, prefix: str = "Rp ") -> str:
    try:
        return f"{prefix}{value:,.2f}"
    except (ValueError, TypeError):
        return f"{prefix}0.00"

def format_currency_no_decimal(value: float, prefix: str = "Rp ") -> str:
    try:
        return f"{prefix}{int(value):,}".replace(',', '.')
    except (ValueError, TypeError):
        return f"{prefix}0"

def format_datetime(dt: Union[datetime, str], format: str = "%d/%m/%Y %H:%M") -> str:
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except:
            return str(dt)
    
    try:
        return dt.strftime(format)
    except:
        return str(dt)

def format_date(d: Union[date, str], format: str = "%d/%m/%Y") -> str:
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
    try:
        return f"{int(qty):,}"
    except (ValueError, TypeError):
        return "0"

def format_percentage(value: float, decimal: int = 2) -> str:
    try:
        return f"{value * 100:.{decimal}f}%"
    except (ValueError, TypeError):
        return "0.00%"

def format_indonesian_date(d: Union[date, str]) -> str:
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
    mapping = {
        "cash": "Kas",
        "bank": "Bank",
        "credit_card": "Kartu Kredit",
        "savings": "Tabungan",
        "investment": "Investasi",
    }
    return mapping.get(account_type.lower(), account_type)

def format_transaction_type(transaction_type: str) -> str:
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
    mapping = {
        "cash": "Tunai",
        "credit": "Kredit",
        "check": "Cek",
        "transfer": "Transfer Bank",
    }
    return mapping.get(payment_type.lower(), payment_type)

def shorten_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    if len(text) > max_length:
        return text[:max_length - len(suffix)] + suffix
    return text

FORMATTERS = {
    'currency': format_currency,
    'datetime': format_datetime,
    'date': format_date,
    'time': format_time,
    'quantity': format_quantity,
    'percentage': format_percentage,
}
