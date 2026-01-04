import streamlit as st
from app.db import get_client
import datetime

def show():
    st.markdown("<h1 style='color: #1f77b4;'>Pencatatan Penjualan</h1>", unsafe_allow_html=True)

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
            st.info("Belum ada produk yang terdaftar untuk toko ini.")
            return

        product_map = {p['productname']: p['productid'] for p in products}
        selected_product_name = st.selectbox(
            "Pilih Produk", 
            options=product_map.keys(), 
            index=None, 
            placeholder="Cari dan pilih produk yang akan dijual..."
        )
        
        if selected_product_name:
            product_id = product_map[selected_product_name]
            
            # Fetch product info
            try:
                info_resp = supabase.rpc("get_product_purchase_info", {"p_product_id": product_id}).execute()
                avg_purchase_price = info_resp.data.get('average_price', 0)
            except Exception as e:
                st.error(f"Gagal mengambil informasi produk: {e}")
                return

            stock_resp = supabase.table("product_warehouse").select(
                "quantity, warehouse_list(warehouseid, name)"
            ).eq("productid", product_id).gt("quantity", 0).execute()
            
            stock_data = stock_resp.data or []
            
            if not stock_data:
                st.warning("Stok produk ini habis di semua gudang.")
                return

            st.divider()
            
            # ========== SECTION 2: Product & Warehouse Summary ==========
            st.markdown("<h3>Ringkasan Stok</h3>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Harga Beli Rata-rata", f"Rp {avg_purchase_price:,.0f}")
            with col2:
                total_warehouse_stock = sum([item['quantity'] for item in stock_data])
                st.metric("Total Stok Tersedia", f"{total_warehouse_stock} unit")
            with col3:
                st.metric("Lokasi Gudang", f"{len(stock_data)} tempat")
            
            st.divider()
            
            # ========== SECTION 3: Sale Form ==========
            st.markdown("<h3>Detail Penjualan</h3>", unsafe_allow_html=True)

            with st.form("sale_form", border=True):
                # Row 1: Quantity and Price
                col_qty, col_price = st.columns(2)
                with col_qty:
                    quantity = st.number_input("Jumlah Dijual (unit)", min_value=1, step=1, value=1)
                with col_price:
                    price = st.number_input("Harga Jual Satuan (Rp)", min_value=0, step=100, format="%d")
                
                # Display total
                total_price = quantity * price
                st.metric("Total Penjualan", f"Rp {total_price:,.0f}", delta=None)
                
                # Row 2: Date and Warehouse
                col_date, col_wh = st.columns(2)
                with col_date:
                    transaction_date = st.date_input("Tanggal Transaksi", value=datetime.date.today())
                
                warehouse_stock_map = {
                    f"{item['warehouse_list']['name']} (Stok: {item['quantity']})" : {
                        "warehoseid": item['warehouse_list']['warehouseid'],
                        "available_qty": item['quantity']
                    } for item in stock_data
                }
                
                with col_wh:
                    selected_warehouse_label = st.selectbox("Gudang Asal", options=warehouse_stock_map.keys())
                
                col_time, col_cust = st.columns(2)
                with col_time:
                    transaction_time = st.time_input("Waktu Transaksi", value=datetime.datetime.now().time())
                with col_cust:
                    customer_name = st.text_input("Nama Pelanggan (opsional)", placeholder="Contoh: Budi, Ibu Siti, dsb...")
                
                # Validate stock availability
                available_qty = warehouse_stock_map[selected_warehouse_label]['available_qty']
                if quantity > available_qty:
                    st.error(f"Jumlah penjualan ({quantity}) melebihi stok yang tersedia ({available_qty} unit)")
                
                st.divider()
                
                # Payment section
                col_payment, col_account = st.columns(2)
                with col_payment:
                    payment_type = st.radio("Metode Pembayaran", ["💵 Cash", "🏦 Credit"], horizontal=True)
                    payment_type = "cash" if "Cash" in payment_type else "credit"

                # Account selection
                accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
                account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
                
                selected_account_name = None
                with col_account:
                    if payment_type == "cash" and account_map:
                        selected_account_name = st.selectbox("Terima ke Rekening", options=account_map.keys())
                    elif not account_map and payment_type == "cash":
                        st.warning("Tidak ada rekening cash tersedia")

                description = st.text_area("Catatan/Deskripsi (opsional)", placeholder="Contoh: Promo, retur parsial, dsb...")

                st.divider()
                submitted = st.form_submit_button("Simpan Transaksi Penjualan", use_container_width=True, type="primary")

                if submitted:
                    # Validation
                    if quantity <= 0:
                        st.error("Jumlah penjualan harus lebih dari 0")
                        return
                    if price < 0:
                        st.error("Harga tidak boleh negatif")
                        return
                    if quantity > available_qty:
                        st.error(f"Jumlah penjualan ({quantity}) melebihi stok yang tersedia ({available_qty} unit)")
                    else:
                        transaction_datetime = datetime.datetime.combine(transaction_date, transaction_time)
                        warehouse_id = warehouse_stock_map[selected_warehouse_label]['warehoseid']
                        try:
                            params = {
                                "p_product_id": product_id,
                                "p_warehouse_id": warehouse_id,
                                "p_quantity": quantity,
                                "p_price": price,
                                "p_customer_name": customer_name,
                                "p_payment_type": payment_type,
                                "p_description": description,
                                "p_store": store,
                                "p_transaction_date": transaction_datetime.isoformat(),
                                "p_account_id": account_map.get(selected_account_name) if selected_account_name else None
                            }
                            supabase.rpc("record_sale_transaction", params).execute()
                            st.success("Transaksi penjualan berhasil disimpan!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan transaksi: {e}")
    
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
