import streamlit as st
import pandas as pd
from app.db import get_client

def show():
    st.markdown("<h1 style='color: #1f77b4;'>Daftar Stok Produk</h1>", unsafe_allow_html=True)

    supabase = get_client()
    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        # Filter & Search Section
        st.markdown("<h3>🔍 Filter & Pencarian</h3>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            search_text = st.text_input("Cari nama produk", placeholder="Contoh: Mie Goreng")
        with col2:
            min_stock = st.number_input("Min. Stok", min_value=0, value=0)
        with col3:
            sort_by = st.selectbox("Urutkan berdasarkan", 
                                  ["Nama Produk", "Stok (Tertinggi)", "Stok (Terendah)", "Harga"])
        
        st.divider()
        
        # Data Fetching
        response = supabase.table("product").select(
            "productid, productname, type, size, color, brand, description, updateat, "
            "productsupply(price, supplier(suppliername)), "
            "product_warehouse(quantity, warehouse_list(name))"
        ).eq("store", store).execute()

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
            
            # Apply search filter
            if search_text:
                term = search_text.lower()
                df = df[
                    df['Nama Produk'].str.lower().str.contains(term) |
                    df['Jenis'].str.lower().str.contains(term, na=False) |
                    df['Merek'].str.lower().str.contains(term, na=False)
                ]
            
            # Apply stock filter
            df = df[df['Total Kuantitas'] >= min_stock]
            
            # Apply sorting
            if sort_by == "Stok (Tertinggi)":
                df = df.sort_values("Total Kuantitas", ascending=False)
            elif sort_by == "Stok (Terendah)":
                df = df.sort_values("Total Kuantitas", ascending=True)
            elif sort_by == "Harga":
                df = df.sort_values("Harga Rata-rata", ascending=False)
            else:  # Nama Produk
                df = df.sort_values("Nama Produk")
            
            # Display stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Produk", len(df))
            with col2:
                total_stock = df['Total Kuantitas'].sum()
                st.metric("Total Stok", f"{total_stock} unit")
            with col3:
                avg_price = df['Harga Rata-rata'].mean()
                st.metric("Harga Rata-rata", f"Rp {avg_price:,.0f}")
            
            st.divider()
            
            st.markdown("<h3>Daftar Produk</h3>", unsafe_allow_html=True)
            
            display_df = df[['ID', 'Nama Produk', 'Jenis', 'Total Kuantitas', 'Harga Rata-rata', 'Supplier', 'Gudang']].copy()
            display_df['Harga Rata-rata'] = display_df['Harga Rata-rata'].apply(lambda x: f"Rp {x:,.0f}")
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Nama Produk": st.column_config.TextColumn("Nama Produk", width="medium"),
                    "Jenis": st.column_config.TextColumn("Jenis", width="small"),
                    "Total Kuantitas": st.column_config.NumberColumn("Stok", width="small"),
                    "Harga Rata-rata": st.column_config.TextColumn("Harga", width="medium"),
                    "Supplier": st.column_config.TextColumn("Supplier", width="medium"),
                    "Gudang": st.column_config.TextColumn("Gudang", width="medium"),
                }
            )
            
            # Optional: Show detailed view
            if st.checkbox("Tampilkan Detail Lengkap"):
                for _, row in df.iterrows():
                    with st.expander(f"{row['Nama Produk']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Jenis**: {row['Jenis']}")
                            st.write(f"**Ukuran**: {row['Ukuran']}")
                            st.write(f"**Warna**: {row['Warna']}")
                            st.write(f"**Merek**: {row['Merek']}")
                        with col2:
                            st.write(f"**Harga Rata-rata**: Rp {row['Harga Rata-rata']:,.0f}")
                            st.write(f"**Total Stok**: {row['Total Kuantitas']} unit")
                            st.write(f"**Supplier**: {row['Supplier']}")
                            st.write(f"**Gudang**: {row['Gudang']}")
                        st.write(f"**Deskripsi**: {row['Deskripsi']}")
                        st.write(f"**Update Terakhir**: {row['Update Terakhir']}")
        else:
            st.info("Tidak ada produk yang terdaftar untuk toko ini.")
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")