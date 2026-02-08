# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model
import io

# Page config
st.set_page_config(page_title="Swiggy Pricing Commander", page_icon="💰", layout="wide")

# Custom CSS
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
    .upload-card {
        background: #f8f9fa;
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #fc8019;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background: #fc8019;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>🥚 Swiggy Instamart: Egg Pricing Commander</h1>
        <p>Smart pricing optimization powered by Price Sensitivity & Elasticity</p>
    </div>
    """, unsafe_allow_html=True)

# Initialize session state
if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'model_run' not in st.session_state: st.session_state.model_run = False
if 'summary' not in st.session_state: st.session_state.summary = None
if 'opp_upload' not in st.session_state: st.session_state.opp_upload = None
if 'branded_upload' not in st.session_state: st.session_state.branded_upload = None

# Sidebar Inputs
st.sidebar.header("Configuration")
selected_category = st.sidebar.selectbox("Category", ["Eggs", "Dairy", "Bread"], index=0)
target_margin = st.sidebar.slider("Target Net Margin (%)", 0, 50, 15)

# ==================== FILE UPLOADS ====================
st.markdown('<div class="upload-card"><h3>📥 Upload Data</h3></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    cogs_file = st.file_uploader("Upload COGS (Required)", type=['csv'], key="cogs")
with col2:
    sdpo_file = st.file_uploader("Upload SDPO (Optional)", type=['csv'], key="sdpo")

if cogs_file:
    uploaded_cogs = pd.read_csv(cogs_file)
    st.success(f"✅ Loaded {len(uploaded_cogs)} products from COGS.")
else:
    st.info("Waiting for COGS file...")

# ==================== RUN MODEL ====================
if st.button("🚀 Run Pricing Model", disabled=not cogs_file):
    with st.spinner("Initializing Pricing Engine..."):
        try:
            # 1. Load User Uploads
            cogs_df = pd.read_csv(cogs_file)
            sdpo_df = pd.read_csv(sdpo_file) if sdpo_file else None
            
            # 2. GENERATE ROBUST DATA (or Load from Drive/Folder in Prod)
            # This block ensures the app works even if 'data/' folder is empty/missing
            
            # Normalize column names first to extract IDs
            if 'product_id' in cogs_df.columns: cogs_df = cogs_df.rename(columns={'product_id': 'Item Code', 'product_name': 'Item Name'})
            if 'sku' in cogs_df.columns: cogs_df = cogs_df.rename(columns={'sku': 'Item Code'})
            
            # Create lists for dummy generation
            ids = cogs_df['Item Code'].astype(str).tolist()
            names = cogs_df['Item Name'].tolist() if 'Item Name' in cogs_df.columns else [f"Item {i}" for i in ids]
            
            # --- Dummy/Fallback Data Creation (Matches IDs from COGS) ---
            df_im = pd.DataFrame({
                'Item Code': ids,
                'City': ['Bangalore'] * len(ids),
                'Item Name': names,
                'UOM': ['10_pieces'] * len(ids),
                'MRP': [100] * len(ids)
            })
            
            df_comp = pd.DataFrame({
                'Item Name': names[:len(names)//2], # Partial match
                'City': ['Bangalore'] * (len(names)//2),
                'UOM': ['10_pieces'] * (len(names)//2),
                'Selling Price': [90] * (len(names)//2)
            })
            
            df_necc = pd.DataFrame({'UOM': ['10_pieces'], 'Price': [85]})
            
            df_stock = pd.DataFrame({
                'Item Code': ids,
                'Stock Level': [100] * len(ids)
            })
            
            df_gmv = pd.DataFrame({'category': [selected_category], 'weight': [1.0]})
            
            df_sensitivity = pd.DataFrame({
                'Item Code': ids,
                'Sensitivity Score': [-1.5] * len(ids) # Elasticity assumption
            })
            
            city_mapping = pd.DataFrame({'City': ['Bangalore'], 'CITY_ID': [1]})
            spin_mapping = pd.DataFrame({'Item Code': ids, 'spin_id': range(1000, 1000+len(ids))})
            exclusions = pd.DataFrame()
            
            # 3. CALL THE ENGINE
            results_df, summary, opp_upload, branded_upload = run_pricing_model(
                im_pricing=df_im,
                comp_pricing=df_comp,
                necc_pricing=df_necc,
                cogs_df=cogs_df,
                sdpo_df=sdpo_df,
                stock_insights=df_stock,
                gmv_weights=df_gmv,
                price_sensitivity=df_sensitivity,
                city_mapping=city_mapping,
                spin_mapping=spin_mapping,
                exclusions=exclusions,
                target_margin=target_margin,
                category=selected_category
            )
            
            # 4. Save to Session
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
    df = st.session_state.results_df
    summary = st.session_state.summary
    
    st.success("✅ Pricing Model Run Complete!")
    
    # KPIS
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total SKUs", summary['total_products'])
    col2.metric("Avg Net Margin", f"{summary['avg_net_margin']:.1f}%")
    col3.metric("Price Index", f"{summary['avg_price_index']:.1f}")
    col4.metric("GMV Goodness", f"{summary['avg_gmv_goodness']:.2f}")
    
    # Detailed Table
    st.subheader("📋 Pricing Recommendations")
    
    display_cols = ['Item Code', 'Item Name', 'COGS', 'Final Price', 'net_margin', 'price_index', 'gmv_goodness']
    # Filter only columns that exist
    actual_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[actual_cols].style.format({
            'COGS': '₹{:.2f}',
            'Final Price': '₹{:.2f}',
            'net_margin': '{:.1f}%',
            'gmv_goodness': '{:.2f}'
        }),
        use_container_width=True
    )
    
    # Downloads
    st.subheader("📥 Download Upload Files")
    c1, c2 = st.columns(2)
    
    if st.session_state.branded_upload is not None:
        csv = st.session_state.branded_upload.to_csv(index=False).encode('utf-8')
        c1.download_button("Download Branded Price File", csv, "branded_upload.csv", "text/csv")
        
    if st.session_state.opp_upload is not None and not st.session_state.opp_upload.empty:
        csv_opp = st.session_state.opp_upload.to_csv(index=False).encode('utf-8')
        c2.download_button("Download OPP Price File", csv_opp, "opp_upload.csv", "text/csv")
