import streamlit as st
from app.db import get_client
import datetime

def show():
    st.markdown("<h1 style='color: #1f77b4;'>Pencatatan Pembelian</h1>", unsafe_allow_html=True)

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()

        # ========== SECTION 1: Product Selection ==========
        st.markdown("<h3>Pilih Produk</h3>", unsafe_allow_html=True)
        
        products_resp = supabase.table("product").select("productid, productname").eq("store", store).order("productname").execute()
        products = products_resp.data or []
        
        if not products:
            st.info("Pastikan data produk sudah terdaftar di menu 'Daftar Stok'.")
            return
            
        product_map = {p['productname']: p['productid'] for p in products}
        selected_product_name = st.selectbox(
            "Pilih Produk", 
            options=product_map.keys(), 
            index=None, 
            placeholder="Cari dan pilih produk yang akan dibeli..."
        )

        if selected_product_name:
            product_id = product_map[selected_product_name]
            
            # Fetch product info
            try:
                info_resp = supabase.rpc("get_product_purchase_info", {"p_product_id": product_id}).execute()
                product_info = info_resp.data
                
                avg_price = product_info.get('average_price', 0)
                warehouse_stock_list = product_info.get('warehouse_stock', [])
            except Exception as e:
                st.error(f"Gagal mengambil informasi produk: {e}")
                return

            st.divider()
            
            # ========== SECTION 2: Product Summary ==========
            st.markdown("<h3>Ringkasan Produk</h3>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Harga Rata-rata", f"Rp {avg_price:,.0f}")
            with col2:
                total_warehouse_stock = sum([item['quantity'] for item in warehouse_stock_list])
                st.metric("Total Stok", f"{total_warehouse_stock} unit")
            with col3:
                st.metric("Lokasi Gudang", f"{len(warehouse_stock_list)} tempat")
            
            # Show warehouse stock details
            if warehouse_stock_list:
                st.markdown("**Distribusi Stok per Gudang:**")
                stock_info = ", ".join([f"🏭 {item['warehouse_name']}: {item['quantity']} unit" for item in warehouse_stock_list])
                st.info(stock_info)
            else:
                st.info("Produk ini belum memiliki stok di gudang manapun.")
            
            st.divider()
            
            # ========== SECTION 3: Purchase Form ==========
            st.markdown("<h3>Detail Pembelian</h3>", unsafe_allow_html=True)

            with st.form("purchase_form", border=True):
                # Row 1: Quantity and Price
                col_qty, col_price = st.columns(2)
                with col_qty:
                    quantity = st.number_input("Jumlah Pembelian (unit)", min_value=1, step=1, value=1)
                with col_price:
                    price = st.number_input("Harga Satuan (Rp)", min_value=0, step=100, format="%d")
                
                # Display total
                total_price = quantity * price
                st.metric("Total Pembelian", f"Rp {total_price:,.0f}", delta=None)
                
                # Row 2: Date and Time
                col_date, col_time = st.columns(2)
                with col_date:
                    transaction_date = st.date_input("Tanggal Transaksi", value=datetime.date.today())
                with col_time:
                    transaction_time = st.time_input("Waktu Transaksi", value=datetime.datetime.now().time())
                
                st.divider()
                
                # Row 3: Supplier and Warehouse
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

                col_supplier, col_warehouse = st.columns(2)
                with col_supplier:
                    selected_supplier_name = st.selectbox("Supplier", options=supplier_map.keys())
                with col_warehouse:
                    selected_warehouse_name = st.selectbox("Simpan ke Gudang", options=warehouse_map.keys())
                
                # Account selection for cash payment
                accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
                account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
                
                col_payment, col_account = st.columns(2)
                with col_payment:
                    payment_type = st.radio("Metode Pembayaran", ["💵 Cash", "🏦 Credit"], horizontal=True)
                    payment_type = "cash" if "Cash" in payment_type else "credit"
                
                selected_account_name = None
                with col_account:
                    if payment_type == "cash" and account_map:
                        selected_account_name = st.selectbox("Bayar dari Rekening", options=account_map.keys())
                    elif not account_map and payment_type == "cash":
                        st.warning("Tidak ada rekening cash tersedia")

                description = st.text_area("Catatan/Deskripsi (opsional)", placeholder="Contoh: Pembayaran dimuka, order khusus, dsb...")
                
                st.divider()
                submitted = st.form_submit_button("Simpan Transaksi Pembelian", use_container_width=True, type="primary")

                if submitted:
                    # Validation
                    if quantity <= 0:
                        st.error("Jumlah pembelian harus lebih dari 0")
                        return
                    if price < 0:
                        st.error("Harga tidak boleh negatif")
                        return
                    
                    transaction_datetime = datetime.datetime.combine(transaction_date, transaction_time)
                    
                    try:
                        params = {
                            "p_product_id": product_id,
                            "p_supplier_id": supplier_map[selected_supplier_name],
                            "p_warehouse_id": warehouse_map[selected_warehouse_name],
                            "p_quantity": quantity,
                            "p_price": price,
                            "p_payment_type": payment_type,
                            "p_description": description,
                            "p_store": store,
                            "p_transaction_date": transaction_datetime.isoformat(),
                            "p_account_id": account_map.get(selected_account_name) if selected_account_name else None
                        }
                        supabase.rpc("record_purchase_transaction", params).execute()
                        st.success("Transaksi pembelian berhasil dicatat!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan transaksi: {e}")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
