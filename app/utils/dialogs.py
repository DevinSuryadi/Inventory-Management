import streamlit as st
from typing import Callable, Any, Optional

def confirm_dialog(
    key: str,
    title: str,
    message: str,
    confirm_label: str = "Ya, Lanjutkan",
    cancel_label: str = "Batal",
    warning: bool = True
) -> bool:
    dialog_key = f"confirm_{key}"
    
    if dialog_key not in st.session_state:
        st.session_state[dialog_key] = False
    
    return st.session_state[dialog_key]

def show_confirmation_popup(
    key: str,
    title: str,
    message: str,
    details: Optional[list] = None,
    on_confirm: Optional[Callable] = None,
    confirm_label: str = "Ya, Lanjutkan",
    cancel_label: str = "Batal"
):

    @st.dialog(title)
    def _show_dialog():
        st.warning(message)
        
        if details:
            st.markdown("**Detail:**")
            for detail in details:
                st.markdown(f"- {detail}")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(cancel_label, use_container_width=True, key=f"{key}_cancel"):
                st.session_state[f"confirmed_{key}"] = False
                st.rerun()
        with col2:
            if st.button(confirm_label, use_container_width=True, type="primary", key=f"{key}_confirm"):
                st.session_state[f"confirmed_{key}"] = True
                if on_confirm:
                    on_confirm()
                st.rerun()
    
    return _show_dialog

def delete_confirmation(
    key: str,
    item_name: str,
    item_type: str = "item",
    additional_warning: str = None
):

    @st.dialog(f"Hapus {item_type.title()}?")
    def _delete_dialog():
        st.error(f"⚠️ Anda akan menghapus **{item_name}**")
        st.warning("Tindakan ini tidak dapat dibatalkan!")
        
        if additional_warning:
            st.info(additional_warning)
        
        st.divider()
        
        # Konfirmasi hapus dengan mengetik nama item
        confirmation_text = st.text_input(
            f'Ketik "{item_name}" untuk mengkonfirmasi penghapusan:',
            key=f"{key}_confirm_text"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Batal", use_container_width=True, key=f"{key}_del_cancel"):
                st.session_state[f"delete_confirmed_{key}"] = False
                st.rerun()
        with col2:
            if st.button("Hapus", use_container_width=True, type="primary", key=f"{key}_del_confirm"):
                if confirmation_text == item_name:
                    st.session_state[f"delete_confirmed_{key}"] = True
                    st.rerun()
                else:
                    st.error("Teks konfirmasi tidak cocok!")
    
    return _delete_dialog

def transaction_confirmation(
    key: str,
    transaction_type: str,
    total_amount: float,
    items: list,
    payment_type: str = "cash",
    additional_info: dict = None
):
    @st.dialog(f"Konfirmasi {transaction_type}")
    def _transaction_dialog():
        st.markdown(f"### {transaction_type}")
        
        # Tampilkan detail item
        st.markdown("**Daftar Item:**")
        for idx, item in enumerate(items, 1):
            subtotal = item.get('qty', 0) * item.get('price', 0)
            st.markdown(f"{idx}. **{item.get('name', 'Item')}** - {item.get('qty', 0)} x Rp {item.get('price', 0):,.0f} = Rp {subtotal:,.0f}")
        
        st.divider()
        
        # Total
        st.markdown(f"### Total: Rp {total_amount:,.0f}")
        st.markdown(f"**Pembayaran:** {'Cash' if payment_type == 'cash' else 'Kredit'}")
        
        # Info tambahan
        if additional_info:
            st.markdown("**Info Tambahan:**")
            for label, value in additional_info.items():
                st.markdown(f"- {label}: {value}")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ Batal", use_container_width=True, key=f"{key}_tx_cancel"):
                st.session_state[f"tx_confirmed_{key}"] = False
                st.rerun()
        with col2:
            if st.button("✅ Konfirmasi", use_container_width=True, type="primary", key=f"{key}_tx_confirm"):
                st.session_state[f"tx_confirmed_{key}"] = True
                st.rerun()
    
    return _transaction_dialog

def is_confirmed(key: str, prefix: str = "confirmed") -> bool:
    """Cek apakah dialog sudah dikonfirmasi"""
    return st.session_state.get(f"{prefix}_{key}", False)

def reset_confirmation(key: str, prefix: str = "confirmed"):
    """Reset status konfirmasi"""
    if f"{prefix}_{key}" in st.session_state:
        del st.session_state[f"{prefix}_{key}"]
