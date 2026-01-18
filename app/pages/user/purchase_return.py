import streamlit as st
from app.db import get_client
import datetime
import json

def show():
    st.markdown("<h1 style='color: #e74c3c;'>Retur Pembelian</h1>", unsafe_allow_html=True)

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()
        
        if 'purchase_return_cart' not in st.session_state:
            st.session_state.purchase_return_cart = []

        st.markdown("### 1️⃣ Pilih Supplier & Gudang")
        
        col_sup, col_wh, col_invoice = st.columns(3)
        
        with col_sup:
            supplier_resp = supabase.table("supplier").select("supplierid, suppliername").eq("store", store).order("suppliername").execute()
            supplier_map = {s['suppliername']: s['supplierid'] for s in supplier_resp.data or []}
            
            if not supplier_map:
                st.error("Belum ada supplier terdaftar untuk toko ini.")
                return
            
            selected_supplier_name = st.selectbox(
                "Pilih Supplier", 
                options=supplier_map.keys(), 
                key="pr_supplier",
                placeholder="Pilih supplier untuk retur..."
            )
        
        with col_wh:
            warehouse_resp = supabase.table("warehouse_list").select("warehouseid, name").eq("store", store).order("name").execute()
            warehouse_map = {w['name']: w['warehouseid'] for w in warehouse_resp.data or []}
            
            if not warehouse_map:
                st.error("Belum ada gudang terdaftar untuk toko ini.")
                return
            
            selected_warehouse_name = st.selectbox(
                "Gudang Asal Barang", 
                options=warehouse_map.keys(), 
                key="pr_warehouse"
            )
        
        with col_invoice:
            invoice_number = st.text_input("No. Nota Retur (opsional)", key="pr_invoice", placeholder="Contoh: RTR-001")

        st.divider()

        # Add Items to Cart
        st.markdown("### 2️⃣ Tambah Barang ke Retur")
        
        products_resp = supabase.table("product").select("productid, productname, type, size, brand, quantity").eq("store", store).order("productname").execute()
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
                "Pilih Produk",
                options=product_map.keys(),
                key="pr_product_select",
                placeholder="Cari produk..."
            )
        
        with col_qty:
            quantity = st.number_input("Jumlah", min_value=1, value=1, key="pr_qty")
        
        with col_price:
            price = st.number_input("Harga Satuan (Rp)", min_value=0, step=100, key="pr_price")
        
        col_add, col_clear = st.columns([3, 1])
        with col_add:
            if st.button("➕ Tambah ke Daftar Retur", use_container_width=True, type="primary"):
                if selected_product_label and quantity > 0:
                    product_data = product_map[selected_product_label]
                    
                    stock_resp = supabase.table("product_warehouse").select("quantity").eq(
                        "productid", product_data['productid']
                    ).eq("warehouseid", warehouse_map[selected_warehouse_name]).execute()
                    
                    current_stock = stock_resp.data[0]['quantity'] if stock_resp.data else 0
                    
                    if quantity > current_stock:
                        st.error(f"Stok tidak mencukupi! Stok tersedia: {current_stock}")
                    else:
                        new_item = {
                            'product_id': product_data['productid'],
                            'name': product_data['productname'],
                            'type': product_data.get('type', '-'),
                            'qty': quantity,
                            'price': price,
                            'subtotal': quantity * price
                        }
                        st.session_state.purchase_return_cart.append(new_item)
                        st.success(f"✅ {product_data['productname']} ditambahkan!")
                        st.rerun()
        
        with col_clear:
            if st.button("Kosongkan", use_container_width=True):
                st.session_state.purchase_return_cart = []
                st.rerun()

        st.divider()

        # Cart Display
        st.markdown("### 3️⃣ Daftar Barang Retur")
        
        cart = st.session_state.purchase_return_cart
        
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
                    if st.button("❌", key=f"remove_pr_{idx}"):
                        st.session_state.purchase_return_cart.pop(idx)
                        st.rerun()
                total_amount += item['subtotal']
            
            st.divider()
            st.markdown(f"## Total Retur: Rp {total_amount:,.0f}")

        st.divider()

        # Return Details
        if cart:
            st.markdown("### 4️⃣ Detail Retur")
            
            total_cart = sum(item['subtotal'] for item in cart)
            
            supplier_id = supplier_map[selected_supplier_name]
            try:
                debt_resp = supabase.rpc("get_supplier_debt_total", {
                    "p_store": store, 
                    "p_supplier_id": supplier_id
                }).execute()
                supplier_total_debt = debt_resp.data if debt_resp.data else 0
            except:
                supplier_total_debt = 0
            
            with st.form("purchase_return_form", border=True):
                col_type, col_reason = st.columns(2)
                
                with col_type:
                    return_type = st.selectbox(
                        "Jenis Retur",
                        options=["refund", "replacement", "credit_note"],
                        format_func=lambda x: {
                            "refund": "Refund",
                            "replacement": "Replacement",
                            "credit_note": "Credit Note"
                        }.get(x, x)
                    )
                    
                    if return_type == "refund":
                        st.info("Supplier mengembalikan uang ke rekening toko.")
                    elif return_type == "replacement":
                        st.info("Supplier akan mengganti dengan barang baru. Tidak ada perubahan kas.")
                    elif return_type == "credit_note":
                        st.info(f"Nilai retur akan memotong hutang supplier ini.")
                        st.write(f"**Hutang ke supplier ini:** Rp {supplier_total_debt:,.0f}")
                        if total_cart > supplier_total_debt:
                            st.error(f"⚠️ Total retur (Rp {total_cart:,.0f}) melebihi hutang (Rp {supplier_total_debt:,.0f})!")
                
                with col_reason:
                    reason = st.selectbox(
                        "Alasan Retur",
                        options=[
                            "Barang rusak",
                            "Barang tidak sesuai pesanan",
                            "Kelebihan order",
                            "Lainnya"
                        ]
                    )
                
                col_date, col_time = st.columns(2)
                with col_date:
                    return_date = st.date_input("Tanggal Retur", value=datetime.date.today())
                with col_time:
                    return_time = st.time_input("Waktu", value=datetime.datetime.now().time())
                
                accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
                account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
                
                selected_account = None
                if return_type == "refund" and account_map:
                    selected_account = st.selectbox("Terima Refund ke Rekening", options=account_map.keys())
                
                description = st.text_area("Catatan Tambahan", placeholder="Deskripsi tambahan untuk retur...")
                
                st.divider()
                
                # Confirmation section
                st.warning("⚠️ Pastikan data sudah benar. Transaksi retur akan mengurangi stok barang di gudang.")
                confirm = st.checkbox("Data retur ini benar")
                
                submitted = st.form_submit_button(
                    "Proses Retur Pembelian", 
                    use_container_width=True, 
                    type="primary"
                )

                if submitted:
                    if not confirm:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                        st.stop()
                        
                    return_datetime = datetime.datetime.combine(return_date, return_time)
                    
                    items_json = json.dumps([{
                        'product_id': item['product_id'],
                        'quantity': item['qty'],
                        'price': item['price']
                    } for item in cart])
                    
                    try:
                        result = supabase.rpc("record_purchase_return", {
                            "p_store": store,
                            "p_supplier_id": supplier_map[selected_supplier_name],
                            "p_warehouse_id": warehouse_map[selected_warehouse_name],
                            "p_items": items_json,
                            "p_return_type": return_type,
                            "p_reason": reason,
                            "p_description": description,
                            "p_account_id": account_map.get(selected_account) if selected_account else None,
                            "p_return_date": return_datetime.isoformat(),
                            "p_created_by": st.session_state.get("username", "system"),
                            "p_invoice_number": invoice_number if invoice_number else None
                        }).execute()
                        
                        st.success(f"✅ Retur pembelian berhasil dicatat! ID: {result.data}")
                        st.session_state.purchase_return_cart = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal memproses retur: {e}")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
