import streamlit as st
from app.db import get_client
import datetime

def show():
    st.title("Transaksi Penjualan")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()

        products_resp = supabase.table("product").select("productid, productname").eq("store", store).order("productname").execute()
        products = products_resp.data or []
        
        if not products:
            st.info("Belum ada produk yang terdaftar untuk toko ini.")
            return

        product_map = {p['productname']: p['productid'] for p in products}
        selected_product_name = st.selectbox("Pilih Produk", options=product_map.keys(), index=None, placeholder="Pilih produk yang akan dijual...")
        
        if selected_product_name:
            product_id = product_map[selected_product_name]
            
            info_resp = supabase.rpc("get_product_purchase_info", {"p_product_id": product_id}).execute()
            avg_purchase_price = info_resp.data.get('average_price', 0)

            stock_resp = supabase.table("product_warehouse").select(
                "quantity, warehouse_list(warehouseid, name)"
            ).eq("productid", product_id).gt("quantity", 0).execute()
            
            stock_data = stock_resp.data or []
            
            if not stock_data:
                st.warning("Stok produk ini habis di semua gudang.")
                return

            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                quantity = st.number_input("Jumlah Dijual", min_value=1, step=1)
            with col2:
                price = st.number_input("Harga Jual Satuan", min_value=0.0, format="%.2f")

            col3, col4 = st.columns(2)
            with col3:
                st.metric("Referensi Harga Beli Rata-rata", f"Rp {avg_purchase_price:,.2f}")
            with col4:
                total_price = quantity * price
                st.metric("Total Penjualan Saat Ini", f"Rp {total_price:,.2f}")

            st.markdown("---")

            with st.form("sale_form"):
                st.subheader("Detail Transaksi")

                col_tgl, col_jam = st.columns(2)
                with col_tgl:
                    transaction_date = st.date_input("Tanggal Transaksi", value=datetime.date.today())
                with col_jam:
                    transaction_time = st.time_input("Waktu Transaksi", value=datetime.datetime.now().time())

                warehouse_stock_map = {
                    f"{item['warehouse_list']['name']} (Stok: {item['quantity']})": {
                        "warehouseid": item['warehouse_list']['warehouseid'],
                        "available_qty": item['quantity']
                    } for item in stock_data
                }
                selected_warehouse_label = st.selectbox("Pilih Gudang Asal", options=warehouse_stock_map.keys())
                
                available_qty = warehouse_stock_map[selected_warehouse_label]['available_qty']
                if quantity > available_qty:
                    st.error(f"Jumlah penjualan ({quantity}) melebihi stok yang tersedia di gudang ini ({available_qty}).")
                
                customer_name = st.text_input("Nama Pelanggan (opsional)")
                payment_type = st.radio("Metode Pembayaran", ["cash", "credit"], horizontal=True)

                # PENYEMPURNAAN: Ambil daftar rekening dan tambahkan pilihan tujuan dana
                accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
                account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
                
                selected_account_name = None
                if payment_type == 'cash':
                    selected_account_name = st.selectbox("Terima pembayaran ke", options=account_map.keys())

                description = st.text_area("Deskripsi (opsional)")

                submitted = st.form_submit_button("Simpan Penjualan")

                if submitted:
                    if quantity > available_qty:
                        st.error(f"Aksi dibatalkan. Jumlah penjualan ({quantity}) melebihi stok ({available_qty}).")
                    else:
                        transaction_datetime = datetime.datetime.combine(transaction_date, transaction_time)
                        warehouse_id = warehouse_stock_map[selected_warehouse_label]['warehouseid']
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
                            # PENYEMPURNAAN: Kirim ID rekening yang dipilih
                            "p_account_id": account_map.get(selected_account_name) if selected_account_name else None
                        }
                        supabase.rpc("record_sale_transaction", params).execute()
                        st.success("Transaksi penjualan berhasil disimpan!")
                        st.rerun()
    
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
