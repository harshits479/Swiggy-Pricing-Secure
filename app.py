# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model

# Page config
st.set_page_config(page_title="Pricing Model", page_icon="💰", layout="wide")

# Custom CSS for compact styling
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 0.8rem 0;
        background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%);
        color: white;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
    }
    .main-header p {
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
    }
    .upload-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 0.8rem;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.3rem;
    }
    .stButton>button {
        height: 3rem;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .compact-metric {
        background-color: #e8f4f8;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
    }
    /* Reduce spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stExpander"] {
        margin-bottom: 0.5rem;
    }
    .stProgress > div > div {
        height: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>💰 Pricing Model Dashboard</h1>
        <p>Upload data files and generate intelligent pricing recommendations</p>
    </div>
    """, unsafe_allow_html=True)

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'model_run' not in st.session_state:
    st.session_state.model_run = False

# ==================== INSTRUCTIONS (Collapsible) ====================
with st.expander("📖 **HOW TO USE** - Click to view instructions", expanded=False):
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("""
        **Step 1:** Upload all 8 required CSV files in the sections below  
        **Step 2:** Monitor upload progress (must be 8/8)  
        **Step 3:** Click "Run Pricing Model" button  
        **Step 4:** Download pricing recommendations
        
        **📁 Required Files:**
        - **Scraped Data (3):** IM Prices, Competition Prices, NECC Prices
        - **Computation (2):** Sales Data, Stocks Data _(product_id, stock_level)_
        - **Static (3):** COGS _(product_id, product_name, cogs)_, SDPO, Exclusion List
        """)
    
    with col2:
        st.markdown("""
        **⚙️ Pricing Logic:**
        - Low stock (< 50): 40% markup
        - Medium (50-200): 30% markup
        - High stock (> 200): 20% markup
        """)

# ==================== FILE UPLOADS ====================

# Scraped Data Inputs
st.markdown('<div class="upload-card"><div class="section-title">📥 Scraped Data Inputs</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.caption("**IM Prices**")
    im_prices = st.file_uploader("IM", type=['csv'], key="im_prices", label_visibility="collapsed")
    if im_prices:
        df = pd.read_csv(im_prices)
        st.session_state.uploaded_files['im_prices'] = df
        st.success(f"✓ {len(df):,} rows")
    elif 'im_prices' in st.session_state.uploaded_files:
        st.info(f"✓ {len(st.session_state.uploaded_files['im_prices']):,} rows")

with col2:
    st.caption("**Competition Prices**")
    comp_prices = st.file_uploader("Comp", type=['csv'], key="comp_prices", label_visibility="collapsed")
    if comp_prices:
        df = pd.read_csv(comp_prices)
        st.session_state.uploaded_files['comp_prices'] = df
        st.success(f"✓ {len(df):,} rows")
    elif 'comp_prices' in st.session_state.uploaded_files:
        st.info(f"✓ {len(st.session_state.uploaded_files['comp_prices']):,} rows")

with col3:
    st.caption("**NECC Prices**")
    necc_prices = st.file_uploader("NECC", type=['csv'], key="necc_prices", label_visibility="collapsed")
    if necc_prices:
        df = pd.read_csv(necc_prices)
        st.session_state.uploaded_files['necc_prices'] = df
        st.success(f"✓ {len(df):,} rows")
    elif 'necc_prices' in st.session_state.uploaded_files:
        st.info(f"✓ {len(st.session_state.uploaded_files['necc_prices']):,} rows")

st.markdown('</div>', unsafe_allow_html=True)

# Computation Inputs
st.markdown('<div class="upload-card"><div class="section-title">🧮 Computation Inputs</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.caption("**Sales Data**")
    sales_file = st.file_uploader("Sales", type=['csv'], key="sales", label_visibility="collapsed")
    if sales_file:
        df = pd.read_csv(sales_file)
        st.session_state.uploaded_files['sales'] = df
        st.success(f"✓ {len(df):,} rows")
    elif 'sales' in st.session_state.uploaded_files:
        st.info(f"✓ {len(st.session_state.uploaded_files['sales']):,} rows")

with col2:
    st.caption("**Stocks Data** _(product_id, stock_level)_")
    stocks_file = st.file_uploader("Stocks", type=['csv'], key="stocks", label_visibility="collapsed")
    if stocks_file:
        df = pd.read_csv(stocks_file)
        st.session_state.uploaded_files['stocks'] = df
        st.success(f"✓ {len(df):,} rows")
    elif 'stocks' in st.session_state.uploaded_files:
        st.info(f"✓ {len(st.session_state.uploaded_files['stocks']):,} rows")

st.markdown('</div>', unsafe_allow_html=True)

# Static Inputs
st.markdown('<div class="upload-card"><div class="section-title">⚙️ Static Inputs <span style="font-size:0.85rem; font-weight:400; color:#666;">(Monthly updates)</span></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.caption("**COGS** _(product_id, product_name, cogs)_")
    cogs_file = st.file_uploader("COGS", type=['csv'], key="cogs", label_visibility="collapsed")
    if cogs_file:
        df = pd.read_csv(cogs_file)
        st.session_state.uploaded_files['cogs'] = df
        st.success(f"✓ {len(df):,} rows")
    elif 'cogs' in st.session_state.uploaded_files:
        st.info(f"✓ {len(st.session_state.uploaded_files['cogs']):,} rows")

with col2:
    st.caption("**Brand Aligned SDPO**")
    sdpo_file = st.file_uploader("SDPO", type=['csv'], key="sdpo", label_visibility="collapsed")
    if sdpo_file:
        df = pd.read_csv(sdpo_file)
        st.session_state.uploaded_files['sdpo'] = df
        st.success(f"✓ {len(df):,} rows")
    elif 'sdpo' in st.session_state.uploaded_files:
        st.info(f"✓ {len(st.session_state.uploaded_files['sdpo']):,} rows")

with col3:
    st.caption("**City Brand Exclusion**")
    exclusion_file = st.file_uploader("Exclusion", type=['csv'], key="exclusion", label_visibility="collapsed")
    if exclusion_file:
        df = pd.read_csv(exclusion_file)
        st.session_state.uploaded_files['exclusion'] = df
        st.success(f"✓ {len(df):,} rows")
    elif 'exclusion' in st.session_state.uploaded_files:
        st.info(f"✓ {len(st.session_state.uploaded_files['exclusion']):,} rows")

st.markdown('</div>', unsafe_allow_html=True)

# ==================== PROGRESS TRACKER & RUN BUTTON ====================
# Define all required files
all_required_files = [
    'im_prices', 'comp_prices', 'necc_prices',
    'sales', 'stocks',
    'cogs', 'sdpo', 'exclusion'
]

uploaded_count = sum(1 for key in all_required_files if key in st.session_state.uploaded_files)
is_ready = uploaded_count == len(all_required_files)

col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 1.5, 2])

with col1:
    scraped_count = sum(1 for key in ['im_prices', 'comp_prices', 'necc_prices'] if key in st.session_state.uploaded_files)
    st.metric("📥 Scraped", f"{scraped_count}/3", delta=None)

with col2:
    compute_count = sum(1 for key in ['sales', 'stocks'] if key in st.session_state.uploaded_files)
    st.metric("🧮 Compute", f"{compute_count}/2", delta=None)

with col3:
    static_count = sum(1 for key in ['cogs', 'sdpo', 'exclusion'] if key in st.session_state.uploaded_files)
    st.metric("⚙️ Static", f"{static_count}/3", delta=None)

with col4:
    st.metric("✅ Total", f"{uploaded_count}/8", delta=None)

with col5:
    run_button = st.button(
        "🚀 RUN MODEL" if is_ready else "⏳ UPLOAD FILES",
        type="primary",
        use_container_width=True,
        disabled=not is_ready
    )

progress = uploaded_count / len(all_required_files)
st.progress(progress)

# ==================== PROCESS MODEL ====================
if run_button:
    try:
        cogs_df = st.session_state.uploaded_files['cogs']
        stocks_df = st.session_state.uploaded_files['stocks']
        
        # Validate required columns
        required_cogs_cols = ['product_id', 'product_name', 'cogs']
        required_stocks_cols = ['product_id', 'stock_level']
        
        if not all(col in cogs_df.columns for col in required_cogs_cols):
            st.error(f"❌ COGS must contain: {', '.join(required_cogs_cols)}")
        elif not all(col in stocks_df.columns for col in required_stocks_cols):
            st.error(f"❌ Stocks must contain: {', '.join(required_stocks_cols)}")
        else:
            with st.spinner("⏳ Running pricing model..."):
                results_df = run_pricing_model(cogs_df, stocks_df)
                st.session_state.results_df = results_df
                st.session_state.model_run = True
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# ==================== DISPLAY RESULTS (Only if model has been run) ====================
if st.session_state.model_run and st.session_state.results_df is not None:
    results_df = st.session_state.results_df
    
    st.success(f"✅ Model completed successfully!", icon="🎉")
    
    # Modeled Prices Insights
    st.markdown('<div class="upload-card"><div class="section-title">📊 Modeled Prices Insights</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Products", f"{len(results_df):,}")
    with col2:
        st.metric("Average Price", f"${results_df['recommended_price'].mean():.2f}")
    with col3:
        st.metric("Min Price", f"${results_df['recommended_price'].min():.2f}")
    with col4:
        st.metric("Max Price", f"${results_df['recommended_price'].max():.2f}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Download button
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="⬇️ DOWNLOAD MODELED PRICES TABLE (CSV)",
        data=csv,
        file_name="modeled_prices.csv",
        mime="text/csv",
        use_container_width=True,
        type="primary"
    )
