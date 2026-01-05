import streamlit as st
import pandas as pd
import numpy as np
import pickle
import tensorflow as tf
import os  # <--- Saya tambah ini biar bisa cek file
from datetime import datetime
from sqlalchemy import text

# ==========================================
# 🧠 KONFIGURASI MODEL (AI 70 MENU)
# ==========================================
# FIX: Otomatis pilih jalur file (Cloud atau Laptop)
if os.path.exists('ncf_model_sql.h5'):
    MODEL_PATH = 'ncf_model_sql.h5'      # Jalur Cloud (GitHub)
    ENCODER_PATH = 'encoders_sql.pkl'
else:
    MODEL_PATH = 'models/context_model.h5'       # Jalur Laptop
    ENCODER_PATH = 'models/context_encoders.pkl'

@st.cache_resource
def load_ai_brain():
    try:
        # Kita gunakan try-except agar tidak error fatal
        if os.path.exists(MODEL_PATH):
            model = tf.keras.models.load_model(MODEL_PATH, compile=False)
        else:
            model = None
            
        if os.path.exists(ENCODER_PATH):
            with open(ENCODER_PATH, "rb") as f:
                encoders = pickle.load(f)
        else:
            encoders = None
            
        return model, encoders
    except Exception as e:
        return None, None

# ==========================================
# 🏷️ KNOWLEDGE BASE (TAGS)
# ==========================================
TAGS_DB = {
    "paket": ["Sharing", "Rame", "Keluarga"],
    "bucket": ["Sharing", "Rame", "Snack", "Keluarga"],
    "platter": ["Sharing", "Rame", "Keluarga"],
    "gurame": ["Sharing", "Berat", "Keluarga"],
    "pizza": ["Sharing", "Rame", "Keluarga"],
    "tumpeng": ["Sharing", "Rame", "Keluarga"],
    "martabak": ["Sharing", "Snack"],
    "sate kambing": ["Sharing", "Berat"],
    "sop": ["Kuah", "Hangat"],
    "soto": ["Kuah", "Hangat"],
    "rawon": ["Kuah", "Hangat"],
    "bakso": ["Kuah", "Hangat"],
    "godog": ["Kuah", "Hangat"],
    "seblak": ["Kuah", "Hangat", "Pedas"],
    "ramen": ["Kuah", "Hangat"],
    "sayur asem": ["Kuah", "Hangat"],
    "capcay": ["Kuah", "Hangat"],
    "es ": ["Dingin"],
    "jus": ["Dingin"],
    "soda": ["Dingin"],
    "tea cold": ["Dingin"],
    "milkshake": ["Dingin"],
    "cola": ["Dingin"],
    "sprite": ["Dingin"],
    "air mineral": ["Dingin"],
    "kopi": ["Hangat"],
    "wedang": ["Hangat"],
    "hot": ["Hangat"],
    "tarik": ["Hangat"],
    "tubruk": ["Hangat"],
    "bandrek": ["Hangat"]
}

def get_tags_for_menu(menu_name):
    tags = []
    m_lower = str(menu_name).lower()
    for keyword, t_list in TAGS_DB.items():
        if keyword in m_lower: tags.extend(t_list)
    return tags

def get_time_of_day():
    h = datetime.now().hour
    if 5 <= h < 11: return "Pagi"
    elif 11 <= h < 15: return "Siang"
    elif 15 <= h < 18: return "Siang"
    else: return "Malam"

def get_menu_image(name, cat):
    name = str(name).lower()
    if "paket" in name or "platter" in name: return "https://cdn-icons-png.flaticon.com/512/3075/3075977.png"
    if "soto" in name or "sop" in name or "ramen" in name: return "https://cdn-icons-png.flaticon.com/512/3480/3480765.png"
    if "es " in name or "jus" in name or "cola" in name: return "https://cdn-icons-png.flaticon.com/512/2405/2405597.png"
    if "kopi" in name or "hot" in name: return "https://cdn-icons-png.flaticon.com/512/924/924514.png"
    if "burger" in name or "pizza" in name: return "https://cdn-icons-png.flaticon.com/512/3075/3075929.png"
    return "https://cdn-icons-png.flaticon.com/512/1375/1375283.png"

