# app/utils/logger.py
# Logging system untuk audit trail dan debugging

import logging
import logging.handlers
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Create logs directory jika tidak ada
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Custom JSON formatter untuk structured logging
class JSONFormatter(logging.Formatter):
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info jika ada
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields jika ada
        if hasattr(record, "user"):
            log_data["user"] = record.user
        if hasattr(record, "store"):
            log_data["store"] = record.store
        if hasattr(record, "data"):
            log_data["data"] = str(record.data)
        
        return json.dumps(log_data, default=str)

def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers = []
    
    # Console handler - simple format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler - JSON format untuk machine-readable logs
    if log_file:
        log_path = LOGS_DIR / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,  # Keep 5 backup files
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    return logger

# Initialize main loggers
app_logger = setup_logger('inventory_app', 'app.log')
transaction_logger = setup_logger('transactions', 'transactions.log')
auth_logger = setup_logger('auth', 'auth.log')
error_logger = setup_logger('errors', 'errors.log', level=logging.ERROR)

# Utility functions untuk common logging tasks

def log_login(username: str, role: str, store: str, success: bool = True):
    """Log user login attempt."""
    extra = {
        "user": username,
        "store": store,
        "role": role,
    }
    if success:
        auth_logger.info(f"User login successful", extra=extra)
    else:
        auth_logger.warning(f"Failed login attempt", extra=extra)

def log_logout(username: str, store: str):
    """Log user logout."""
    auth_logger.info(f"User logout", extra={"user": username, "store": store})

def log_purchase_transaction(
    username: str,
    store: str,
    product_id: int,
    product_name: str,
    quantity: int,
    price: float,
    supplier_id: int,
    supplier_name: str,
    transaction_date: str
):
    """Log purchase transaction."""
    data = {
        "type": "purchase",
        "product_id": product_id,
        "product_name": product_name,
        "quantity": quantity,
        "unit_price": price,
        "total": quantity * price,
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "date": transaction_date,
    }
    transaction_logger.info(
        f"Purchase transaction recorded",
        extra={"user": username, "store": store, "data": data}
    )

def log_sale_transaction(
    username: str,
    store: str,
    product_id: int,
    product_name: str,
    quantity: int,
    price: float,
    customer_name: Optional[str],
    transaction_date: str
):
    """Log sale transaction."""
    data = {
        "type": "sale",
        "product_id": product_id,
        "product_name": product_name,
        "quantity": quantity,
        "unit_price": price,
        "total": quantity * price,
        "customer": customer_name or "Unnamed",
        "date": transaction_date,
    }
    transaction_logger.info(
        f"Sale transaction recorded",
        extra={"user": username, "store": store, "data": data}
    )

def log_stock_adjustment(
    username: str,
    store: str,
    product_id: int,
    product_name: str,
    warehouse: str,
    adjustment_type: str,  # "add" or "reduce"
    quantity: int,
    reason: str,
    date: str
):
    """Log stock adjustment."""
    data = {
        "type": "stock_adjustment",
        "adjustment_type": adjustment_type,
        "product_id": product_id,
        "product_name": product_name,
        "warehouse": warehouse,
        "quantity": quantity,
        "reason": reason,
        "date": date,
    }
    transaction_logger.info(
        f"Stock adjustment recorded",
        extra={"user": username, "store": store, "data": data}
    )

def log_payment(
    username: str,
    store: str,
    payment_type: str,  # "supplier" or "customer"
    payer_or_recipient: str,
    amount: float,
    transaction_id: int,
    date: str
):
    """Log payment transaction."""
    data = {
        "type": payment_type,
        "payer_or_recipient": payer_or_recipient,
        "amount": amount,
        "transaction_id": transaction_id,
        "date": date,
    }
    transaction_logger.info(
        f"Payment recorded",
        extra={"user": username, "store": store, "data": data}
    )

def log_error(error: Exception, context: str = "", username: Optional[str] = None):
    """Log error untuk debugging."""
    extra = {}
    if username:
        extra["user"] = username
    
    error_logger.error(f"Error in {context}: {str(error)}", exc_info=True, extra=extra)

# Export loggers untuk digunakan di module lain
__all__ = [
    'app_logger',
    'transaction_logger',
    'auth_logger',
    'error_logger',
    'log_login',
    'log_logout',
    'log_purchase_transaction',
    'log_sale_transaction',
    'log_stock_adjustment',
    'log_payment',
    'log_error',
]
