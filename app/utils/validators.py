import re
from typing import Any, Optional

def validate_product_name(name: str) -> tuple[bool, str]:
    if not name or not name.strip():
        return False, "Nama produk tidak boleh kosong atau hanya spasi."
    
    if len(name.strip()) < 3:
        return False, "Nama produk minimal 3 karakter."
    
    if len(name.strip()) > 100:
        return False, "Nama produk maksimal 100 karakter."
    
    return True, ""

def validate_supplier_name(name: str) -> tuple[bool, str]:
    if not name or not name.strip():
        return False, "Nama supplier tidak boleh kosong."
    
    if len(name.strip()) < 3:
        return False, "Nama supplier minimal 3 karakter."
    
    if len(name.strip()) > 100:
        return False, "Nama supplier maksimal 100 karakter."
    
    return True, ""

def validate_warehouse_name(name: str) -> tuple[bool, str]:
    if not name or not name.strip():
        return False, "Nama gudang tidak boleh kosong."
    
    if len(name.strip()) < 3:
        return False, "Nama gudang minimal 3 karakter."
    
    return True, ""

def validate_phone_number(phone: str) -> tuple[bool, str]:
    if not phone or not phone.strip():
        return True, "" 
    cleaned = phone.replace("-", "").replace(" ", "").replace("+", "")
    
    if cleaned.startswith("62"):
        if len(cleaned) < 10 or len(cleaned) > 13:
            return False, "Nomor telepon tidak valid (format: +62 8xx-xxxx-xxxx)."
    elif cleaned.startswith("8"):
        if len(cleaned) < 9 or len(cleaned) > 12:
            return False, "Nomor telepon tidak valid (format: 08xx-xxxx-xxxx)."
    else:
        return False, "Nomor telepon harus dimulai dengan 08 atau +62."
    
    return True, ""

def validate_quantity(qty: Any) -> tuple[bool, str]:
    try:
        qty_int = int(qty)
        if qty_int < 1:
            return False, "Jumlah harus minimal 1."
        return True, ""
    except (ValueError, TypeError):
        return False, "Jumlah harus berupa angka."

def validate_price(price: Any) -> tuple[bool, str]:
    try:
        price_float = float(price)
        if price_float < 0.01:
            return False, "Harga harus minimal Rp 0.01."
        return True, ""
    except (ValueError, TypeError):
        return False, "Harga harus berupa angka."

def validate_email(email: str) -> tuple[bool, str]:
    """Validasi email format."""
    if not email or not email.strip():
        return True, "" 
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email.strip()):
        return False, "Format email tidak valid."
    
    return True, ""

def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 2:
        return False, "Password minimal 2 karakter."
    
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password harus mengandung huruf."
    
    if not re.search(r'[0-9]', password):
        return False, "Password harus mengandung angka."
    
    return True, ""

def validate_username(username: str) -> tuple[bool, str]:
    if not username or not username.strip():
        return False, "Username tidak boleh kosong."
    
    if len(username.strip()) < 3:
        return False, "Username minimal 3 karakter."
    
    if len(username.strip()) > 20:
        return False, "Username maksimal 20 karakter."
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username.strip()):
        return False, "Username hanya boleh mengandung huruf, angka, dan underscore."
    
    return True, ""

# Dictionary untuk easy import
VALIDATORS = {
    'product_name': validate_product_name,
    'supplier_name': validate_supplier_name,
    'warehouse_name': validate_warehouse_name,
    'phone': validate_phone_number,
    'quantity': validate_quantity,
    'price': validate_price,
    'email': validate_email,
    'password': validate_password,
    'username': validate_username,
}