# ==========================================
# 🚀 HYBRID BOOSTER LOGIC (Final Version)
# ==========================================
def apply_hybrid_boost(row, weather, group_size, time_now):
    boost = 0.0
    tags = get_tags_for_menu(row['menu_name'])
    
    # Logic Keluarga (High Priority)
    if group_size == "Keluarga":
        if "Keluarga" in tags or "Sharing" in tags:
            boost += 10.0 
    
    # Logic Cuaca
    if weather == "Hujan" and "Hangat" in tags: boost += 2.0
    if weather == "Cerah" and "Dingin" in tags: boost += 2.0
        
    return row['ai_score'] + boost

# ==========================================
# 🖥️ UI KASIR (LENGKAP: BAYAR + STRUK)
# ==========================================
def show_kasir_page(engine, df_menu, model_ignored, user_enc_ignored, item_enc_ignored, navigate_to, get_logo_svg):
    
    # KITA PAKAI MODEL DARI MAIN.PY JIKA ADA, KALAU TIDAK LOAD SENDIRI
    model_local, encoders = load_ai_brain()
    
    # Prioritas: Pakai model yang dikirim dari App Utama (biar hemat memori)
    # Tapi kalau App Utama gagal load, pakai model_local yang barusan kita load
    model_ai = model_ignored if model_ignored is not None else model_local

    # CSS Styles
    st.markdown("""
    <style>
    .marquee-box { background: #1e293b; color: #fbbf24; padding: 8px; font-size: 14px; white-space: nowrap; overflow: hidden; margin-bottom: 10px; border-radius: 8px; border: 1px solid #334155; }
    .control-panel { background: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .hero-container { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 16px; padding: 20px; border: 1px solid #6366f1; margin-bottom: 25px; box-shadow: 0 10px 20px rgba(99, 102, 241, 0.15); color: white; }
    .rec-title { color: #fbbf24; font-size: 14px; font-weight: bold; margin-top: 15px; border-bottom: 1px solid #334155; padding-bottom: 5px; }
    .bill-box { background: white; padding: 15px; border-radius: 10px; border: 2px dashed #cbd5e1; }
    </style>
    """, unsafe_allow_html=True)

    # --- SIDEBAR DEBUG & NAV ---
    with st.sidebar:
        st.markdown(f"""<div style="text-align:center;">{get_logo_svg(width="50", height="50")}</div>""", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; color:white;'>HOLY GRAIL POS</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Debug AI Brain Status
        with st.expander("🔍 System Status"):
            if encoders:
                # FIX: Cek kunci dictionary biar tidak error (user_id vs user_encoder)
                u_key = 'user_id' if 'user_id' in encoders else 'user_encoder'
                m_key = 'menu_id' if 'menu_id' in encoders else 'item_encoder'
                
                st.write(f"🧠 AI Menu Memory: {len(encoders[m_key].classes_)}")
                st.write(f"📚 DB Menu Count: {len(df_menu)}")
                if len(encoders[m_key].classes_) != len(df_menu):
                    st.error("⚠️ DATA BELUM SINKRON")
                else:
                    st.success("✅ AI & DB SINKRON")
            else:
                st.error("AI Offline")

        if st.button("🏠 Keluar", use_container_width=True): navigate_to('landing')

    st.markdown("""<div class='marquee-box'>📢 SYSTEM READY: Pembayaran Tunai & QRIS Aktif. Struk Otomatis. 🧾</div>""", unsafe_allow_html=True)

    # --- INPUT PANEL (CONTEXT) ---
    with st.container():
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1: search_name = st.text_input("👤 Pelanggan", placeholder="Ketik nama...", label_visibility="collapsed")
        with c2: weather = st.selectbox("Cuaca", ["Cerah", "Hujan"], label_visibility="collapsed")
        with c3: group_size = st.selectbox("Grup", ["Sendiri", "Keluarga"], label_visibility="collapsed")
        with c4: 
            time_now = get_time_of_day()
            display_time = "Sore" if 15 <= datetime.now().hour < 18 else time_now 
            st.markdown(f"<div style='text-align:center; padding:8px; background:#e2e8f0; border-radius:8px; color:#334155; font-weight:bold;'>🕒 {display_time}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- USER SEARCH LOGIC ---
    cust_id, cust_status, final_cust_name = None, "Baru", search_name
    if search_name:
        try:
            with engine.connect() as conn:
                found_users = conn.execute(text("SELECT user_id, name FROM users WHERE name ILIKE :nm LIMIT 5"), {"nm": f"%{search_name}%"}).fetchall()
            if found_users:
                options = {f"{u[1]} (ID:{u[0]})": u for u in found_users}
                new_opt = f"➕ Baru: '{search_name}'"
                options[new_opt] = None
                choice = st.selectbox("📋 Pilih Member:", list(options.keys()))
                if choice != new_opt:
                    cust_id, final_cust_name = options[choice]
                    cust_status = "Lama"
                    st.success(f"✅ MEMBER: {final_cust_name}")
                else: st.info(f"🆕 BARU: {final_cust_name}")
            else: st.info(f"🆕 BARU: {final_cust_name}")
        except: pass

    # ==========================================
    # 🔥 AI RECOMMENDATION ENGINE
    # ==========================================
    if search_name and model_ai and encoders:
        rec_df = df_menu.copy()
        rec_df['ai_score'] = 0.0

        # Filter Guillotine
        if weather == "Hujan":
            rec_df = rec_df[~rec_df['menu_name'].apply(lambda x: "Dingin" in get_tags_for_menu(x))]
        if group_size == "Sendiri":
            rec_df = rec_df[~rec_df['menu_name'].apply(lambda x: "Sharing" in get_tags_for_menu(x))]
        
        # AI Prediction
        if not rec_df.empty:
            try:
                # --- FIX: DETEKSI KUNCI ENCODER (Biar gak error KeyError) ---
                u_key = 'user_id' if 'user_id' in encoders else 'user_encoder'
                m_key = 'menu_id' if 'menu_id' in encoders else 'item_encoder'

                ctx_weather_id = encoders['weather'].transform([weather])[0]
                ctx_time_id = encoders['time_of_day'].transform([time_now])[0] 
                ctx_group_id = encoders['group_size'].transform([group_size])[0]
                
                u_id_enc = 0
                if cust_status == "Lama" and str(cust_id) in encoders[u_key].classes_:
                    u_id_enc = encoders[u_key].transform([str(cust_id)])[0]
                
                rec_df['menu_id_str'] = rec_df['menu_id'].astype(str)
                valid_menus = rec_df[rec_df['menu_id_str'].isin(encoders[m_key].classes_)]
                
                if not valid_menus.empty:
                    m_ids_enc = encoders[m_key].transform(valid_menus['menu_id_str'].values)
                    count = len(m_ids_enc)
                    scores = model_ai.predict(
                        [np.array([u_id_enc]*count), np.array(m_ids_enc), np.array([ctx_weather_id]*count), 
                         np.array([ctx_time_id]*count), np.array([ctx_group_id]*count)], verbose=0
                    ).flatten()
                    rec_df.loc[valid_menus.index, 'ai_score'] = scores
            except Exception as e: pass 

        # Hybrid Boost
        rec_df['final_score'] = rec_df.apply(lambda row: apply_hybrid_boost(row, weather, group_size, time_now), axis=1)
        rec_df = rec_df.sort_values('final_score', ascending=False)

        # Display Cards
        st.markdown('<div class="hero-container">', unsafe_allow_html=True)
        st.markdown(f"""<div style="font-size:18px; font-weight:bold; color:#fbbf24;">✨ Rekomendasi Cerdas</div>""", unsafe_allow_html=True)
        
        def render_cards(df, key_prefix):
            if df.empty: return
            cols = st.columns(4)
            for idx, (_, row) in enumerate(df.iterrows()):
                with cols[idx]:
                    img = get_menu_image(row['menu_name'], row['category'])
                    raw = row['final_score']
                    if raw > 5.0: score_text, score_color = "🔥 Super Match", "#f472b6"
                    elif raw > 0.1: score_text, score_color = f"{int((raw/5.0)*100)}% Match", "#4ade80"
                    else: score_text, score_color = "New Item", "#94a3b8"

                    st.markdown(f"""<div style="background:rgba(255,255,255,0.1); padding:10px; border-radius:10px; text-align:center;"><img src="{img}" style="width:50px; margin-bottom:5px;"><div style="font-size:11px; font-weight:bold; height:35px; display:flex; align-items:center; justify-content:center;">{row['menu_name']}</div><div style="color:{score_color}; font-size:11px; font-weight:bold;">{score_text}</div></div>""", unsafe_allow_html=True)
                    if st.button("AMBIL", key=f"{key_prefix}_{idx}", use_container_width=True):
                        m_name = row['menu_name']
                        if m_name in st.session_state['cart']: st.session_state['cart'][m_name]['qty'] += 1
                        else: st.session_state['cart'][m_name] = {'qty': 1, 'price': row['price'], 'id': row['menu_id'], 'category': row['category']}
                        st.toast(f"+ {m_name}")

        st.markdown('<div class="rec-title">🍽️ TOP MAKANAN</div>', unsafe_allow_html=True)
        render_cards(rec_df[rec_df['category'] != 'Minuman'].head(4), "food")
        st.markdown('<div class="rec-title">🥤 TOP MINUMAN</div>', unsafe_allow_html=True)
        render_cards(rec_df[rec_df['category'] == 'Minuman'].head(4), "drink")
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # 🛒 MENU & CART (DENGAN PEMBAYARAN & STRUK)
    # ==========================================
    col_menu, col_bill = st.columns([2.5, 1.5]) 
    
    with col_menu:
        st.subheader(f"📖 Buku Menu ({len(df_menu)} Item)") 
        search = st.text_input("Cari menu...", label_visibility="collapsed")
        cats = sorted(df_menu['category'].unique().tolist())
        if "Paket Jumbo" in cats: cats.remove("Paket Jumbo"); cats.insert(0, "Paket Jumbo")
        tabs = st.tabs(cats)
        for i, cat in enumerate(cats):
            with tabs[i]:
                filtered = df_menu[df_menu['category'] == cat]
                if search: filtered = filtered[filtered['menu_name'].str.contains(search, case=False)]
                cols = st.columns(3)
                for idx, (_, row) in enumerate(filtered.iterrows()):
                    with cols[idx % 3]:
                        img = get_menu_image(row['menu_name'], cat)
                        st.markdown(f"""<div style="background:white; border:1px solid #ddd; border-radius:10px; text-align:center; overflow:hidden;"><img src="{img}" style="width:100%; height:100px; object-fit:cover;"><div style="padding:5px;"><div style="font-weight:bold; font-size:12px; color:#333; height:35px;">{row['menu_name']}</div><div style="color:green; font-weight:bold;">Rp {row['price']:,}</div></div></div>""", unsafe_allow_html=True)
                        if st.button("➕", key=f"add_{row['menu_id']}", use_container_width=True):
                            m_name = row['menu_name']
                            if m_name in st.session_state['cart']: st.session_state['cart'][m_name]['qty'] += 1
                            else: st.session_state['cart'][m_name] = {'qty': 1, 'price': row['price'], 'id': row['menu_id'], 'category': row['category']}
                            st.rerun()

    # --- KERANJANG & CHECKOUT ---
    with col_bill:
        st.markdown('<div class="bill-box">', unsafe_allow_html=True)
        st.markdown('<h4>🛒 Keranjang Belanja</h4>', unsafe_allow_html=True)
        
        if not st.session_state['cart']:
            st.caption("Keranjang masih kosong.")
        else:
            total_belanja = 0
            # List Item
            for m, item in st.session_state['cart'].items():
                subtotal = item['qty'] * item['price']
                total_belanja += subtotal
                
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{m}**\n<small>@{item['price']:,}</small>", unsafe_allow_html=True)
                c2.write(f"x{item['qty']}")
                if c3.button("🗑️", key=f"del_{m}"): 
                    del st.session_state['cart'][m]
                    st.rerun()
            
            st.markdown("---")
            st.markdown(f"### Total: Rp {total_belanja:,}")
            
            # --- PEMBAYARAN ---
            st.write("💳 **Metode Pembayaran**")
            metode = st.selectbox("Pilih", ["Tunai", "QRIS", "Debit/Credit"], label_visibility="collapsed")
            
            bayar = 0
            kembalian = 0
            siap_bayar = False

            if metode == "Tunai":
                bayar = st.number_input("Uang Diterima (Rp)", min_value=0, value=total_belanja)
                kembalian = bayar - total_belanja
                if bayar >= total_belanja:
                    st.success(f"Kembalian: Rp {kembalian:,}")
                    siap_bayar = True
                else:
                    st.error("Uang kurang!")
            else:
                st.info("Silakan scan QRIS / Gesek Kartu")
                siap_bayar = True
                bayar = total_belanja # Anggap pas

            # --- TOMBOL BAYAR ---
            if siap_bayar:
                if st.button("✅ PROSES PEMBAYARAN", type="primary", use_container_width=True):
                    if not search_name:
                        st.error("Harap isi nama pelanggan!")
                    else:
                        try:
                            # 1. Simpan User (Kalau baru)
                            uid_final = cust_id
                            if not uid_final:
                                with engine.connect() as conn:
                                    res = conn.execute(text("INSERT INTO users (name, favorite_category) VALUES (:nm, 'Umum') RETURNING user_id"), {"nm": final_cust_name})
                                    uid_final = res.fetchone()[0]
                                    conn.commit()
                            
                            # 2. Simpan Transaksi (Orders)
                            ts_val = datetime.now()
                            with engine.connect() as conn:
                                for m, item in st.session_state['cart'].items():
                                    conn.execute(text("""
                                        INSERT INTO orders (user_id, menu_id, rating, weather, group_size, time_of_day, timestamp) 
                                        VALUES (:u, :m, 5, :w, :g, :t, :ts)
                                    """), {
                                        "u": uid_final, "m": item['id'], "w": weather, "g": group_size, "t": time_now, "ts": ts_val
                                    })
                                conn.commit()
                            
                            # 3. TAMPILKAN STRUK (Session State Trick)
                            st.session_state['last_trx'] = {
                                'name': final_cust_name,
                                'items': st.session_state['cart'],
                                'total': total_belanja,
                                'pay': bayar,
                                'change': kembalian,
                                'method': metode,
                                'time': ts_val.strftime("%Y-%m-%d %H:%M")
                            }
                            st.session_state['cart'] = {} # Kosongkan keranjang
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error Database: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

        # --- STRUK POP-UP (SETELAH BAYAR) ---
        if 'last_trx' in st.session_state and st.session_state['last_trx']:
            trx = st.session_state['last_trx']
            st.markdown("---")
            with st.expander("🧾 LIHAT STRUK TERAKHIR", expanded=True):
                st.markdown(f"""
                <div style="text-align:center; font-family:monospace;">
                    <h4>HOLY GRAIL RESTO</h4>
                    <p>{trx['time']}</p>
                    <p>Pelanggan: {trx['name']}</p>
                    <hr>
                </div>
                """, unsafe_allow_html=True)
                
                for m, item in trx['items'].items():
                    sub = item['qty'] * item['price']
                    st.markdown(f"<div style='display:flex; justify-content:space-between; font-family:monospace;'><span>{item['qty']}x {m}</span><span>{sub:,}</span></div>", unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="font-family:monospace;">
                    <hr>
                    <div style="display:flex; justify-content:space-between;"><b>TOTAL</b> <b>Rp {trx['total']:,}</b></div>
                    <div style="display:flex; justify-content:space-between;">Bayar ({trx['method']}) <span>{trx['pay']:,}</span></div>
                    <div style="display:flex; justify-content:space-between;">Kembali <span>{trx['change']:,}</span></div>
                    <hr>
                    <center>Terima Kasih!</center>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Transaksi Baru"):
                    del st.session_state['last_trx']
                    st.rerun()
