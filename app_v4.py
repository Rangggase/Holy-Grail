import streamlit as st
import pandas as pd
import tensorflow as tf
import pickle
import os
from sqlalchemy import create_engine

# --- IMPORT MODULES ---
# Pastikan file kasir_view.py & admin_view.py ada di folder yang sama
try:
    from kasir_view import show_kasir_page
    from admin_view import show_admin_dashboard
except ImportError as e:
    st.error(f"❌ Error Import: {e}")
    st.stop()

# --- KONFIGURASI DATABASE ---
DB_USER = "postgres"
DB_PASS = "admin123" 
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "food_delivery_db"
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Final Project", layout="wide", page_icon="⚡", initial_sidebar_state="collapsed")

# --- CSS GLOBAL ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; background-image: radial-gradient(circle at center, #1f2937 0%, #0e1117 100%); }
    .block-container { padding-top: 2rem !important; }
    .login-card-container { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(25px); border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 20px 40px rgba(0,0,0,0.4); padding: 30px 25px; text-align: center; color: white; margin-top: 2vh; max-width: 400px; margin-left: auto; margin-right: auto; }
    .login-title { font-size: 22px; font-weight: 800; margin-bottom: 5px; letter-spacing: -0.5px; }
    .login-divider { display: flex; align-items: center; color: #64748b; margin: 20px 0; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
    .login-divider::before, .login-divider::after { content: ""; flex: 1; border-bottom: 1px solid #334155; margin: 0 10px; }
    div[data-testid="stButton"] > button:first-child { background: linear-gradient(to right, #4f46e5, #7c3aed); color: white; border: none; border-radius: 12px; font-weight:700; }
    .bill-box { background-color: #ffffff; border-radius: 16px; padding: 20px; border: 1px solid #eef2f6; color: black; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
</style>
""", unsafe_allow_html=True)

# Helper Logo
def get_logo_svg(width="100%", height="100%"):
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="grad_spark" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#22d3ee;stop-opacity:1" /><stop offset="50%" style="stop-color:#818cf8;stop-opacity:1" /><stop offset="100%" style="stop-color:#e879f9;stop-opacity:1" /></linearGradient><filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><path d="M 70 20 A 35 35 0 1 0 70 80" fill="none" stroke="url(#grad_spark)" stroke-width="12" stroke-linecap="round" filter="url(#glow)" /><path d="M 60 10 L 45 45 L 65 45 L 40 90" fill="none" stroke="#ffffff" stroke-width="0" fill-opacity="1"><animate attributeName="opacity" values="0.8;1;0.8" dur="2s" repeatCount="indefinite" /></path><polygon points="75,5 55,45 75,45 55,95 85,50 65,50" fill="url(#grad_spark)" transform="translate(-10, 0)" filter="url(#glow)"/></svg>"""

# --- LOAD RESOURCES SQL ---
@st.cache_resource
def get_resources():
    print(f"🔌 Mencoba koneksi ke: {DATABASE_URL}")
    try:
        engine = create_engine(DATABASE_URL)
        # Test koneksi langsung
        with engine.connect() as conn:
            pass 
        
        # --- PATH FILE BARU ---
        model_path = 'models/context_model.h5'
        encoder_path = 'models/context_encoders.pkl'
        
        if os.path.exists(model_path) and os.path.exists(encoder_path):
            # Load Model AI
            model_ncf = tf.keras.models.load_model(model_path, compile=False)
            
            # Load Encoders
            with open(encoder_path, 'rb') as f: 
                data = pickle.load(f)
            
            # --- FIX: KUNCI DICTIONARY DISESUAIKAN ---
            # Menggunakan 'user_id' dan 'menu_id' sesuai isi file .pkl
            return engine, model_ncf, data['user_id'], data['menu_id']
        else:
            st.warning("⚠️ Model AI tidak ditemukan di folder 'models/'. Pastikan file 'context_model.h5' ada.")
            return engine, None, None, None

    except Exception as e:
        # Tampilkan error merah jika masih gagal
        st.error(f"❌ Error System: {e}")
        return None, None, None, None

engine, model_ncf, user_enc, item_enc = get_resources()

# Load Helper Data
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

# --- NAVIGASI ---
if 'page' not in st.session_state: st.session_state['page'] = 'landing'
if 'cart' not in st.session_state: st.session_state['cart'] = {}

def navigate_to(page):
    st.session_state['page'] = page
    st.rerun()

# --- ROUTING ---
if st.session_state['page'] == 'landing':
    # HALAMAN LOGIN
    st.markdown("""<style>[data-testid="collapsedControl"] { display: none; }</style>""", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 1.5, 1])
    with col_center:
        st.markdown('<div class="login-card-container">', unsafe_allow_html=True)
        st.markdown(f"""<div style="display: flex; justify-content: center; margin-bottom: 15px;">{get_logo_svg(width="60", height="60")}</div>""", unsafe_allow_html=True)
        st.markdown("""<h1 class="login-title"></h1><p class="login-subtitle"></p>""", unsafe_allow_html=True)

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
    # PANGGIL KASIR & BAWA BEKAL
    df_menu = get_data_menu()
    show_kasir_page(engine, df_menu, model_ncf, user_enc, item_enc, navigate_to, get_logo_svg)

elif st.session_state['page'] == 'admin_dashboard':
    # PANGGIL ADMIN & BAWA BEKAL
    df_trx = get_data_transaksi()
    show_admin_dashboard(df_trx, navigate_to, get_logo_svg)