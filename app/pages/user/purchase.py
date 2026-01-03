import streamlit as st
from app.db import get_client
import datetime

def show():
    st.title("Purchase (Pembelian)")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()

        products_resp = supabase.table("product").select("productid, productname").eq("store", store).order("productname").execute()
        products = products_resp.data or []
        
        if not products:
            st.info("Pastikan data produk sudah terdaftar.")
            return
            
        product_map = {p['productname']: p['productid'] for p in products}
        selected_product_name = st.selectbox("Pilih Produk", options=product_map.keys(), index=None, placeholder="Pilih produk yang akan dibeli...")

        if selected_product_name:
            product_id = product_map[selected_product_name]
            
            info_resp = supabase.rpc("get_product_purchase_info", {"p_product_id": product_id}).execute()
            product_info = info_resp.data
            
            avg_price = product_info.get('average_price', 0)
            warehouse_stock_list = product_info.get('warehouse_stock', [])

            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                quantity = st.number_input("Jumlah", min_value=1, step=1)
            with col2:
                price = st.number_input("Harga Satuan", min_value=0.0, format="%.2f")

            col3, col4 = st.columns(2)
            with col3:
                st.metric("Harga Beli Rata-rata Sebelumnya", f"Rp {avg_price:,.2f}")
            with col4:
                total_price = quantity * price
                st.metric("Total Pembelian Saat Ini", f"Rp {total_price:,.2f}")

            st.write("**Stok Produk Saat Ini di Gudang:**")
            if warehouse_stock_list:
                stock_info = " | ".join([f"{item['warehouse_name']}: **{item['quantity']}**" for item in warehouse_stock_list])
                st.info(stock_info)
            else:
                st.info("Produk ini belum memiliki stok di gudang manapun.")
            
            st.markdown("---")

            with st.form("purchase_form"):
                st.subheader("Detail Transaksi")
                
                col_tgl, col_jam = st.columns(2)
                with col_tgl:
                    transaction_date = st.date_input("Tanggal Transaksi", value=datetime.date.today())
                with col_jam:
                    transaction_time = st.time_input("Waktu Transaksi", value=datetime.datetime.now().time())
                
                supplier_resp = supabase.table("supplier").select("supplierid, suppliername").order("suppliername").execute()
                warehouse_resp = supabase.table("warehouse_list").select("warehouseid, name").order("name").execute()
                
                supplier_map = {s['suppliername']: s['supplierid'] for s in supplier_resp.data or []}
                warehouse_map = {w['name']: w['warehouseid'] for w in warehouse_resp.data or []}

                selected_supplier_name = st.selectbox("Supplier", options=supplier_map.keys())
                selected_warehouse_name = st.selectbox("Simpan ke Gudang", options=warehouse_map.keys())
                
                # PENYEMPURNAAN: Ambil daftar rekening dan tambahkan pilihan sumber dana
                accounts_resp = supabase.table("accounts").select("account_id, account_name").eq("store", store).execute()
                account_map = {acc['account_name']: acc['account_id'] for acc in accounts_resp.data or []}
                
                payment_type = st.radio("Metode Pembayaran", ["cash", "credit"], horizontal=True)
                
                # Hanya tampilkan pilihan rekening jika pembayaran 'cash'
                selected_account_name = None
                if payment_type == 'cash':
                    selected_account_name = st.selectbox("Bayar dari", options=account_map.keys())

                description = st.text_area("Deskripsi (opsional)")
                
                submitted = st.form_submit_button("Simpan Transaksi")

                if submitted:
                    transaction_datetime = datetime.datetime.combine(transaction_date, transaction_time)
                    
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
                        # PENYEMPURNAAN: Kirim ID rekening yang dipilih
                        "p_account_id": account_map.get(selected_account_name) if selected_account_name else None
                    }
                    supabase.rpc("record_purchase_transaction", params).execute()
                    st.success("Transaksi pembelian berhasil dicatat!")
                    st.rerun()

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses halaman: {e}")
