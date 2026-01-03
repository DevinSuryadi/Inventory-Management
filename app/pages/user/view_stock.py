import streamlit as st
import pandas as pd
from app.db import get_client

def show():
    st.title("View Stock Produk")

    supabase = get_client()
    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        response = supabase.table("product").select(
            "productid, productname, type, size, color, brand, description, updateat, "
            "productsupply(price, supplier(suppliername)), "
            "product_warehouse(quantity, warehouse_list(name))"
        ).eq("store", store).order("productid", desc=True).execute()

        rows = []
        for p in response.data:
            supplies = p.get("productsupply", [])
            if supplies:
                total_harga = sum(s["price"] for s in supplies)
                avg_price = total_harga / len(supplies) if supplies else 0
                supplier_names = {s["supplier"]["suppliername"] for s in supplies if s.get("supplier")}
            else:
                avg_price = 0
                supplier_names = set()

            warehouses = p.get("product_warehouse", [])
            total_quantity = sum(w["quantity"] for w in warehouses)
            warehouse_names = {w["warehouse_list"]["name"] for w in warehouses if w.get("warehouse_list")}

            rows.append({
                "ID": p["productid"],
                "Nama Produk": p["productname"],
                "Jenis": p["type"],
                "Ukuran": p["size"],
                "Warna": p["color"],
                "Merek": p["brand"],
                "Harga Rata-rata": round(avg_price, 2),
                "Total Kuantitas": total_quantity,
                "Supplier": ", ".join(sorted(supplier_names)),
                "Gudang": ", ".join(sorted(warehouse_names)),
                "Deskripsi": p["description"],
                "Update Terakhir": pd.to_datetime(p["updateat"]).strftime('%Y-%m-%d %H:%M') if p["updateat"] else None
            })

        if rows:
            df = pd.DataFrame(rows)
            
            search = st.text_input("Cari produk berdasarkan nama, jenis, atau merek")
            if search:
                term = search.lower()
                df = df[
                    df['Nama Produk'].str.lower().str.contains(term) |
                    df['Jenis'].str.lower().str.contains(term, na=False) |
                    df['Merek'].str.lower().str.contains(term, na=False)
                ]

            st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                disabled=True # Membuat tabel read-only
            )
        else:
            st.info("Tidak ada produk yang ditemukan untuk toko ini.")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
