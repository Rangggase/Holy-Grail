import streamlit as st
import pandas as pd
import tensorflow as tf
import pickle
import os
from sqlalchemy import create_engine, text

# --- 1. SETUP HALAMAN (WAJIB DI ATAS) ---
st.set_page_config(page_title="Final Project", layout="wide", page_icon="⚡", initial_sidebar_state="collapsed")

# --- 2. CSS GLOBAL ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; background-image: radial-gradient(circle at center, #1f2937 0%, #0e1117 100%); }
    .block-container { padding-top: 2rem !important; }
    .login-card-container { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(25px); border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 20px 40px rgba(0,0,0,0.4); padding: 30px 25px; text-align: center; color: white; margin-top: 2vh; max-width: 400px; margin-left: auto; margin-right: auto; }
    .login-title { font-size: 22px; font-weight: 800; margin-bottom: 5px; letter-spacing: -0.5px; }
    .login-divider { display: flex; align-items: center; color: #64748b; margin: 20px 0; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
    .login-divider::before, .login-divider::after { content: ""; flex: 1; border-bottom: 1px solid #334155; margin: 0 10px; }
    div[data-testid="stButton"] > button:first-child { background: linear-gradient(to right, #4f46e5, #7c3aed); color: white; border: none; border-radius: 12px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# --- 3. KONEKSI DATABASE (SUPER STRICT) ---
# Kita hapus opsi localhost. Kalau gagal, STOP aplikasi.
try:
    if "postgres" in st.secrets:
        db = st.secrets["postgres"]
        DATABASE_URL = f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['dbname']}"
    else:
        st.error("❌ ERROR FATAL: Secrets '[postgres]' tidak ditemukan!")
        st.info("💡 Solusi: Buka Streamlit Cloud -> Settings -> Secrets. Pastikan isinya dimulai dengan [postgres]")
        st.stop()
except Exception as e:
    st.error(f"❌ Terjadi kesalahan saat membaca Secrets: {e}")
    st.stop()

# --- 4. LOAD RESOURCES (MODEL & DATABASE) ---
@st.cache_resource
def get_resources():
    # A. KONEKSI DATABASE
    try:
        engine = create_engine(DATABASE_URL)
        # Test koneksi (Penting!)
        with engine.connect() as conn:
            pass 
    except Exception as e:
        st.error(f"❌ Gagal Konek ke Neon Database: {e}")
        return None, None, None, None

    # B. LOAD MODEL AI (AUTO DETECT)
    # Cek file Cloud dulu, baru lokal
    if os.path.exists('ncf_model_sql.h5'):
        model_path = 'ncf_model_sql.h5'
        encoder_path = 'encoders_sql.pkl'
    elif os.path.exists('models/context_model.h5'): # Fallback laptop
        model_path = 'models/context_model.h5'
        encoder_path = 'models/context_encoders.pkl'
    else:
        st.warning("⚠️ Model AI tidak ditemukan. Rekomendasi akan error.")
        return engine, None, None, None

    try:
        model_ncf = tf.keras.models.load_model(model_path, compile=False)
        with open(encoder_path, 'rb') as f: 
            data = pickle.load(f)
        
        # Ambil encoder dengan aman
        u_enc = data.get('user_id') if 'user_id' in data else data.get('user_encoder')
        m_enc = data.get('menu_id') if 'menu_id' in data else data.get('item_encoder')
        
        return engine, model_ncf, u_enc, m_enc

    except Exception as e:
        st.warning(f"⚠️ Gagal load model AI: {e}")
        return engine, None, None, None

engine, model_ncf, user_enc, item_enc = get_resources()

# --- 5. IMPORT HALAMAN LAIN (SETELAH KONEKSI AMAN) ---
try:
    from kasir_view import show_kasir_page
    from admin_view import show_admin_dashboard
except ImportError as e:
    st.error(f"❌ Error Import File: {e}")
    st.stop()

# --- 6. LOGIC APP UTAMA ---
# Helper Data Functions
def get_data_menu():
    if engine is None: return pd.DataFrame()
    return pd.read_sql("SELECT * FROM menu", engine)

def get_data_transaksi():
    if engine is None: return pd.DataFrame()
    query = """
    SELECT o.timestamp as order_datetime, m.menu_name, m.price as total_price, 
           m.category, u.name as customer_name
    FROM orders o
    JOIN menu m ON o.menu_id = m.menu_id
    JOIN users u ON o.user_id = u.user_id
    """
    df = pd.read_sql(query, engine)
    if not df.empty:
        df['order_datetime'] = pd.to_datetime(df['order_datetime'])
    return df

def get_logo_svg(width="100%", height="100%"):
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><path d="M 50 10 L 10 90 L 90 90 Z" fill="#6366f1"/></svg>"""

# Navigasi & Routing
if 'page' not in st.session_state: st.session_state['page'] = 'landing'
if 'cart' not in st.session_state: st.session_state['cart'] = {}

def navigate_to(page):
    st.session_state['page'] = page
    st.rerun()

if st.session_state['page'] == 'landing':
    # HALAMAN LOGIN
    st.markdown("""<style>[data-testid="collapsedControl"] { display: none; }</style>""", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 1.5, 1])
    with col_center:
        st.markdown('<div class="login-card-container">', unsafe_allow_html=True)
        st.markdown(f"""<div style="display: flex; justify-content: center; margin-bottom: 15px;">{get_logo_svg(width="60", height="60")}</div>""", unsafe_allow_html=True)
        st.markdown("""<h1 class="login-title">HOLY GRAIL POS</h1><p class="login-subtitle">Sistem Kasir Cerdas & Terintegrasi</p>""", unsafe_allow_html=True)

        if st.button("🏪 Masuk Kasir", key="btn_kasir_primary", use_container_width=True): navigate_to('kasir_main')
        st.markdown("""<div class="login-divider">ADMIN ACCESS</div>""", unsafe_allow_html=True)
        password = st.text_input("🔐", type="password", placeholder="Password admin...", label_visibility="collapsed")
        if st.button("Login Admin ➝", key="btn_admin_secondary", use_container_width=True):
            if password == "admin123":
                st.toast("Login Berhasil!", icon="✅")
                navigate_to('admin_dashboard')
            else:
                st.error("Password Salah!")
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state['page'] == 'kasir_main':
    df_menu = get_data_menu()
    show_kasir_page(engine, df_menu, model_ncf, user_enc, item_enc, navigate_to, get_logo_svg)

elif st.session_state['page'] == 'admin_dashboard':
    df_trx = get_data_transaksi()
    show_admin_dashboard(df_trx, navigate_to, get_logo_svg)
