import streamlit as st
from app.auth import login, logout
from app.pages.admin import dashboard as admin_dashboard
from app.pages.admin import finance_management 
from app.pages.admin import cashflow_history
from app.pages.admin import admin_management
from app.pages.admin import staff_management
from app.pages.admin import operational_expense as admin_expense
from app.pages.user import (
    view_stock, register_stock, stock_adjustment, adjustment_history,
    purchase, purchase_history, sale, sales_history, sales_payable,
    view_supplier, add_supplier, supplier_debt,
    view_warehouse, register_warehouse, 
    import_stock, 
    purchase_return, sale_return, return_history
)

st.set_page_config(
    page_title="Sistem Inventaris Toko",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    with open("app/styles.css", "r", encoding="utf-8") as css_file:
        st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.markdown("""
    <style>
        .main { padding: 2rem; }
        .stButton>button {
            width: 100%;
            padding: 0.75rem;
            border-radius: 0.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .login-container {
            max-width: 400px;
            margin: 5rem auto;
            padding: 2rem;
            border-radius: 1rem;
            border: 1px solid #e0e0e0;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .sidebar-header {
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            padding: 0.5rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.store = ""

# Struktur Menu User
USER_PAGES = {
    "Manajemen Produk": {
        "Lihat Stok": view_stock.show,
        "Daftarkan Produk": register_stock.show,
        "Sesuaikan Stok": stock_adjustment.show,
        "Riwayat Penyesuaian": adjustment_history.show,
        "Impor dari Excel": import_stock.show,
    },
    "Transaksi": {
        "Pembelian": purchase.show,
        "Riwayat Pembelian": purchase_history.show,
        "Penjualan": sale.show,
        "Riwayat Penjualan": sales_history.show,
        "Piutang Pelanggan": sales_payable.show,
    },
    "Retur": {
        "Retur Pembelian": purchase_return.show,
        "Retur Penjualan": sale_return.show,
        "Riwayat Retur": return_history.show,
    },
    "Supplier": {
        "Lihat Supplier": view_supplier.show,
        "Tambah Supplier": add_supplier.show,
        "Utang Supplier": supplier_debt.show,
    },
    "Gudang": {
        "Lihat Gudang": view_warehouse.show,
        "Daftarkan Gudang": register_warehouse.show,
    }
}

# Fungsi Login Screen 
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #1f77b4;'>Inventory System</h1>", unsafe_allow_html=True)

        with st.container():
            st.markdown("---")
            col_a, col_b = st.columns([1, 1], gap="small")

            with col_a:
                username = st.text_input("Username", key="login_username")
            with col_b:
                password = st.text_input("Password", type="password", key="login_password")

            st.markdown("")
            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn2:
                if st.button("Login", use_container_width=True, type="primary"):
                    if login(username, password):
                        st.success("Login berhasil!")
                        st.rerun()

def main():
    init_session_state()

    if not st.session_state.logged_in:
        login_screen()
    else:
        # Header Sidebar
        with st.sidebar:
            st.markdown(f"### Pengguna: {st.session_state.username}")
            role_display = ""
            if st.session_state.role == 'pegawai':
                role_display = 'Pegawai'
            elif st.session_state.role == 'admin':
                role_display = 'Admin'
            else:
                role_display = st.session_state.role
            st.markdown(f"**Role:** {role_display}")
            if st.session_state.role == 'pegawai':
                st.markdown(f"**Toko:** {st.session_state.store}")
            st.divider()
        
        if st.session_state.role == 'admin':
            # Admin Menu
            with st.sidebar:
                st.markdown("### Menu Admin", help="Manajemen sistem dan toko")
                admin_menu = st.radio(
                    "Pilih Menu",
                    ["Dashboard Analisis", "Keuangan", "Biaya Operasional", "Laporan Kas", "Manajemen Toko", "Manajemen Pegawai"],
                    label_visibility="collapsed"
                )

            # Header admin
            col_title, col_logout = st.columns([8, 1])
            with col_title:
                st.markdown("## Admin Pusat Dashboard")
            with col_logout:
                if st.button("Logout", help="Logout", key="admin_logout"):
                    logout()
                    st.rerun()

            if admin_menu == "Dashboard Analisis":
                admin_dashboard.show()
            elif admin_menu == "Keuangan":
                finance_management.show()
            elif admin_menu == "Biaya Operasional":
                admin_expense.show()
            elif admin_menu == "Laporan Kas":
                cashflow_history.show()
            elif admin_menu == "Manajemen Toko":
                admin_management.show()
            elif admin_menu == "Manajemen Pegawai":
                staff_management.show()
        
        elif st.session_state.role == 'pegawai':
            # Staff Menu
            with st.sidebar:
                st.markdown("### Menu Toko", help="Operasional toko")
                main_menu = st.radio(
                    "Kategori Menu",
                    list(USER_PAGES.keys()),
                    label_visibility="collapsed"
                )
                
                if main_menu in USER_PAGES:
                    st.markdown("### Sub-Menu")
                    submenu = st.radio(
                        "Pilih Halaman",
                        list(USER_PAGES[main_menu].keys()),
                        label_visibility="collapsed",
                        key=f"submenu_{main_menu}"
                    )
                    page_function = USER_PAGES[main_menu][submenu]

            # Header halaman staff
            col_title, col_logout = st.columns([8, 1])
            with col_title:
                st.markdown(f"## {st.session_state.store} - {submenu}")
            with col_logout:
                if st.button("Logout", help="Logout", key="staff_logout"):
                    logout()
                    st.rerun()
            
            st.divider()
            page_function()

if __name__ == "__main__":
    main()
