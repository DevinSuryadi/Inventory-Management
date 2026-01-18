import streamlit as st
from app.db import get_client
import datetime
import json

def show():
    st.markdown("<h1 style='color: #27ae60;'>Pencatatan Penjualan</h1>", unsafe_allow_html=True)

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()
        
        # Create tabs for regular sale and other sale
        tab_regular, tab_other = st.tabs(["Penjualan Stok", "Penjualan Lainnya"])
        
        # ===== TAB 1: PENJUALAN STOK (REGULAR) =====
        with tab_regular:
            show_regular_sale(supabase, store)
        
        # ===== TAB 2: PENJUALAN LAINNYA (NON-STOK) =====
        with tab_other:
            show_other_sale(supabase, store)
    
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")


def show_regular_sale(supabase, store):
    """Penjualan regular dengan stok"""
    
    # Initialize cart in session state
    if 'sale_cart' not in st.session_state:
        st.session_state.sale_cart = []

    # Warehouse Selection
    st.markdown("### 1️⃣ Pilih Gudang & Pelanggan")
    
    warehouse_resp = supabase.table("warehouse_list").select("warehouseid, name").eq("store", store).order("name").execute()
    warehouse_map = {w['name']: w['warehouseid'] for w in warehouse_resp.data or []}
    
    if not warehouse_map:
        st.error("Belum ada gudang terdaftar.")
        return
    
    col_wh, col_cust, col_invoice = st.columns(3)
    with col_wh:
        selected_warehouse_name = st.selectbox("Gudang Asal", options=warehouse_map.keys(), key="sale_warehouse")
    with col_cust:
        customer_name = st.text_input("Nama Pelanggan (opsional)", key="sale_customer")
    with col_invoice:
        invoice_number = st.text_input("No. Nota (opsional)", key="sale_invoice", placeholder="Contoh: INV-001")

    st.divider()

    # Add Items to Cart
    st.markdown("### 2️⃣ Tambah Barang ke Keranjang")
    
    products_resp = supabase.table("product").select("productid, productname, type, size, brand, harga").eq("store", store).order("productname").execute()
    products = products_resp.data or []
    
    if not products:
        st.info("Belum ada produk yang terdaftar untuk toko ini.")
        return
    
    def product_label(p):
        name = p['productname']
        size = p.get('size', '')
        ptype = p.get('type', '')
        label = name
        if size:
            label += f" ({size})"
        if ptype:
            label += f" - {ptype}"
        return label
    
    product_map = {product_label(p): p for p in products}
    
    col_prod, col_qty, col_price = st.columns([3, 1, 2])
    
    with col_prod:
        selected_product_label = st.selectbox(
            "Pilih Produk",
            options=product_map.keys(),
            key="sale_product_select",
            placeholder="Cari produk..."
        )
    
    # Get stock for selected product
    selected_product_stock = 0
    if selected_product_label:
        product_data = product_map[selected_product_label]
        stock_resp = supabase.table("product_warehouse").select("quantity").eq(
            "productid", product_data['productid']
        ).eq("warehouseid", warehouse_map[selected_warehouse_name]).execute()
        selected_product_stock = stock_resp.data[0]['quantity'] if stock_resp.data else 0
        
        # Show stock info
        if selected_product_stock > 0:
            st.info(f"Stok tersedia di gudang: **{selected_product_stock} unit**")
        else:
            st.warning("⚠️ Stock tidak ada di gudang.")
    
    with col_qty:
        quantity = st.number_input("Jumlah", min_value=1, value=1, max_value=max(1, selected_product_stock), key="sale_qty")
    
    with col_price:
        default_price = product_map[selected_product_label].get('harga', 0) if selected_product_label else 0
        price = st.number_input("Harga Jual (Rp)", min_value=0, value=int(default_price or 0), step=100, key="sale_price")
    
    col_add, col_clear = st.columns([3, 1])
    with col_add:
        if st.button("➕ Tambah ke Keranjang", use_container_width=True, type="primary", key="sale_add_btn"):
            if selected_product_label and quantity > 0 and selected_product_stock > 0:
                product_data = product_map[selected_product_label]
                
                total_in_cart = sum([item['qty'] for item in st.session_state.sale_cart if item['product_id'] == product_data['productid']])
                if total_in_cart + quantity > selected_product_stock:
                    st.error(f"Stok tidak mencukupi! Tersedia: {selected_product_stock}, di keranjang: {total_in_cart}")
                else:
                    new_item = {
                        'product_id': product_data['productid'],
                        'name': product_data['productname'],
                        'type': product_data.get('type', '-'),
                        'qty': quantity,
                        'price': price,
                        'subtotal': quantity * price
                    }
                    st.session_state.sale_cart.append(new_item)
                    st.success(f"✅ {product_data['productname']} ditambahkan!")
                    st.rerun()
            elif selected_product_stock == 0:
                st.error("Tidak bisa menambahkan produk dengan stok 0!")
    
    with col_clear:
        if st.button("Kosongkan", use_container_width=True, key="sale_clear_btn"):
            st.session_state.sale_cart = []
            st.rerun()

    st.divider()

    # Cart Display
    st.markdown("### 3️⃣ Keranjang Penjualan")
    
    cart = st.session_state.sale_cart
    
    if not cart:
        st.info("Keranjang kosong. Tambahkan produk di atas.")
    else:
        total_amount = 0
        for idx, item in enumerate(cart):
            col1, col2, col3, col4, col5 = st.columns([3, 1, 2, 2, 1])
            with col1:
                st.write(f"**{item['name']}** ({item['type']})")
            with col2:
                st.write(f"{item['qty']} unit")
            with col3:
                st.write(f"@ Rp {item['price']:,.0f}")
            with col4:
                st.write(f"**Rp {item['subtotal']:,.0f}**")
            with col5:
                if st.button("❌", key=f"remove_sale_{idx}"):
                    st.session_state.sale_cart.pop(idx)
                    st.rerun()
            total_amount += item['subtotal']
        
        st.divider()
        st.markdown(f"## Total: Rp {total_amount:,.0f}")

    st.divider()

    # Payment & Confirm
    if cart:
        st.markdown("### 4️⃣ Pembayaran & Konfirmasi")
        
        col_payment, col_account = st.columns(2)
        with col_payment:
            payment_type = st.radio("Metode Pembayaran", ["Cash", "Credit"], horizontal=True, key="sale_payment_type")
            payment_type_value = "cash" if "Cash" in payment_type else "credit"
        
        accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
        account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
        
        selected_account_name = None
        due_date = None
        
        with col_account:
            if payment_type_value == "cash":
                if account_map:
                    selected_account_name = st.selectbox("Terima ke Rekening", options=list(account_map.keys()), key="sale_account")
                else:
                    st.warning("Tidak ada rekening cash tersedia")
            else:
                due_date = st.date_input("Jatuh Tempo (TOP)", value=datetime.date.today() + datetime.timedelta(days=30), key="sale_due_date")
        
        with st.form("sale_form", border=True):
            col_date, col_time = st.columns(2)
            with col_date:
                transaction_date = st.date_input("Tanggal Transaksi", value=datetime.date.today())
            with col_time:
                transaction_time = st.time_input("Waktu Transaksi", value=datetime.datetime.now().time())

            description = st.text_area("Catatan/Deskripsi (opsional)")
            
            st.divider()
            
            st.warning("⚠️ Pastikan semua data sudah benar sebelum menyimpan transaksi.")
            confirm = st.checkbox("Data transaksi ini benar")
            
            submitted = st.form_submit_button("Simpan Transaksi Penjualan", use_container_width=True, type="primary")

            if submitted:
                if not confirm:
                    st.error("Harap centang konfirmasi terlebih dahulu!")
                    st.stop()
                    
                transaction_datetime = datetime.datetime.combine(transaction_date, transaction_time)
                total_amount = sum(item['subtotal'] for item in cart)
                
                items_list = [{
                    'product_id': item['product_id'],
                    'quantity': item['qty'],
                    'price': item['price']
                } for item in cart]
                
                try:
                    result = supabase.rpc("record_sale_transaction_multi", {
                        "p_store": store,
                        "p_warehouse_id": warehouse_map[selected_warehouse_name],
                        "p_items": json.dumps(items_list),
                        "p_payment_type": payment_type_value,
                        "p_customer_name": customer_name if customer_name else None,
                        "p_due_date": due_date.isoformat() if due_date else None,
                        "p_account_id": account_map.get(selected_account_name) if selected_account_name else None,
                        "p_description": description,
                        "p_transaction_date": transaction_datetime.isoformat(),
                        "p_created_by": st.session_state.get("username", "system"),
                        "p_invoice_number": invoice_number if invoice_number else None
                    }).execute()
                    
                    st.success(f"✅ Transaksi penjualan berhasil dicatat! ID: {result.data}")
                    st.session_state.sale_cart = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan transaksi: {e}")


