import streamlit as st
from app.db import get_client
import datetime

def show():
    st.title("Stock Adjustment")

    store = st.session_state.get("store")
    if not store:
        st.warning("Data toko tidak ditemukan. Silakan login kembali.")
        return

    # Initialize form key for reset
    if "stock_adj_form_key" not in st.session_state:
        st.session_state.stock_adj_form_key = 0

    try:
        supabase = get_client()

        product_res = supabase.table("product").select("productid, productname, size, type").eq("store", store).order("productname").execute()
        products = product_res.data or []

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
        
        product_map = {product_label(p): p['productid'] for p in products}
        selected_product_name = st.selectbox("Pilih Produk yang Akan Disesuaikan", options=product_map.keys(), key=f"adj_product_{st.session_state.stock_adj_form_key}")

        if selected_product_name:
            product_id = product_map[selected_product_name]
            
            stock_resp = supabase.table("product_warehouse").select(
                "quantity, warehouse_list(warehouseid, name)"
            ).eq("productid", product_id).execute()
            
            stock_data = stock_resp.data or []

            warehouse_options = {
                f"{item['warehouse_list']['name']} (Stok: {item['quantity']})": {
                    "id": item['warehouse_list']['warehouseid'],
                    "qty": item['quantity']
                } for item in stock_data
            }
            all_warehouses_resp = supabase.table("warehouse_list").select("warehouseid, name").eq("store", store).execute()
            for wh in all_warehouses_resp.data:
                label = f"{wh['name']} (Stok: 0)"
                if label not in warehouse_options:
                    warehouse_options[label] = {"id": wh['warehouseid'], "qty": 0}

            if not warehouse_options:
                st.warning("Tidak ada gudang terdaftar. Silakan daftarkan gudang terlebih dahulu.")
                return

            with st.form(f"adjustment_form_{st.session_state.stock_adj_form_key}"):
                st.subheader(f"Menyesuaikan: {selected_product_name}")
                
                selected_warehouse_label = st.selectbox("Pilih Gudang", options=warehouse_options.keys())
                
                adj_type = st.radio("Jenis Penyesuaian", ["add", "reduce"], horizontal=True, format_func=lambda x: "➕ Tambah" if x == "add" else "➖ Kurangi")
                
                max_val = None
                current_stock = warehouse_options[selected_warehouse_label]['qty']

                if adj_type == 'reduce':
                    if current_stock > 0:
                        max_val = current_stock
                        st.info(f"Anda bisa mengurangi {max_val} item dari gudang ini.")
                    else:
                        st.error("Stok di gudang ini sudah 0")
                
                quantity = st.number_input("Jumlah", min_value=1, max_value=max_val, step=1, disabled=(adj_type == 'reduce' and current_stock == 0))

                # Input Tanggal dan Waktu
                st.divider()
                col_tgl, col_jam = st.columns(2)
                with col_tgl:
                    transaction_date = st.date_input("Tanggal Penyesuaian", value=datetime.date.today())
                with col_jam:
                    transaction_time = st.time_input("Waktu Penyesuaian", value=datetime.datetime.now().time())

                description = st.text_area("Keterangan / Alasan")
                
                st.divider()
                st.warning("⚠️ Penyesuaian stok akan mengubah jumlah barang di gudang.")
                
                confirm = st.checkbox("Saya yakin penyesuaian ini benar")
                submitted = st.form_submit_button("Simpan Perubahan", use_container_width=True, type="primary")

                if submitted:
                    if not confirm:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                        st.stop()
                    
                    if adj_type == 'reduce' and current_stock == 0:
                         st.error("Aksi dibatalkan. Stok 0 tidak bisa dikurangi.")
                    else:
                        transaction_datetime = datetime.datetime.combine(transaction_date, transaction_time)
                        params = {
                            "p_product_id": product_id,
                            "p_warehouse_id": warehouse_options[selected_warehouse_label]['id'],
                            "p_adj_type": adj_type,
                            "p_quantity": quantity,
                            "p_description": description if description.strip() else None,
                            "p_transaction_date": transaction_datetime.isoformat()
                        }
                        supabase.rpc("record_stock_adjustment", params).execute()
                        st.success("✅ Penyesuaian stok berhasil disimpan.")
                        # Reset form by incrementing key
                        st.session_state.stock_adj_form_key += 1
                        st.rerun()

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
