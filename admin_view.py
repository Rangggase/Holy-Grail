import streamlit as st
import pandas as pd
import plotly.express as px

def show_admin_dashboard(df_trx, navigate_to, get_logo_svg):
    
    # --- STYLE CSS ---
    st.markdown("""<style>.metric-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }.metric-label { font-size: 14px; color: #666; font-weight: 600; text-transform: uppercase; }.metric-value { font-size: 28px; font-weight: 800; color: #2c3e50; margin: 10px 0; }.metric-delta { font-size: 12px; font-weight: 600; }</style>""", unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"""<div style="display: flex; justify-content: center; margin-bottom: 10px;">{get_logo_svg(width="50", height="50")}</div>""", unsafe_allow_html=True)
        st.markdown("<h2 style='color:white; text-align:center; margin-top:0; font-weight:800; letter-spacing:1px;'>ADMIN PANEL</h2>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🏠 Keluar", type="secondary", use_container_width=True): navigate_to('landing')

    st.title("📊 Dashboard Admin (Pro + Export)")
    
    if df_trx.empty: 
        st.warning("⚠️ Belum ada data. Silakan lakukan transaksi dulu.")
        return

    # --- METRICS UTAMA ---
    total_revenue = df_trx['total_price'].sum()
    total_orders = len(df_trx) 
    avg_order = total_revenue / total_orders if total_orders > 0 else 0
    # Mode bisa error jika data kosong atau multimodal, kita handle aman
    best_seller = df_trx['menu_name'].mode()[0] if not df_trx['menu_name'].mode().empty else "-"
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>Omzet</div><div class='metric-value'>Rp {total_revenue:,.0f}</div><div class='metric-delta' style='color:#16a34a;'>↗ All Time</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>Transaksi</div><div class='metric-value'>{total_orders}</div><div class='metric-delta' style='color:#2563eb;'>📦 Total Item</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>Rata-rata</div><div class='metric-value'>Rp {avg_order:,.0f}</div><div class='metric-delta' style='color:#d97706;'>💵 / Item</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-label'>Favorit</div><div class='metric-value' style='font-size:18px;'>{best_seller}</div><div class='metric-delta' style='color:#dc2626;'>⭐ Paling Laris</div></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- TABS ANALISIS ---
    tab1, tab2, tab3, tab4 = st.tabs(["💎 5-Tier Segmentasi", "📈 Tren Penjualan", "🍔 Analisis Menu", "📝 Data Transaksi"])
    
    # 1. TAB SEGMENTASI
    with tab1:
        c_left, c_right = st.columns([2, 1])
        with c_left:
            st.subheader("🔍 Peta Pelanggan (5 Level)")
            
            rfm = df_trx.groupby('customer_name').agg({
                'total_price': 'sum', 
                'order_datetime': 'count'
            }).reset_index()
            rfm.columns = ['Nama', 'Total_Belanja', 'Jumlah_Order']
            
            # Tier Calibration (Sesuai Visual Grafik)
            def get_5_tier_segment(row):
                val = row['Total_Belanja']
                if val >= 10_000_000: return '1. 💎 Diamond (VVIP)'
                elif val >= 4_500_000: return '2. 👑 Platinum (High)'
                elif val >= 3_000_000: return '3. 🥇 Gold (Mid-High)'
                elif val >= 1_000_000: return '4. 🥈 Silver (Mid-Low)'
                else: return '5. 🥉 Bronze (Low)'
            
            rfm['Segment'] = rfm.apply(get_5_tier_segment, axis=1)
            
            fig_cluster = px.scatter(
                rfm, x='Total_Belanja', y='Jumlah_Order', color='Segment',
                hover_data=['Nama'], title="Sebaran Pelanggan 5 Tingkat",
                color_discrete_map={
                    '1. 💎 Diamond (VVIP)': '#b9f2ff', 
                    '2. 👑 Platinum (High)': '#e5e4e2',
                    '3. 🥇 Gold (Mid-High)': '#FFD700', 
                    '4. 🥈 Silver (Mid-Low)': '#C0C0C0',
                    '5. 🥉 Bronze (Low)': '#cd7f32'
                },
                category_orders={"Segment": ["1. 💎 Diamond (VVIP)", "2. 👑 Platinum (High)", "3. 🥇 Gold (Mid-High)", "4. 🥈 Silver (Mid-Low)", "5. 🥉 Bronze (Low)"]}
            )
            fig_cluster.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_cluster, use_container_width=True)

        with c_right:
            st.subheader("💡 Strategi")
            st.markdown("""
            **1. 💎 Diamond (> 10 Juta)** Layanan Personal.
            **2. 👑 Platinum (> 4.5 Juta)** Paket Bundling.
            **3. 🥇 Gold (> 3 Juta)** Promo Diskon.
            **4. 🥈 Silver (> 1 Juta)** Voucher Reguler.
            **5. 🥉 Bronze (< 1 Juta)** Pancingan Buy 1 Get 1.
            """)    
            st.write(rfm['Segment'].value_counts())
        
    # 2. TAB SALES TREND
    with tab2:
        st.subheader("⏰ Tren Penjualan (Jam Sibuk)")
        
        df_trx['order_datetime'] = pd.to_datetime(df_trx['order_datetime'])
        df_trx['Jam'] = df_trx['order_datetime'].dt.hour
        
        hourly_sales = df_trx.groupby('Jam')['total_price'].sum().reset_index()
        all_hours = pd.DataFrame({'Jam': range(24)})
        hourly_sales = all_hours.merge(hourly_sales, on='Jam', how='left').fillna(0)

        fig_trend = px.area(
            hourly_sales, x='Jam', y='total_price', markers=True, 
            labels={'Jam': 'Jam (00-23)', 'total_price': 'Total Omzet'},
            color_discrete_sequence=['#818cf8']
        )
        fig_trend.update_xaxes(dtick=1)
        fig_trend.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_trend, use_container_width=True)

    # 3. TAB MENU ANALYSIS
    with tab3:
        st.subheader("🏆 Analisis Menu")
        df_minuman = df_trx[df_trx['category'] == 'Minuman']
        df_makanan = df_trx[df_trx['category'] != 'Minuman']
        c_food, c_drink = st.columns(2)
        
        with c_food:
            if not df_makanan.empty:
                top_food = df_makanan['menu_name'].value_counts().head(5).reset_index()
                top_food.columns = ['Menu', 'Terjual']
                st.plotly_chart(px.bar(top_food, x='Terjual', y='Menu', orientation='h', color='Terjual', color_continuous_scale='OrRd'), use_container_width=True)

        with c_drink:
            if not df_minuman.empty:
                top_drink = df_minuman['menu_name'].value_counts().head(5).reset_index()
                top_drink.columns = ['Menu', 'Terjual']
                st.plotly_chart(px.bar(top_drink, x='Terjual', y='Menu', orientation='h', color='Terjual', color_continuous_scale='Teal'), use_container_width=True)

    # 4. TAB DATA TRANSAKSI (DENGAN FITUR DOWNLOAD)
    with tab4:
        st.subheader("📝 Data Riwayat Transaksi")
        
        # Filter
        col_f1, col_f2 = st.columns([3, 1])
        with col_f1:
            pil_kategori = st.multiselect("Filter Kategori", df_trx['category'].unique())
        
        df_show = df_trx.sort_values(by='order_datetime', ascending=False)
        if pil_kategori:
            df_show = df_show[df_show['category'].isin(pil_kategori)]
            
        # Tampilkan Tabel
        st.dataframe(df_show, use_container_width=True)
        st.caption(f"Menampilkan {len(df_show)} baris data.")

        # --- FITUR DOWNLOAD ---
        st.markdown("### 📥 Export Laporan")
        
        # Convert DF to CSV
        csv = df_show.to_csv(index=False).encode('utf-8')
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📄 Download sebagai CSV",
                data=csv,
                file_name='laporan_penjualan_holygrail.csv',
                mime='text/csv',
                type='primary',
                use_container_width=True
            )
