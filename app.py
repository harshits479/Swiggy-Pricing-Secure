# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model
import io

# Page config
st.set_page_config(page_title="Swiggy Pricing Commander", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1.2rem 0;
        background: linear-gradient(135deg, #fc8019 0%, #ff5e00 100%);
        color: white;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div class="main-header">
        <h1>🥚 Swiggy Instamart: Egg Pricing Commander</h1>
        <p>Smart pricing optimization powered by Price Sensitivity & Elasticity</p>
    </div>
    """, unsafe_allow_html=True)

if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'model_run' not in st.session_state: st.session_state.model_run = False
if 'summary' not in st.session_state: st.session_state.summary = None
if 'opp_upload' not in st.session_state: st.session_state.opp_upload = None
if 'branded_upload' not in st.session_state: st.session_state.branded_upload = None

st.sidebar.header("Configuration")
selected_category = st.sidebar.selectbox("Category", ["Eggs", "Dairy", "Bread"], index=0)
target_margin = st.sidebar.slider("Target Net Margin (%)", 0, 50, 15)

col1, col2 = st.columns(2)
with col1:
    cogs_file = st.file_uploader("Upload COGS (Required)", type=['csv'], key="cogs")
with col2:
    sdpo_file = st.file_uploader("Upload SDPO (Optional)", type=['csv'], key="sdpo")

if cogs_file:
    cogs_file.seek(0)
    uploaded_cogs = pd.read_csv(cogs_file)
    st.success(f"✅ Loaded {len(uploaded_cogs)} products from COGS.")
    cogs_file.seek(0)

if st.button("🚀 Run Pricing Model", disabled=not cogs_file):
    with st.spinner("Initializing Pricing Engine..."):
        try:
            cogs_file.seek(0)
            cogs_df = pd.read_csv(cogs_file)
            
            sdpo_df = None
            if sdpo_file:
                sdpo_file.seek(0)
                sdpo_df = pd.read_csv(sdpo_file)
            
            # --- Dummy Data Gen ---
            if 'product_id' in cogs_df.columns: cogs_df = cogs_df.rename(columns={'product_id': 'Item Code', 'product_name': 'Item Name'})
            if 'sku' in cogs_df.columns: cogs_df = cogs_df.rename(columns={'sku': 'Item Code'})
            
            ids = cogs_df['Item Code'].astype(str).tolist()
            names = cogs_df['Item Name'].tolist() if 'Item Name' in cogs_df.columns else [f"Item {i}" for i in ids]
            
            df_im = pd.DataFrame({
                'Item Code': ids,
                'City': ['Bangalore'] * len(ids),
                'Item Name': names,
                'UOM': ['10_pieces'] * len(ids),
                'Selling Price': [100] * len(ids), # Important for GMV calc
                'MRP': [110] * len(ids)
            })
            
            df_comp = pd.DataFrame({
                'Item Name': names,
                'City': ['Bangalore'] * len(names),
                'UOM': ['10_pieces'] * len(names),
                'Selling Price': [90] * len(names)
            })
            
            df_necc = pd.DataFrame({'UOM': ['10_pieces'], 'Price': [85]})
            df_stock = pd.DataFrame({'Item Code': ids, 'Stock Level': [100] * len(ids)})
            df_gmv = pd.DataFrame({'category': [selected_category], 'weight': [1.0]})
            
            # Simulated Sensitivity (-1.5 means price cut = huge volume)
            df_sensitivity = pd.DataFrame({'Item Code': ids, 'Sensitivity Score': [-1.5] * len(ids)})
            
            city_mapping = pd.DataFrame({'City': ['Bangalore'], 'CITY_ID': [1]})
            spin_mapping = pd.DataFrame({'Item Code': ids, 'spin_id': range(1000, 1000+len(ids))})
            exclusions = pd.DataFrame()
            
            results_df, summary, opp_upload, branded_upload = run_pricing_model(
                df_im, df_comp, df_necc, cogs_df, sdpo_df, df_stock, df_gmv, df_sensitivity, 
                city_mapping, spin_mapping, exclusions, target_margin, selected_category
            )
            
            st.session_state.results_df = results_df
            st.session_state.summary = summary
            st.session_state.opp_upload = opp_upload
            st.session_state.branded_upload = branded_upload
            st.session_state.model_run = True
            
        except Exception as e:
            st.error(f"❌ Error running model: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# ==================== DISPLAY RESULTS ====================
if st.session_state.model_run and st.session_state.results_df is not None:
    summary = st.session_state.summary
    
    st.markdown("### 📊 Key Performance Indicators")
    
    col1, col2 = st.columns(2)
    
    # Modeled NM
    col1.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #555;">Modeled Net Margin</h3>
            <h1 style="color: #fc8019; font-size: 3rem;">{summary['avg_net_margin']:.1f}%</h1>
            <p>Target: {target_margin}%</p>
        </div>
    """, unsafe_allow_html=True)
    
    # GMV Uplift
    uplift = summary['avg_gmv_uplift']
    color = "green" if uplift >= 0 else "red"
    sign = "+" if uplift >= 0 else ""
    
    col2.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #555;">GMV Goodness (Uplift)</h3>
            <h1 style="color: {color}; font-size: 3rem;">{sign}{uplift:.1f}%</h1>
            <p>Expected Revenue Impact</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.success("Pricing successfully Modeled.")
    
    # Downloads
    st.markdown("---")
    st.subheader("📥 Download Upload Files")
    c1, c2 = st.columns(2)
    
    if st.session_state.branded_upload is not None:
        csv = st.session_state.branded_upload.to_csv(index=False).encode('utf-8')
        c1.download_button("Download Branded Price File", csv, "branded_upload.csv", "text/csv")
        
    if st.session_state.opp_upload is not None and not st.session_state.opp_upload.empty:
        csv_opp = st.session_state.opp_upload.to_csv(index=False).encode('utf-8')
        c2.download_button("Download OPP Price File", csv_opp, "opp_upload.csv", "text/csv")
