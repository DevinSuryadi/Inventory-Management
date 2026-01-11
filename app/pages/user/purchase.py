import streamlit as st
from app.db import get_client
import datetime
import json

def show():
    st.markdown("<h1 style='color: #1f77b4;'>Pencatatan Pembelian</h1>", unsafe_allow_html=True)

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()
        
        # Initialize cart in session state
        if 'purchase_cart' not in st.session_state:
            st.session_state.purchase_cart = []

        # Supplier & Warehouse Selection
        st.markdown("### 1️⃣ Pilih Supplier & Gudang")
        
        supplier_resp = supabase.table("supplier").select("supplierid, suppliername").order("suppliername").execute()
        warehouse_resp = supabase.table("warehouse_list").select("warehouseid, name").order("name").execute()
        
        supplier_map = {s['suppliername']: s['supplierid'] for s in supplier_resp.data or []}
        warehouse_map = {w['name']: w['warehouseid'] for w in warehouse_resp.data or []}

        if not supplier_map:
            st.error("Belum ada supplier terdaftar. Silakan daftar supplier terlebih dahulu.")
            return
        if not warehouse_map:
            st.error("Belum ada gudang terdaftar. Silakan daftar gudang terlebih dahulu.")
            return
        
        col_sup, col_wh = st.columns(2)
        with col_sup:
            selected_supplier_name = st.selectbox("Supplier", options=supplier_map.keys(), key="purch_supplier")
        with col_wh:
            selected_warehouse_name = st.selectbox("Simpan ke Gudang", options=warehouse_map.keys(), key="purch_warehouse")

        st.divider()

        # Add Items to Cart
        st.markdown("### 2️⃣ Tambah Barang ke Keranjang")
        
        products_resp = supabase.table("product").select("productid, productname, type, brand, quantity").eq("store", store).order("productname").execute()
        products = products_resp.data or []
        
        if not products:
            st.info("Pastikan data produk sudah terdaftar di menu 'Daftar Stok'.")
            return
        
        product_map = {f"{p['productname']} ({p.get('type', '-')}) - Stok: {p.get('quantity', 0)}": p for p in products}
        
        col_prod, col_qty, col_price = st.columns([3, 1, 2])
        
        with col_prod:
            selected_product_label = st.selectbox(
                "Pilih Produk",
                options=product_map.keys(),
                key="purch_product_select",
                placeholder="Cari produk..."
            )
        
        with col_qty:
            quantity = st.number_input("Jumlah", min_value=1, value=1, key="purch_qty")
        
        with col_price:
            price = st.number_input("Harga Satuan (Rp)", min_value=0, step=100, key="purch_price")
        
        col_add, col_clear = st.columns([3, 1])
        with col_add:
            if st.button("➕ Tambah ke Keranjang", use_container_width=True, type="primary"):
                if selected_product_label and quantity > 0:
                    product_data = product_map[selected_product_label]
                    new_item = {
                        'product_id': product_data['productid'],
                        'name': product_data['productname'],
                        'type': product_data.get('type', '-'),
                        'qty': quantity,
                        'price': price,
                        'subtotal': quantity * price
                    }
                    st.session_state.purchase_cart.append(new_item)
                    st.success(f"✅ {product_data['productname']} ditambahkan!")
                    st.rerun()
        
        with col_clear:
            if st.button("Kosongkan", use_container_width=True):
                st.session_state.purchase_cart = []
                st.rerun()

        st.divider()

        # Cart Display
        st.markdown("### 3️⃣ Keranjang Belanja")
        
        cart = st.session_state.purchase_cart
        
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
                    if st.button("❌", key=f"remove_purch_{idx}"):
                        st.session_state.purchase_cart.pop(idx)
                        st.rerun()
                total_amount += item['subtotal']
            
            st.divider()
            st.markdown(f"## Total: Rp {total_amount:,.0f}")

        st.divider()

        # Payment & Confirm
        if cart:
            st.markdown("### 4️⃣ Pembayaran & Konfirmasi")
            
            with st.form("purchase_form", border=True):
                col_date, col_time = st.columns(2)
                with col_date:
                    transaction_date = st.date_input("Tanggal Transaksi", value=datetime.date.today())
                with col_time:
                    transaction_time = st.time_input("Waktu Transaksi", value=datetime.datetime.now().time())
                
                col_payment, col_account = st.columns(2)
                with col_payment:
                    payment_type = st.radio("Metode Pembayaran", ["Cash", "Credit"], horizontal=True)
                    payment_type_value = "cash" if "Cash" in payment_type else "credit"
                
                accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
                account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
                
                selected_account_name = None
                due_date = None
                
                with col_account:
                    if payment_type_value == "cash" and account_map:
                        selected_account_name = st.selectbox("Bayar dari Rekening", options=account_map.keys())
                    elif payment_type_value == "credit":
                        due_date = st.date_input("Jatuh Tempo (TOP)", value=datetime.date.today() + datetime.timedelta(days=30))
                    elif not account_map and payment_type_value == "cash":
                        st.warning("Tidak ada rekening cash tersedia")

                description = st.text_area("Catatan/Deskripsi (opsional)")
                
                st.divider()
                
                # Confirmation
                st.warning("⚠️ Pastikan semua data sudah benar sebelum menyimpan transaksi.")
                confirm = st.checkbox("Data transaksi ini benar")
                
                submitted = st.form_submit_button("Simpan Transaksi Pembelian", use_container_width=True, type="primary")
                if submitted:
                    if not confirm:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                        st.stop()
                        
                    transaction_datetime = datetime.datetime.combine(transaction_date, transaction_time)
                    total_amount = sum(item['subtotal'] for item in cart)
                    
                    # Prepare items for RPC
                    items_json = json.dumps([{
                        'product_id': item['product_id'],
                        'quantity': item['qty'],
                        'price': item['price']
                    } for item in cart])
                    
                    try:
                        result = supabase.rpc("record_purchase_transaction_multi", {
                            "p_store": store,
                            "p_supplier_id": supplier_map[selected_supplier_name],
                            "p_warehouse_id": warehouse_map[selected_warehouse_name],
                            "p_items": items_json,
                            "p_payment_type": payment_type_value,
                            "p_due_date": due_date.isoformat() if due_date else None,
                            "p_account_id": account_map.get(selected_account_name) if selected_account_name else None,
                            "p_description": description,
                            "p_transaction_date": transaction_datetime.isoformat(),
                            "p_created_by": st.session_state.get("username", "system")
                        }).execute()
                        
                        st.success(f"✅ Transaksi pembelian berhasil dicatat! ID: {result.data}")
                        st.session_state.purchase_cart = []
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan transaksi: {e}")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
