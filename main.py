import streamlit as st
# Mengimpor semua modul yang dibutuhkan
from app.auth import login, logout
from app.pages.admin import dashboard as admin_dashboard
from app.pages.admin import finance_management 
from app.pages.admin import cashflow_history
from app.pages.user import (
    view_stock, register_stock, stock_adjustment, adjustment_history,
    purchase, purchase_history, sale, sales_history, sales_payable,
    view_supplier, add_supplier, supplier_debt,
    view_warehouse, register_warehouse, 
    import_stock
)

# Konfigurasi Halaman
st.set_page_config(
    page_title="Sistem Inventaris Toko",
    page_icon="📦",
    layout="wide"
)

# --- Inisialisasi Session State ---
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.store = ""

# --- Struktur Menu User ---
USER_PAGES = {
    "📦 Product Management": {
        "View Stock": view_stock.show,
        "Register Stock": register_stock.show,
        "Stock Adjustment": stock_adjustment.show,
        "Adjustment History": adjustment_history.show,
        "Import Stock (Excel)": import_stock.show,
    },
    "🛒 Transaction": {
        "Purchase": purchase.show,
        "Purchase History": purchase_history.show,
        "Sale": sale.show,
        "Sales History": sales_history.show,
        "Sales Payable": sales_payable.show,
    },
    "👥 Supplier": {
        "View Supplier": view_supplier.show,
        "Add Supplier": add_supplier.show,
        "Supplier Debt": supplier_debt.show,
    },
    "🏠 Warehouse": {
        "View Warehouse": view_warehouse.show,
        "Register Warehouse": register_warehouse.show,
    }
}

# --- Fungsi Utama Aplikasi ---
def main():
    init_session_state()

    if not st.session_state.logged_in:
        with st.container():
            st.title("Login Sistem Inventaris")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login", use_container_width=True):
                if login(username, password):
                    st.success("Login berhasil!")
                    st.rerun()
    else:
        st.sidebar.markdown(f"Selamat datang, **{st.session_state.username}**!")
        
        if st.session_state.role == 'admin':
            # PENYEMPURNAAN: Membuat menu navigasi untuk admin
            st.sidebar.title("Menu Admin")
            st.sidebar.markdown(f"Peran: **Admin Pusat**")
            st.sidebar.divider()
            
            admin_menu = st.sidebar.radio(
                "Navigasi Admin", 
                ["📊 Analytics Dashboard", "💰 Manajemen Keuangan", "📜 Riwayat Arus Kas"]
            )
            
            st.sidebar.divider()
            if st.sidebar.button("Logout", use_container_width=True):
                logout()
                st.rerun()

            # Menampilkan halaman sesuai pilihan menu admin
            if admin_menu == "📊 Analytics Dashboard":
                admin_dashboard.show()
            elif admin_menu == "💰 Manajemen Keuangan":
                finance_management.show()
            elif admin_menu == "📜 Riwayat Arus Kas":
                cashflow_history.show()
        
        elif st.session_state.role == 'pegawai':
            st.sidebar.title("Menu Navigasi")
            st.sidebar.markdown(f"Toko: **{st.session_state.store}**")
            st.sidebar.divider()
            
            main_menu = st.sidebar.radio("Menu Utama", list(USER_PAGES.keys()))
            
            if main_menu in USER_PAGES:
                submenu_options = list(USER_PAGES[main_menu].keys())
                submenu = st.sidebar.radio("Sub-Menu", submenu_options, key=f"submenu_{main_menu}")
                page_function = USER_PAGES[main_menu][submenu]
                page_function()
        
            st.sidebar.divider()
            if st.sidebar.button("Logout", use_container_width=True):
                logout()
                st.rerun()

if __name__ == "__main__":
    main()
