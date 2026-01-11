import streamlit as st
import logging
from typing import Any, Callable, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')

def handle_api_error(error: Exception, context: str = "") -> str:
    error_str = str(error).lower()
    
    # Supabase specific errors
    if "connection" in error_str or "network" in error_str:
        message = "Koneksi ke server gagal. Silakan cek koneksi internet Anda."
    elif "unauthorized" in error_str or "401" in error_str:
        message = "Anda tidak memiliki akses. Silakan login kembali."
    elif "not found" in error_str or "404" in error_str:
        message = "Data tidak ditemukan."
    elif "conflict" in error_str or "duplicate" in error_str:
        message = "Data sudah ada atau terjadi konflik. Silakan cek kembali."
    elif "timeout" in error_str:
        message = "Request timeout. Silakan coba lagi."
    else:
        message = "Terjadi kesalahan di server. Silakan coba lagi nanti."
    
    # Log full error untuk debugging
    logger.error(f"API Error in {context}: {str(error)}")
    
    return message

def safe_api_call(func: Callable[..., T], *args, **kwargs) -> Optional[T]:
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_msg = handle_api_error(e, func.__name__)
        st.error(error_msg)
        return None

def show_success_toast(message: str, duration: int = 3):
    """Show success message dengan auto-dismiss."""
    st.success(message)

def show_error_toast(message: str, duration: int = 5):
    """Show error message dengan auto-dismiss."""
    st.error(message)

def show_warning_toast(message: str, duration: int = 4):
    """Show warning message dengan auto-dismiss."""
    st.warning(message)

def confirm_action(title: str, question: str = "Lanjutkan?", key: str = None) -> bool:
    if key is None:
        key = f"confirm_{title}"
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Ya, {question}", key=f"{key}_yes"):
            return True
    with col2:
        if st.button(f"Batal", key=f"{key}_no"):
            return False
    
    return False

def validate_form_data(data: dict, required_fields: list[str]) -> tuple[bool, str]:
    missing_fields = [f for f in required_fields if not data.get(f)]
    
    if missing_fields:
        return False, f"Field berikut wajib diisi: {', '.join(missing_fields)}"
    
    return True, ""

class ErrorHandler:
    
    def __init__(self, context: str = "", show_error: bool = True):
        self.context = context
        self.show_error = show_error
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            error_msg = handle_api_error(exc_val, self.context)
            
            if self.show_error:
                st.error(error_msg)
            
            logger.error(f"{self.context}: {str(exc_val)}")
            
            return True
        
        return False
