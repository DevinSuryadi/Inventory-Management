import streamlit as st
from app.db import get_client
import datetime
import json

def show():
    st.markdown("<h1 style='color: #9b59b6;'>Retur Penjualan</h1>", unsafe_allow_html=True)

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()
        
        # Initialize cart in session state
        if 'sale_return_cart' not in st.session_state:
            st.session_state.sale_return_cart = []

        #  Customer & Warehouse Selection 
        st.markdown("### 1️⃣ Informasi Pelanggan & Gudang")
        
        col_cust, col_wh = st.columns(2)
        
        with col_cust:
            customer_name = st.text_input(
                "Nama Pelanggan",
                placeholder="Masukkan nama pelanggan...",
                key="sr_customer"
            )
        
        with col_wh:
            warehouse_resp = supabase.table("warehouse_list").select("warehouseid, name").eq("store", store).order("name").execute()
            warehouse_map = {w['name']: w['warehouseid'] for w in warehouse_resp.data or []}
            
            if not warehouse_map:
                st.error("Belum ada gudang terdaftar untuk toko ini.")
                return
            
            selected_warehouse_name = st.selectbox(
                "Simpan ke Gudang", 
                options=warehouse_map.keys(), 
                key="sr_warehouse",
                help="Barang yang diretur akan masuk ke gudang ini"
            )

        st.divider()

        #  Add Items to Cart 
        st.markdown("### 2️⃣ Tambah Barang yang Diretur")
        
        products_resp = supabase.table("product").select("productid, productname, type, size, brand, harga, quantity").eq("store", store).order("productname").execute()
        products = products_resp.data or []
        
        if not products:
            st.info("Belum ada produk terdaftar di toko ini.")
            return
        
        def product_label(p):
            name = p['productname']
            size = p.get('size', '')
            ptype = p.get('type', '')
            stock = p.get('quantity', 0)
            label = name
            if size:
                label += f" ({size})"
            if ptype:
                label += f" - {ptype}"
            label += f" [Stok: {stock}]"
            return label
        
        product_map = {product_label(p): p for p in products}
        
        col_prod, col_qty, col_price = st.columns([3, 1, 2])
        
        with col_prod:
            selected_product_label = st.selectbox(
                "Pilih Produk yang Diretur",
                options=product_map.keys(),
                key="sr_product_select",
                placeholder="Cari produk..."
            )
        
        with col_qty:
            quantity = st.number_input("Jumlah", min_value=1, value=1, key="sr_qty")
        
        with col_price:
            # Auto-fill dengan harga jual jika ada
            default_price = 0
            if selected_product_label:
                default_price = product_map[selected_product_label].get('harga', 0) or 0
            price = st.number_input("Harga Satuan (Rp)", min_value=0, value=int(default_price), step=100, key="sr_price")
        
        col_add, col_clear = st.columns([3, 1])
        with col_add:
            if st.button("➕ Tambah ke Daftar Retur", use_container_width=True, type="primary", key="sr_add"):
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
                    st.session_state.sale_return_cart.append(new_item)
                    st.success(f"✅ {product_data['productname']} ditambahkan!")
                    st.rerun()
        
        with col_clear:
            if st.button("Kosongkan", use_container_width=True, key="sr_clear"):
                st.session_state.sale_return_cart = []
                st.rerun()

        st.divider()

        #  Cart Display 
        st.markdown("### 3️⃣ Daftar Barang Retur")
        
        cart = st.session_state.sale_return_cart
        
        if not cart:
            st.info("Belum ada barang dalam daftar retur. Tambahkan barang di atas.")
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
                    if st.button("❌", key=f"remove_sr_{idx}"):
                        st.session_state.sale_return_cart.pop(idx)
                        st.rerun()
                total_amount += item['subtotal']
            
            st.divider()
            st.markdown(f"## Total Retur: Rp {total_amount:,.0f}")

        st.divider()

        #  Return Details 
        if cart:
            st.markdown("### 4️⃣ Detail Retur")
            
            with st.form("sale_return_form", border=True):
                col_type, col_reason = st.columns(2)
                
                with col_type:
                    return_type = st.selectbox(
                        "Jenis Retur",
                        options=["refund", "replacement", "store_credit"],
                        format_func=lambda x: {
                            "refund": "Refund",
                            "replacement": "Replacement",
                            "store_credit": "Store Credit"
                        }.get(x, x)
                    )
                
                with col_reason:
                    reason = st.selectbox(
                        "Alasan Retur",
                        options=[
                            "Barang rusak",
                            "Barang tidak sesuai",
                            "Pelanggan berubah pikiran",
                            "Ukuran tidak cocok",
                            "Lainnya"
                        ]
                    )
                
                col_date, col_time = st.columns(2)
                with col_date:
                    return_date = st.date_input("Tanggal Retur", value=datetime.date.today())
                with col_time:
                    return_time = st.time_input("Waktu", value=datetime.datetime.now().time())
                
                # Account selection for refund
                accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
                account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
                
                selected_account = None
                if return_type == "refund" and account_map:
                    selected_account = st.selectbox("Bayar Refund dari Rekening", options=account_map.keys())
                    st.warning("⚠️ Saldo rekening akan dikurangi untuk refund ke pelanggan.")
                
                description = st.text_area("Catatan Tambahan", placeholder="Deskripsi tambahan untuk retur...")
                
                st.divider()
                
                confirm = st.checkbox("Data retur ini benar")
                
                submitted = st.form_submit_button(
                    "Proses Retur Penjualan", 
                    use_container_width=True, 
                    type="primary"
                )

                if submitted:
                    if not confirm:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                        st.stop()
                        
                    return_datetime = datetime.datetime.combine(return_date, return_time)
                    
                    # Prepare items for RPC
                    items_json = json.dumps([{
                        'product_id': item['product_id'],
                        'quantity': item['qty'],
                        'price': item['price']
                    } for item in cart])
                    
                    try:
                        result = supabase.rpc("record_sale_return", {
                            "p_store": store,
                            "p_warehouse_id": warehouse_map[selected_warehouse_name],
                            "p_customer_name": customer_name if customer_name else None,
                            "p_items": items_json,
                            "p_return_type": return_type,
                            "p_reason": reason,
                            "p_description": description,
                            "p_account_id": account_map.get(selected_account) if selected_account else None,
                            "p_return_date": return_datetime.isoformat(),
                            "p_created_by": st.session_state.get("username", "system")
                        }).execute()
                        
                        st.success(f"✅ Retur penjualan berhasil dicatat! ID: {result.data}")
                        st.session_state.sale_return_cart = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal memproses retur: {e}")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