def show_other_sale(supabase, store):
    
    if 'other_sale_cart' not in st.session_state:
        st.session_state.other_sale_cart = []
    
    st.markdown("### 1️⃣ Info Pelanggan & Nota")
    
    col1, col2 = st.columns(2)
    with col1:
        other_customer_name = st.text_input("Nama Pelanggan (opsional)", key="other_sale_customer")
    with col2:
        other_invoice_number = st.text_input("No. Nota (opsional)", key="other_sale_invoice", placeholder="Contoh: INV-001")
    
    st.divider()
    
    st.markdown("### 2️⃣ Tambah Barang")
    
    col_name, col_type, col_qty, col_price = st.columns([3, 2, 1, 2])
    
    with col_name:
        item_name = st.text_input("Nama Barang", key="other_sale_item_name", placeholder="Contoh: Jasa Pasang")
    with col_type:
        item_type = st.text_input("Jenis/Kategori", key="other_sale_item_type", placeholder="Contoh: Jasa")
    with col_qty:
        other_quantity = st.number_input("Jumlah", min_value=1, value=1, key="other_sale_qty")
    with col_price:
        other_price = st.number_input("Harga Satuan (Rp)", min_value=0, step=1000, key="other_sale_price")
    
    col_add, col_clear = st.columns([3, 1])
    with col_add:
        if st.button("➕ Tambah ke Keranjang", use_container_width=True, type="primary", key="other_sale_add_btn"):
            if item_name and other_quantity > 0 and other_price > 0:
                new_item = {
                    'name': item_name,
                    'type': item_type or '-',
                    'qty': other_quantity,
                    'price': other_price,
                    'subtotal': other_quantity * other_price
                }
                st.session_state.other_sale_cart.append(new_item)
                st.success(f"✅ {item_name} ditambahkan!")
                st.rerun()
            else:
                st.error("Harap isi nama barang, jumlah, dan harga!")
    
    with col_clear:
        if st.button("Kosongkan", use_container_width=True, key="other_sale_clear_btn"):
            st.session_state.other_sale_cart = []
            st.rerun()
    
    st.divider()
    
    st.markdown("### 3️⃣ Keranjang Penjualan Lainnya")
    
    cart = st.session_state.other_sale_cart
    
    if not cart:
        st.info("Keranjang kosong. Tambahkan barang di atas.")
    else:
        total_amount = 0
        for idx, item in enumerate(cart):
            col1, col2, col3, col4, col5 = st.columns([3, 1, 2, 2, 1])
            with col1:
                st.write(f"**{item['name']}** ({item['type']})")
            with col2:
                st.write(f"{item['qty']} unit")
            with col3:
                st.write(f"@ Rp {item['price']:,.0f}")
            with col4:
                st.write(f"**Rp {item['subtotal']:,.0f}**")
            with col5:
                if st.button("❌", key=f"remove_other_sale_{idx}"):
                    st.session_state.other_sale_cart.pop(idx)
                    st.rerun()
            total_amount += item['subtotal']
        
        st.divider()
        st.markdown(f"## Total: Rp {total_amount:,.0f}")
    
    st.divider()
    
    if cart:
        st.markdown("### 4️⃣ Pembayaran & Konfirmasi")
        
        col_payment, col_account = st.columns(2)
        with col_payment:
            other_payment_type = st.radio("Metode Pembayaran", ["Cash", "Credit"], horizontal=True, key="other_sale_payment_type")
            other_payment_type_value = "cash" if "Cash" in other_payment_type else "credit"
        
        accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
        account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
        
        other_selected_account_name = None
        other_due_date = None
        
        with col_account:
            if other_payment_type_value == "cash":
                if account_map:
                    other_selected_account_name = st.selectbox("Terima ke Rekening", options=list(account_map.keys()), key="other_sale_account")
                else:
                    st.warning("Tidak ada rekening cash tersedia")
            else:
                other_due_date = st.date_input("Jatuh Tempo (TOP)", value=datetime.date.today() + datetime.timedelta(days=30), key="other_sale_due_date")
        
        with st.form("other_sale_form", border=True):
            col_date, col_time = st.columns(2)
            with col_date:
                other_transaction_date = st.date_input("Tanggal Transaksi", value=datetime.date.today(), key="other_sale_date")
            with col_time:
                other_transaction_time = st.time_input("Waktu Transaksi", value=datetime.datetime.now().time(), key="other_sale_time")

            other_description = st.text_area("Catatan/Deskripsi (opsional)", key="other_sale_desc")
            
            st.divider()
            
            st.warning("⚠️ Pastikan semua data sudah benar sebelum menyimpan transaksi.")
            other_confirm = st.checkbox("Data transaksi ini benar", key="other_sale_confirm")
            
            other_submitted = st.form_submit_button("Simpan Penjualan Lainnya", use_container_width=True, type="primary")

            if other_submitted:
                if not other_confirm:
                    st.error("Harap centang konfirmasi terlebih dahulu!")
                    st.stop()
                
                other_transaction_datetime = datetime.datetime.combine(other_transaction_date, other_transaction_time)
                
                try:
                    for item in cart:
                        result = supabase.rpc("record_other_sale", {
                            "p_store": store,
                            "p_customer_name": other_customer_name if other_customer_name else None,
                            "p_item_name": item['name'],
                            "p_item_type": item['type'],
                            "p_quantity": item['qty'],
                            "p_price": item['price'],
                            "p_payment_type": other_payment_type_value,
                            "p_due_date": other_due_date.isoformat() if other_due_date else None,
                            "p_account_id": account_map.get(other_selected_account_name) if other_selected_account_name else None,
                            "p_description": other_description,
                            "p_transaction_date": other_transaction_datetime.isoformat(),
                            "p_created_by": st.session_state.get("username", "system"),
                            "p_invoice_number": other_invoice_number if other_invoice_number else None
                        }).execute()
                    
                    st.success(f"✅ Penjualan lainnya berhasil dicatat!")
                    st.session_state.other_sale_cart = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan transaksi: {e}")
