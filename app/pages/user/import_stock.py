import streamlit as st
from app.db import get_client
import pandas as pd
import io
import datetime

def show():
    st.title("Impor Produk dari Excel")

    store = st.session_state.get("store")
    username = st.session_state.get("username", "system")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    supabase = get_client()

    # Fetch existing warehouses, suppliers, and accounts
    warehouses = supabase.table("warehouse_list").select("warehouseid, name").execute()
    suppliers = supabase.table("supplier").select("supplierid, suppliername").execute()
    accounts = supabase.table("accounts").select("account_id, account_name, balance").eq("store", store).execute()
    
    warehouse_list = warehouses.data if warehouses.data else []
    supplier_list = suppliers.data if suppliers.data else []
    account_list = accounts.data if accounts.data else []
    
    warehouse_names = [w['name'] for w in warehouse_list]
    supplier_names = [s['suppliername'] for s in supplier_list]

    # Check if warehouses exist
    if not warehouse_list:
        st.error("⚠️ Belum ada gudang yang terdaftar. Silakan daftarkan gudang terlebih dahulu.")
        return

    # Import Settings
    st.markdown("---")
    st.subheader("Pengaturan Import")
    
    col_set1, col_set2 = st.columns(2)
    
    with col_set1:
        # Default Warehouse
        warehouse_options = {w['name']: w['warehouseid'] for w in warehouse_list}
        default_warehouse = st.selectbox(
            "Gudang Default",
            options=list(warehouse_options.keys()),
            help="Digunakan jika kolom Gudang di Excel kosong"
        )
        default_warehouse_id = warehouse_options[default_warehouse]
        
        # Default Supplier
        if supplier_list:
            supplier_options = {s['suppliername']: s['supplierid'] for s in supplier_list}
            supplier_options["-- Tidak ada default (wajib isi di Excel) --"] = None
            default_supplier = st.selectbox(
                "Supplier Default",
                options=list(supplier_options.keys()),
                help="Digunakan jika kolom Supplier di Excel kosong. Supplier baru akan dibuat otomatis."
            )
            default_supplier_id = supplier_options[default_supplier]
        else:
            st.info("Belum ada supplier. Supplier baru akan dibuat otomatis dari Excel.")
            default_supplier_id = None
    
    with col_set2:
        # Payment Type
        payment_type = st.selectbox(
            "Jenis Pembayaran",
            options=["cash", "credit"],
            format_func=lambda x: "Tunai" if x == "cash" else "Kredit/Tempo",
            help="Untuk produk yang diimpor dengan jumlah > 0"
        )
        
        # Account (for cash payment)
        selected_account_id = None
        due_date = None
        
        if payment_type == "cash":
            if account_list:
                account_options = {f"{a['account_name']} (Rp {a['balance']:,.0f})": a['account_id'] for a in account_list}
                account_options["-- Tidak potong saldo --"] = None
                selected_account = st.selectbox("Akun Pembayaran", options=list(account_options.keys()))
                selected_account_id = account_options[selected_account]
            else:
                st.warning("Tidak ada akun kas. Pembayaran tidak akan mengurangi saldo.")
        else:
            # Due date for credit
            due_date = st.date_input(
                "Jatuh Tempo (TOP)",
                value=datetime.date.today() + datetime.timedelta(days=30),
                min_value=datetime.date.today()
            )

    # Info Section
    st.markdown("---")
    st.subheader("Informasi Referensi")
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("**Gudang yang Tersedia:**")
        for w in warehouse_names:
            st.markdown(f"- `{w}`")
    
    with col_info2:
        st.markdown("**Supplier yang Tersedia:**")
        if supplier_names:
            for s in supplier_names:
                st.markdown(f"- `{s}`")
        else:
            st.markdown("_Belum ada supplier(Otomatis)")

    # Download Template
    st.markdown("---")
    st.subheader("1. Unduh Template Excel")

    example_warehouse = warehouse_names[0] if warehouse_names else "Nama Gudang"
    example_supplier = supplier_names[0] if supplier_names else "Nama Supplier"
    
    template_df = pd.DataFrame({
        "Nama Produk": ["Granit Murano 60x60", "Keramik Putih 30x30", "Semen Tiga Roda 50kg"],
        "Jumlah": [100, 0, 50],
        "Gudang": [example_warehouse, "", example_warehouse],
        "Harga Beli": [75000, 0, 55000],
        "Supplier": [example_supplier, "", example_supplier],
        "Jenis": ["Granit", "Keramik", "Semen"],
        "Ukuran": ["60x60", "30x30", "50kg"],
        "Warna": ["Abu-abu", "Putih", ""],
        "Merek": ["Murano", "Roman", "Tiga Roda"],
        "Deskripsi": ["Contoh: dengan stok", "Contoh: hanya daftar produk", "Contoh: dengan stok"]
    })
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name='Data Produk')
    
    st.download_button(
        label="Unduh Template (.xlsx)",
        data=output.getvalue(),
        file_name="template_import_produk.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.caption("""
    **Keterangan kolom:**
    - **Nama Produk** (wajib)
    - **Jumlah** (wajib, isi 0 jika hanya ingin mendaftarkan produk tanpa stok)
    - **Gudang** (opsional, gunakan default jika kosong)
    - **Harga Beli** (wajib jika jumlah > 0)
    - **Supplier** (wajib jika jumlah > 0, otomatis dibuat jika belum ada)
    - **Jenis, Ukuran, Warna, Merek, Deskripsi**: Opsional
    """)

    # Upload File
    st.markdown("---")
    st.subheader("2. Unggah File Excel yang Sudah Diisi")
    
    uploaded_file = st.file_uploader("Pilih file .xlsx", type=["xlsx"])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            required_columns = ["Nama Produk"]
            optional_purchase_cols = ["Jumlah", "Harga Beli"]
            missing_cols = [col for col in required_columns if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ File Excel tidak valid. Kolom berikut tidak ditemukan: **{', '.join(missing_cols)}**")
            else:
                # Fill missing optional columns with defaults
                if "Jumlah" not in df.columns:
                    df["Jumlah"] = 0
                if "Harga Beli" not in df.columns:
                    df["Harga Beli"] = 0
                if "Gudang" not in df.columns:
                    df["Gudang"] = ""
                if "Supplier" not in df.columns:
                    df["Supplier"] = ""
                
                df = df.dropna(subset=["Nama Produk"])
                df = df[df["Nama Produk"].astype(str).str.strip() != ""]
                
                if len(df) == 0:
                    st.warning("File tidak berisi data produk yang valid.")
                    return
                
                st.success(f"✅ File valid! Ditemukan **{len(df)} produk** untuk diimpor.")
                
                # Validate warehouses in uploaded file (only if provided)
                df_warehouses = df["Gudang"].dropna().unique().tolist()
                df_warehouses = [w for w in df_warehouses if str(w).strip() != ""]
                invalid_warehouses = [w for w in df_warehouses if str(w).strip().lower() not in [wh.lower() for wh in warehouse_names]]
                
                if invalid_warehouses:
                    st.error(f"❌ Gudang tidak valid ditemukan di file: **{', '.join(invalid_warehouses)}**")
                    return
                
                # Analyze data
                df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0).astype(int)
                df["Harga Beli"] = pd.to_numeric(df["Harga Beli"], errors="coerce").fillna(0)
                
                register_only = df[df["Jumlah"] == 0]
                with_purchase = df[df["Jumlah"] > 0]
                
                # Show preview
                st.markdown("**Preview Data:**")
                st.dataframe(df, use_container_width=True)
                
                # Summary
                st.markdown("**Ringkasan Import:**")
                col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
                with col_sum1:
                    st.metric("Total Baris", len(df))
                with col_sum2:
                    st.metric("Daftar Saja (qty=0)", len(register_only))
                with col_sum3:
                    st.metric("Dengan Pembelian (qty>0)", len(with_purchase))
                with col_sum4:
                    total_value = (with_purchase["Jumlah"] * with_purchase["Harga Beli"]).sum()
                    st.metric("Total Nilai Beli", f"Rp {total_value:,.0f}")

                # Import Process
                st.markdown("---")
                st.subheader("3. Mulai Proses Impor")
                
                if len(register_only) > 0:
                    st.caption(f"{len(register_only)} produk akan didaftarkan tanpa stok")
                if len(with_purchase) > 0:
                    st.caption(f"{len(with_purchase)} produk akan diimpor sebagai pembelian")
                
                confirm = st.checkbox("✅ Data sudah benar dan siap diimpor")
                
                if st.button(f"Impor {len(df)} Produk", use_container_width=True, type="primary"):
                    if not confirm:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                    else:
                        df_clean = df.fillna("")
                        df_json = df_clean.astype(str).to_json(orient='records')
                        
                        with st.spinner("Sedang mengimpor data ke database..."):
                            try:
                                # Use smart import function
                                params = {
                                    "products_json": df_json,
                                    "p_store": store,
                                    "p_default_warehouse_id": default_warehouse_id,
                                    "p_default_supplier_id": default_supplier_id,
                                    "p_payment_type": payment_type,
                                    "p_account_id": selected_account_id,
                                    "p_due_date": due_date.isoformat() if due_date else None,
                                    "p_created_by": username
                                }
                                result = supabase.rpc("bulk_import_smart", params).execute()
                                
                                if result.data and "Berhasil" in str(result.data):
                                    st.success(f"✅ {result.data}")
                                    st.balloons()
                                    st.info("Cek **Riwayat Pembelian** untuk transaksi dan **Lihat Stok** untuk stok produk.")
                                else:
                                    st.error(f"Terjadi kesalahan saat impor: {result.data}")
                            except Exception as e:
                                st.error(f"Gagal menjalankan impor: {str(e)}")

        except Exception as e:
            st.error(f"Gagal membaca file Excel. Detail error: {e}")
