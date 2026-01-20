import streamlit as st
from app.db import get_client
from app.auth import change_password, reset_password_admin
import pandas as pd
import datetime
import json
import re

def parse_rpc_result(result):
    """Parse RPC result yang mungkin berupa dict, bytes, atau string JSON."""
    if result.data is None:
        return {'success': False, 'message': 'No data returned'}
    
    data = result.data
    
    if isinstance(data, dict):
        return data
    
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {'success': False, 'message': f'Invalid JSON: {data}'}
    
    return {'success': False, 'message': f'Unknown data type: {type(data)}'}

def parse_rpc_exception(e):
    """Parse exception dari Supabase RPC yang mungkin berisi JSON valid di details."""
    error_str = str(e)

    match = re.search(r"b'(\{.*\})'", error_str)
    if match:
        try:
            json_str = match.group(1)
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    if hasattr(e, 'details') and e.details:
        details = e.details
        if isinstance(details, bytes):
            try:
                return json.loads(details.decode('utf-8'))
            except:
                pass
        elif isinstance(details, str):
            # Cek format b'...'
            if details.startswith("b'") and details.endswith("'"):
                try:
                    inner = details[2:-1]
                    return json.loads(inner)
                except:
                    pass
    
    return None

def show():
    st.title("Manajemen Toko")
    
    supabase = get_client()
    admin_user = st.session_state.get("username")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Manajemen Toko", "Kelola Supplier", "Kelola Gudang", "Keamanan"])
    
    # Manajemen Toko
    with tab1:
        st.header("Kelola Data Toko")
        
        # Sub-tabs untuk toko
        toko_tab1, toko_tab2, toko_tab3, toko_tab4 = st.tabs(["Lihat Toko", "Tambah Toko", "Edit Toko", "Hapus Toko"])
        
        # View Toko
        with toko_tab1:
            st.subheader("Daftar Toko")
            try:
                users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
                stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
                
                if stores:
                    store_data = []
                    for store in stores:
                        count_resp = supabase.table("users").select("*", count='exact').eq("store", store).eq("role", "pegawai").execute()
                        staff_count = count_resp.count if count_resp.count else 0
                        store_data.append({
                            "Nama Toko": store,
                            "Jumlah Staff": staff_count,
                            "Status": "Aktif"
                        })
                    
                    df = pd.DataFrame(store_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Belum ada toko yang terdaftar.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Add Toko
        with toko_tab2:
            st.subheader("Daftarkan Toko Baru")
            with st.form("add_store_form"):
                store_name = st.text_input("Nama Toko (Username)*", placeholder="Contoh: SuryaJaya")
                store_display_name = st.text_input("Nama Tampilan Toko*", placeholder="Contoh: TokoKeramik_SuryaJaya")
                password = st.text_input("Password (min 6 karakter)*", type="password")
                confirm_password = st.text_input("Konfirmasi Password*", type="password")
                
                st.divider()
                confirm_add = st.checkbox("Data toko sudah benar")
                submitted = st.form_submit_button("➕ Daftarkan Toko", use_container_width=True, type="primary")
                
                if submitted:
                    if not confirm_add:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                        st.stop()
                    if not store_name.strip() or not store_display_name.strip():
                        st.error("Nama toko dan nama tampilan harus diisi!")
                        st.stop()
                    
                    if len(password) < 6:
                        st.error("Password minimal 6 karakter!")
                        st.stop()
                    
                    if password != confirm_password:
                        st.error("Password tidak cocok!")
                        st.stop()
                    
                    try:
                        from werkzeug.security import generate_password_hash
                        
                        check_user = supabase.table("users").select("*").eq("username", store_name).execute()
                        if check_user.data:
                            st.error(f"Username '{store_name}' sudah ada!")
                            st.stop()
                        
                        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                        
                        new_user = {
                            "username": store_name,
                            "password": hashed_password,
                            "role": "pegawai",
                            "store": store_display_name
                        }
                        
                        response = supabase.table("users").insert(new_user).execute()
                        if response.data:
                            st.success(f"✅ Toko '{store_display_name}' berhasil dibuat dengan username '{store_name}'!")
                            st.rerun()
                        else:
                            st.error("Gagal membuat toko. Silakan coba lagi.")
                    
                    except Exception as e:
                        error_str = str(e)
                        if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                            st.error(f"Username '{store_name}' sudah terdaftar di sistem. Gunakan username lain.")
                        elif "user_id" in error_str:
                            st.error("Error: Gagal generate ID pengguna.")
                        else:
                            st.error(f"Gagal membuat toko: {error_str}")
        
        # Edit Toko
        with toko_tab3:
            st.subheader("Edit Data Toko")
            try:
                users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
                stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
                
                if stores:
                    selected_store = st.selectbox("Pilih Toko yang Akan Diedit", options=stores)
                    
                    with st.form("edit_store_form"):
                        new_store_name = st.text_input("Nama Toko Baru", value=selected_store)
                        
                        st.divider()
                        confirm_edit = st.checkbox("Ubah nama toko")
                        submitted = st.form_submit_button("💾 Update Nama Toko", use_container_width=True)
                        
                        if submitted:
                            if not confirm_edit:
                                st.error("Harap centang konfirmasi terlebih dahulu!")
                                st.stop()
                            if new_store_name != selected_store:
                                try:
                                    response = supabase.table("users").update({"store": new_store_name}).eq("store", selected_store).execute()
                                    if response.data:
                                        st.success(f"✅ Nama toko berhasil diubah dari '{selected_store}' ke '{new_store_name}'!")
                                        st.rerun()
                                    else:
                                        st.error("Gagal mengupdate nama toko. Silakan coba lagi.")
                                except Exception as e:
                                    error_str = str(e)
                                    if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                                        st.error(f"Nama toko '{new_store_name}' sudah ada. Gunakan nama lain.")
                                    else:
                                        st.error(f"Error: {error_str}")
                            else:
                                st.info("Tidak ada perubahan data.")
                else:
                    st.info("Belum ada toko untuk diedit.")
            except Exception as e:
                st.error(f"Error: {e}")

        with toko_tab4:
            st.subheader("Hapus Toko")
            st.error("⚠️ **PERINGATAN:** Menghapus toko akan menghapus SEMUA data terkait secara permanen!")
            st.warning("""
            Data yang akan dihapus:
            - Semua user/pegawai toko
            - Semua produk dan stok
            - Semua supplier dan hutang
            - Semua gudang
            - Semua transaksi (penjualan, pembelian, retur)
            - Semua riwayat keuangan (arus kas, biaya operasional)
            - Semua data pegawai dan gaji
            """)
            
            try:
                users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
                stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
                
                if stores:
                    selected_store_delete = st.selectbox("Pilih Toko yang Akan Dihapus", options=stores, key="delete_store_select")
                    
                    st.markdown("---")
                    st.markdown("### Konfirmasi Penghapusan")
                    st.write(f"Untuk menghapus toko **{selected_store_delete}**, ketik nama toko tersebut di bawah:")
                    
                    confirm_name = st.text_input("Ketik nama toko untuk konfirmasi", key="confirm_store_name")
                    confirm_check = st.checkbox(f"Saya memahami bahwa tindakan ini TIDAK DAPAT DIBATALKAN", key="confirm_delete_check")
                    
                    col_del1, col_del2 = st.columns(2)
                    with col_del1:
                        if st.button("Hapus Toko Permanen", type="primary", use_container_width=True, disabled=not confirm_check):
                            if confirm_name != selected_store_delete:
                                st.error(f"Nama toko tidak cocok! Ketik '{selected_store_delete}' untuk konfirmasi.")
                            else:
                                try:
                                    result = supabase.rpc("delete_store_cascade", {"p_store_name": selected_store_delete}).execute()
                                    data = parse_rpc_result(result)
                                    if data.get('success'):
                                        deleted = data.get('deleted_counts', {})
                                        st.success(f"✅ Toko '{selected_store_delete}' berhasil dihapus!")
                                        st.info(f"""
                                        Data yang dihapus:
                                        - {deleted.get('users', 0)} user
                                        - {deleted.get('products', 0)} produk
                                        - {deleted.get('suppliers', 0)} supplier
                                        - {deleted.get('warehouses', 0)} gudang
                                        - {deleted.get('sales', 0)} transaksi penjualan
                                        - {deleted.get('purchases', 0)} transaksi pembelian
                                        """)
                                        st.rerun()
                                    else:
                                        st.error(f"Gagal menghapus toko: {data.get('message', 'Unknown error')}")
                                except Exception as e:
                                    parsed = parse_rpc_exception(e)
                                    if parsed and parsed.get('success'):
                                        deleted = parsed.get('deleted_counts', {})
                                        st.success(f"✅ Toko '{selected_store_delete}' berhasil dihapus!")
                                        st.rerun()
                                    else:
                                        st.error(f"Error: {e}")
                else:
                    st.info("Tidak ada toko untuk dihapus.")
            except Exception as e:
                st.error(f"Error: {e}")
    
    with tab2:
        st.header("Kelola Supplier")
        
        try:
            users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
            stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
            
            if not stores:
                st.info("Belum ada toko yang terdaftar.")
            else:
                selected_store_supplier = st.selectbox("Pilih Toko", options=stores, key="supplier_store_select")
                
                sup_tab1, sup_tab2 = st.tabs(["Daftar Supplier", "Edit / Hapus Supplier"])
                
                # Daftar Supplier
                with sup_tab1:
                    st.subheader("Daftar Supplier")
                    try:
                        suppliers_resp = supabase.table("supplier").select("supplierid, suppliername, supplierno, address, description").eq("store", selected_store_supplier).order("suppliername").execute()
                        
                        if suppliers_resp.data:
                            sup_data = []
                            for sup in suppliers_resp.data:
                                debt_resp = supabase.rpc("get_supplier_debt_total", {
                                    "p_store": selected_store_supplier,
                                    "p_supplier_id": sup['supplierid']
                                }).execute()
                                total_debt = debt_resp.data if debt_resp.data else 0
                                
                                sup_data.append({
                                    'supplierid': sup['supplierid'],
                                    'suppliername': sup['suppliername'],
                                    'supplierno': sup['supplierno'] or '-',
                                    'address': sup['address'] or '-',
                                    'total_debt': total_debt
                                })
                            
                            df_sup = pd.DataFrame(sup_data)
                            df_sup['total_debt'] = df_sup['total_debt'].apply(lambda x: f"Rp {x:,.0f}" if x else "Rp 0")
                            
                            st.dataframe(
                                df_sup.rename(columns={
                                    'supplierid': 'ID',
                                    'suppliername': 'Nama Supplier',
                                    'supplierno': 'No. Telp',
                                    'address': 'Alamat',
                                    'total_debt': 'Total Hutang'
                                }),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("Tidak ada supplier untuk toko ini.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                with sup_tab2:
                    st.subheader("Edit atau Hapus Supplier")
                    try:
                        suppliers_resp = supabase.table("supplier").select("*").eq("store", selected_store_supplier).order("suppliername").execute()
                        
                        if suppliers_resp.data:
                            supplier_options = {s['suppliername']: s for s in suppliers_resp.data}
                            selected_supplier = st.selectbox("Pilih Supplier", options=list(supplier_options.keys()), key="edit_del_supplier")
                            
                            sup_data = supplier_options[selected_supplier]
                            
                            st.markdown("#### Edit Supplier")
                            with st.form("edit_supplier_form"):
                                new_name = st.text_input("Nama Supplier", value=sup_data['suppliername'])
                                new_phone = st.text_input("No. Telepon", value=sup_data['supplierno'] or "")
                                new_address = st.text_area("Alamat", value=sup_data['address'] or "")
                                new_desc = st.text_area("Deskripsi", value=sup_data['description'] or "")
                                
                                if st.form_submit_button("Simpan Perubahan", use_container_width=True):
                                    try:
                                        result = supabase.rpc("update_supplier", {
                                            "p_supplier_id": sup_data['supplierid'],
                                            "p_supplier_name": new_name,
                                            "p_supplier_no": new_phone if new_phone else None,
                                            "p_address": new_address if new_address else None,
                                            "p_description": new_desc if new_desc else None
                                        }).execute()
                                        data = parse_rpc_result(result)
                                        if data.get('success'):
                                            st.success("✅ Supplier berhasil diupdate!")
                                            st.rerun()
                                        else:
                                            st.error(data.get('message', 'Gagal update supplier'))
                                    except Exception as e:
                                        parsed = parse_rpc_exception(e)
                                        if parsed and parsed.get('success'):
                                            st.success("✅ Supplier berhasil diupdate!")
                                            st.rerun()
                                        else:
                                            st.error(f"Error: {e}")
                            
                            # Delete Section
                            st.markdown("---")
                            st.markdown("#### Hapus Supplier Permanen")
                            st.error("⚠️ **PERINGATAN:** Menghapus supplier akan menghapus hutang terkait. Riwayat transaksi tetap ada tapi nama supplier akan hilang.")
                            
                            confirm_delete_sup = st.checkbox(f"Saya yakin ingin menghapus supplier '{selected_supplier}' secara permanen", key="confirm_delete_sup")
                            
                            if st.button("Hapus Supplier Permanen", disabled=not confirm_delete_sup, type="primary", key="btn_delete_sup"):
                                try:
                                    result = supabase.rpc("delete_supplier_permanent", {
                                        "p_supplier_id": sup_data['supplierid']
                                    }).execute()
                                    data = parse_rpc_result(result)
                                    if data.get('success'):
                                        st.success(data.get('message'))
                                        st.rerun()
                                    else:
                                        st.error(data.get('message', 'Gagal menghapus supplier'))
                                except Exception as e:
                                    parsed = parse_rpc_exception(e)
                                    if parsed and parsed.get('success'):
                                        st.success(parsed.get('message', 'Supplier berhasil dihapus!'))
                                        st.rerun()
                                    else:
                                        st.error(f"Error: {e}")
                        else:
                            st.info("Tidak ada supplier untuk diedit/dihapus.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with tab3:
        st.header("Kelola Gudang")
        
        try:
            users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
            stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
            
            if not stores:
                st.info("Belum ada toko yang terdaftar.")
            else:
                selected_store_warehouse = st.selectbox("Pilih Toko", options=stores, key="warehouse_store_select")
                
                wh_tab1, wh_tab2, wh_tab3 = st.tabs(["Daftar Gudang", "Migrasi Stok", "Edit / Hapus Gudang"])
                
                # Daftar Gudang
                with wh_tab1:
                    st.subheader("Daftar Gudang")
                    try:
                        warehouses_resp = supabase.table("warehouse_list").select("warehouseid, name").eq("store", selected_store_warehouse).order("name").execute()
                        
                        if warehouses_resp.data:
                            wh_data = []
                            for wh in warehouses_resp.data:
                                stock_resp = supabase.table("product_warehouse").select("quantity").eq("warehouseid", wh['warehouseid']).execute()
                                total_stock = sum([s['quantity'] for s in (stock_resp.data or [])])
                                product_count = len([s for s in (stock_resp.data or []) if s['quantity'] > 0])
                                wh_data.append({
                                    'warehouseid': wh['warehouseid'],
                                    'name': wh['name'],
                                    'product_count': product_count,
                                    'total_stock': total_stock
                                })
                            
                            df_wh = pd.DataFrame(wh_data)
                            st.dataframe(
                                df_wh.rename(columns={
                                    'warehouseid': 'ID',
                                    'name': 'Nama Gudang',
                                    'product_count': 'Jenis Produk',
                                    'total_stock': 'Total Stok'
                                }),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("Tidak ada gudang untuk toko ini.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                # Migrasi Stok
                with wh_tab2:
                    st.subheader("Migrasi Stok Antar Gudang")
                    st.info("Pindahkan stok dari satu gudang ke gudang lain sebelum menghapus gudang.")
                    
                    try:
                        warehouses_resp = supabase.table("warehouse_list").select("warehouseid, name").eq("store", selected_store_warehouse).order("name").execute()
                        
                        if warehouses_resp.data and len(warehouses_resp.data) >= 2:
                            warehouse_options = {wh['name']: wh['warehouseid'] for wh in warehouses_resp.data}
                            
                            col_src, col_tgt = st.columns(2)
                            with col_src:
                                source_wh_name = st.selectbox("Gudang Asal", options=list(warehouse_options.keys()), key="migrate_source")
                            with col_tgt:
                                target_options = [n for n in warehouse_options.keys() if n != source_wh_name]
                                target_wh_name = st.selectbox("Gudang Tujuan", options=target_options, key="migrate_target")
                            
                            source_wh_id = warehouse_options[source_wh_name]
                            target_wh_id = warehouse_options[target_wh_name]
                        
                            st.markdown("---")
                            st.markdown(f"#### Stok di Gudang **{source_wh_name}**")
                            
                            stock_resp = supabase.rpc("get_warehouse_stock_summary", {"p_warehouse_id": source_wh_id}).execute()
                            
                            if stock_resp.data:
                                df_stock = pd.DataFrame(stock_resp.data)
                                df_stock['harga'] = df_stock['harga'].apply(lambda x: f"Rp {x:,.0f}" if x else "-")
                                
                                st.dataframe(
                                    df_stock.rename(columns={
                                        'productid': 'ID Produk',
                                        'productname': 'Nama Produk',
                                        'quantity': 'Stok',
                                        'harga': 'Harga Beli'
                                    }),
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                                total_stock = df_stock['quantity'].sum() if 'quantity' in df_stock.columns else 0
                                st.write(f"**Total: {len(df_stock)} produk, {total_stock} unit**")
                                
                                # Migration options
                                st.markdown("---")
                                migrate_mode = st.radio(
                                    "Pilih Mode Migrasi",
                                    ["Migrasi Semua Stok", "Migrasi Per Produk"],
                                    key="migrate_mode"
                                )
                                
                                if migrate_mode == "Migrasi Semua Stok":
                                    st.warning(f"Semua stok ({total_stock} unit dari {len(df_stock)} produk) akan dipindahkan ke gudang **{target_wh_name}**")
                                    
                                    confirm_migrate_all = st.checkbox("Konfirmasi migrasi semua stok", key="confirm_migrate_all")
                                    
                                    if st.button("Migrasi Semua Stok", disabled=not confirm_migrate_all, type="primary", key="btn_migrate_all"):
                                        try:
                                            result = supabase.rpc("migrate_all_warehouse_stock", {
                                                "p_source_warehouse_id": source_wh_id,
                                                "p_target_warehouse_id": target_wh_id
                                            }).execute()
                                            data = parse_rpc_result(result)
                                            if data.get('success'):
                                                st.success(data.get('message'))
                                                st.balloons()
                                                st.rerun()
                                            else:
                                                st.error(data.get('message', 'Gagal migrasi stok'))
                                        except Exception as e:
                                            parsed = parse_rpc_exception(e)
                                            if parsed and parsed.get('success'):
                                                st.success(parsed.get('message', 'Migrasi stok berhasil!'))
                                                st.balloons()
                                                st.rerun()
                                            else:
                                                st.error(f"Error: {e}")
                                
                                else:
                                    product_options = {f"{p['productname']} (Stok: {p['quantity']})": p for p in stock_resp.data}
                                    selected_product = st.selectbox("Pilih Produk", options=list(product_options.keys()), key="migrate_product")
                                    
                                    prod_data = product_options[selected_product]
                                    max_qty = prod_data['quantity']
                                    
                                    migrate_qty = st.number_input(
                                        "Jumlah yang Dipindahkan",
                                        min_value=1,
                                        max_value=max_qty,
                                        value=max_qty,
                                        key="migrate_qty"
                                    )
                                    
                                    if st.button(f"Pindahkan {migrate_qty} unit", type="primary", key="btn_migrate_one"):
                                        try:
                                            result = supabase.rpc("migrate_product_stock", {
                                                "p_product_id": prod_data['productid'],
                                                "p_source_warehouse_id": source_wh_id,
                                                "p_target_warehouse_id": target_wh_id,
                                                "p_quantity": migrate_qty
                                            }).execute()
                                            data = parse_rpc_result(result)
                                            if data.get('success'):
                                                st.success(data.get('message'))
                                                st.rerun()
                                            else:
                                                st.error(data.get('message', 'Gagal migrasi stok'))
                                        except Exception as e:
                                            parsed = parse_rpc_exception(e)
                                            if parsed and parsed.get('success'):
                                                st.success(parsed.get('message', 'Migrasi stok berhasil!'))
                                                st.rerun()
                                            else:
                                                st.error(f"Error: {e}")
                            else:
                                st.info(f"Tidak ada stok di gudang **{source_wh_name}**")
                        
                        elif warehouses_resp.data and len(warehouses_resp.data) == 1:
                            st.warning("Perlu minimal 2 gudang untuk melakukan migrasi stok.")
                        else:
                            st.info("Tidak ada gudang untuk toko ini.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                # Edit / Hapus Gudang
                with wh_tab3:
                    st.subheader("Edit atau Hapus Gudang")
                    try:
                        warehouses_resp = supabase.table("warehouse_list").select("warehouseid, name").eq("store", selected_store_warehouse).order("name").execute()
                        
                        if warehouses_resp.data:
                            warehouse_options = {wh['name']: wh['warehouseid'] for wh in warehouses_resp.data}
                            selected_warehouse = st.selectbox("Pilih Gudang", options=list(warehouse_options.keys()), key="edit_del_warehouse")
                            
                            wh_id = warehouse_options[selected_warehouse]
                            
                            stock_resp = supabase.table("product_warehouse").select("quantity").eq("warehouseid", wh_id).execute()
                            total_stock = sum([s['quantity'] for s in (stock_resp.data or [])])
                            product_count = len([s for s in (stock_resp.data or []) if s['quantity'] > 0])
                            
                            st.info(f"Gudang ini memiliki **{product_count} jenis produk** dengan total **{total_stock} unit** stok.")
                            
                            st.markdown("#### Edit Nama Gudang")
                            with st.form("edit_warehouse_form"):
                                new_wh_name = st.text_input("Nama Gudang", value=selected_warehouse)
                                
                                if st.form_submit_button("💾 Simpan Perubahan", use_container_width=True):
                                    if new_wh_name.strip() and new_wh_name != selected_warehouse:
                                        try:
                                            result = supabase.rpc("update_warehouse", {
                                                "p_warehouse_id": wh_id,
                                                "p_warehouse_name": new_wh_name.strip()
                                            }).execute()
                                            data = parse_rpc_result(result)
                                            if data.get('success'):
                                                st.success("✅ Gudang berhasil diupdate!")
                                                st.rerun()
                                            else:
                                                st.error(data.get('message', 'Gagal update gudang'))
                                        except Exception as e:
                                            # Coba parse JSON dari exception
                                            parsed = parse_rpc_exception(e)
                                            if parsed and parsed.get('success'):
                                                st.success("✅ Gudang berhasil diupdate!")
                                                st.rerun()
                                            else:
                                                st.error(f"Error: {e}")
                                    else:
                                        st.info("Tidak ada perubahan.")
                            
                            # Delete Section
                            st.markdown("---")
                            st.markdown("#### Hapus Gudang Permanen")
                            
                            if total_stock > 0:
                                st.error(f"⚠️ **PERINGATAN:** Gudang ini masih memiliki {total_stock} unit stok!")
                                st.warning("Anda bisa memilih untuk:")
                                st.write("1. **Pindahkan stok** terlebih dahulu ke gudang lain (gunakan tab Migrasi Stok)")
                                st.write("2. **Hapus paksa** - stok akan dihapus dari sistem")
                                
                                force_delete = st.checkbox("Hapus paksa (stok akan dihapus)", key="force_delete_wh")
                            else:
                                force_delete = False
                                st.success("✅ Gudang kosong, aman untuk dihapus.")
                            
                            confirm_delete_wh = st.checkbox(f"Saya yakin ingin menghapus gudang '{selected_warehouse}' secara permanen", key="confirm_delete_wh")
                            
                            delete_disabled = not confirm_delete_wh or (total_stock > 0 and not force_delete)
                            
                            if st.button("Hapus Gudang Permanen", disabled=delete_disabled, type="primary", key="btn_delete_wh"):
                                try:
                                    result = supabase.rpc("delete_warehouse_permanent", {
                                        "p_warehouse_id": wh_id,
                                        "p_force_delete_stock": force_delete
                                    }).execute()
                                    data = parse_rpc_result(result)
                                    if data.get('success'):
                                        st.success(data.get('message'))
                                        if force_delete:
                                            st.warning(f"Stok yang dihapus: {data.get('stock_deleted', 0)} unit")
                                        st.rerun()
                                    else:
                                        st.error(data.get('message', 'Gagal menghapus gudang'))
                                except Exception as e:
                                    parsed = parse_rpc_exception(e)
                                    if parsed and parsed.get('success'):
                                        st.success(parsed.get('message', 'Gudang berhasil dihapus!'))
                                        if force_delete:
                                            st.warning(f"Stok yang dihapus: {parsed.get('stock_deleted', 0)} unit")
                                        st.rerun()
                                    else:
                                        st.error(f"Error: {e}")
                        else:
                            st.info("Tidak ada gudang untuk diedit/dihapus.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with tab4:
        st.header("Manajemen Keamanan")
        
        sec_tab1, sec_tab2 = st.tabs(["Ubah Password Admin", "Reset Password Toko"])
        
        # Admin Password Change
        with sec_tab1:
            st.subheader("Ubah Password Akun Admin")
            with st.form("change_pass_form"):
                old_password = st.text_input("Password Lama", type="password")
                new_password = st.text_input("Password Baru (min 6 char)", type="password")
                confirm_new = st.text_input("Konfirmasi Password Baru", type="password")
                
                submitted = st.form_submit_button("Ubah Password", use_container_width=True, type="primary")
                
                if submitted:
                    if len(new_password) < 6:
                        st.error("Password minimal 6 karakter!")
                    elif new_password != confirm_new:
                        st.error("Password baru tidak cocok!")
                    else:
                        if change_password(admin_user, old_password, new_password):
                            st.success("Password berhasil diubah!")

        # User Password Reset
        with sec_tab2:
            st.subheader("Reset Password Toko Lain")
            st.warning("⚠️ Tindakan ini akan mengubah password Toko secara permanen.")
            try:
                users = supabase.table("users").select("username, role").execute()
                if users.data:
                    usernames = [u['username'] for u in users.data if u['role'] != 'admin' or u['username'] != admin_user]
                    
                    if usernames:
                        selected_user = st.selectbox("Pilih User", options=usernames)
                        
                        with st.form("reset_pass_form"):
                            new_pass = st.text_input("Password Baru", type="password")
                            confirm = st.text_input("Konfirmasi Password", type="password")
                            
                            st.divider()
                            confirm_reset = st.checkbox(f"Reset password untuk **{selected_user}**")
                            submitted = st.form_submit_button("Reset Password", use_container_width=True, type="primary", disabled=not confirm_reset)
                            
                            if submitted and confirm_reset:
                                if len(new_pass) < 6:
                                    st.error("Password minimal 6 karakter!")
                                elif new_pass != confirm:
                                    st.error("Password tidak cocok!")
                                else:
                                    if reset_password_admin(selected_user, new_pass):
                                        st.success(f"✅ Password '{selected_user}' berhasil direset!")
                                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
