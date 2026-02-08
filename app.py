# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model

# Page config
st.set_page_config(page_title="Pricing Model", page_icon="💰", layout="wide")

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .upload-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .info-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #0066cc;
        margin-bottom: 1.5rem;
    }
    .success-box {
        background-color: #d4edda;
        padding: 0.5rem;
        border-radius: 5px;
        margin-top: 0.5rem;
    }
    .stButton>button {
        height: 3.5rem;
        font-size: 1.2rem;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>💰 Pricing Model Dashboard</h1>
        <p style="margin: 0; font-size: 1.1rem;">Upload your data files and generate intelligent pricing recommendations</p>
    </div>
    """, unsafe_allow_html=True)

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}

# Define all required files
all_required_files = [
    'im_prices', 'comp_prices', 'necc_prices',  # Scraped Data
    'sales', 'stocks',  # Computation Inputs
    'cogs', 'sdpo', 'exclusion'  # Static Inputs
]

uploaded_count = sum(1 for key in all_required_files if key in st.session_state.uploaded_files)
is_ready = uploaded_count == len(all_required_files)

# ==================== SECTION 1: INSTRUCTIONS ====================
with st.expander("📖 **HOW TO USE THIS TOOL** - Click to expand", expanded=True):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 📋 Quick Start Guide:
        
        **Step 1:** Upload all required files in the three sections below  
        **Step 2:** Monitor the progress tracker to see upload status  
        **Step 3:** Click the "Run Pricing Model" button once all files are uploaded  
        **Step 4:** Review results and download the pricing recommendations  
        
        ---
        
        ### 📁 File Requirements:
        
        **🔹 Scraped Data Inputs** (3 files)
        - IM Prices CSV
        - Competition Prices CSV  
        - NECC Prices CSV
        
        **🔹 Computation Inputs** (2 files)
        - Sales Data CSV
        - Stocks Data CSV _(must include: product_id, stock_level)_
        
        **🔹 Static Inputs** (3 files - update monthly)
        - COGS Inputs CSV _(must include: product_id, product_name, cogs)_
        - Brand Aligned SDPO CSV
        - City Brand Exclusion List CSV
        """)
    
    with col2:
        st.markdown("""
        ### ⚙️ Pricing Logic:
        
        **Low Stock**  
        < 50 units  
        → 40% markup
        
        **Medium Stock**  
        50-200 units  
        → 30% markup
        
        **High Stock**  
        \> 200 units  
        → 20% markup
        
        ---
        
        ### 💡 Tips:
        - All 8 files are required
        - Ensure CSV format
        - Check column names match requirements
        - Static inputs need monthly updates
        """)

st.divider()

# ==================== SECTION 2: PROGRESS TRACKER ====================
st.markdown('<div class="section-title">📊 Upload Progress Tracker</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    scraped_count = sum(1 for key in ['im_prices', 'comp_prices', 'necc_prices'] if key in st.session_state.uploaded_files)
    st.metric("📥 Scraped Data", f"{scraped_count}/3", delta="Complete" if scraped_count == 3 else "Pending")

with col2:
    compute_count = sum(1 for key in ['sales', 'stocks'] if key in st.session_state.uploaded_files)
    st.metric("🧮 Computation Data", f"{compute_count}/2", delta="Complete" if compute_count == 2 else "Pending")

with col3:
    static_count = sum(1 for key in ['cogs', 'sdpo', 'exclusion'] if key in st.session_state.uploaded_files)
    st.metric("⚙️ Static Data", f"{static_count}/3", delta="Complete" if static_count == 3 else "Pending")

with col4:
    st.metric("✅ Overall Status", f"{uploaded_count}/8", delta="READY TO RUN!" if is_ready else "Upload files")

# Progress bar
progress = uploaded_count / len(all_required_files)
st.progress(progress, text=f"Upload Progress: {uploaded_count} of {len(all_required_files)} files completed")

st.divider()

# ==================== SECTION 3: FILE UPLOADS ====================

# Scraped Data Inputs
st.markdown('<div class="upload-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📥 1. Scraped Data Inputs</div>', unsafe_allow_html=True)
st.caption("Upload pricing data from various market sources")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**IM Prices**")
    im_prices = st.file_uploader("Internal Market pricing data", type=['csv'], key="im_prices")
    if im_prices:
        st.session_state.uploaded_files['im_prices'] = pd.read_csv(im_prices)
        st.markdown(f'<div class="success-box">✅ Uploaded: {len(st.session_state.uploaded_files["im_prices"]):,} rows</div>', unsafe_allow_html=True)

with col2:
    st.markdown("**Competition Prices**")
    comp_prices = st.file_uploader("Competitor pricing data", type=['csv'], key="comp_prices")
    if comp_prices:
        st.session_state.uploaded_files['comp_prices'] = pd.read_csv(comp_prices)
        st.markdown(f'<div class="success-box">✅ Uploaded: {len(st.session_state.uploaded_files["comp_prices"]):,} rows</div>', unsafe_allow_html=True)

with col3:
    st.markdown("**NECC Prices**")
    necc_prices = st.file_uploader("National Egg Co-ordination Committee pricing", type=['csv'], key="necc_prices")
    if necc_prices:
        st.session_state.uploaded_files['necc_prices'] = pd.read_csv(necc_prices)
        st.markdown(f'<div class="success-box">✅ Uploaded: {len(st.session_state.uploaded_files["necc_prices"]):,} rows</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Computation Inputs
st.markdown('<div class="upload-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🧮 2. Computation Inputs</div>', unsafe_allow_html=True)
st.caption("Upload sales and inventory data for pricing calculations")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Sales Data**")
    st.caption("Historical sales information")
    sales_file = st.file_uploader("Upload Sales CSV", type=['csv'], key="sales")
    if sales_file:
        st.session_state.uploaded_files['sales'] = pd.read_csv(sales_file)
        st.markdown(f'<div class="success-box">✅ Uploaded: {len(st.session_state.uploaded_files["sales"]):,} rows</div>', unsafe_allow_html=True)

with col2:
    st.markdown("**Stocks Data** 📌")
    st.caption("Required columns: `product_id`, `stock_level`")
    stocks_file = st.file_uploader("Upload Stocks CSV", type=['csv'], key="stocks")
    if stocks_file:
        st.session_state.uploaded_files['stocks'] = pd.read_csv(stocks_file)
        st.markdown(f'<div class="success-box">✅ Uploaded: {len(st.session_state.uploaded_files["stocks"]):,} rows</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Static Inputs
st.markdown('<div class="upload-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">⚙️ 3. Static Inputs</div>', unsafe_allow_html=True)
st.caption("📅 Upload monthly or when changes occur")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**COGS Inputs** 📌")
    st.caption("Required: `product_id`, `product_name`, `cogs`")
    cogs_file = st.file_uploader("Upload COGS CSV", type=['csv'], key="cogs")
    if cogs_file:
        st.session_state.uploaded_files['cogs'] = pd.read_csv(cogs_file)
        st.markdown(f'<div class="success-box">✅ Uploaded: {len(st.session_state.uploaded_files["cogs"]):,} rows</div>', unsafe_allow_html=True)

with col2:
    st.markdown("**Brand Aligned SDPO**")
    st.caption("Discount by IM configuration")
    sdpo_file = st.file_uploader("Upload SDPO CSV", type=['csv'], key="sdpo")
    if sdpo_file:
        st.session_state.uploaded_files['sdpo'] = pd.read_csv(sdpo_file)
        st.markdown(f'<div class="success-box">✅ Uploaded: {len(st.session_state.uploaded_files["sdpo"]):,} rows</div>', unsafe_allow_html=True)

with col3:
    st.markdown("**City Brand Exclusion List**")
    st.caption("Excluded brands by city")
    exclusion_file = st.file_uploader("Upload Exclusion List CSV", type=['csv'], key="exclusion")
    if exclusion_file:
        st.session_state.uploaded_files['exclusion'] = pd.read_csv(exclusion_file)
        st.markdown(f'<div class="success-box">✅ Uploaded: {len(st.session_state.uploaded_files["exclusion"]):,} rows</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ==================== SECTION 4: RUN MODEL ====================
st.markdown('<div class="section-title">🚀 4. Generate Pricing Recommendations</div>', unsafe_allow_html=True)

if not is_ready:
    st.warning(f"⚠️ Please upload all {len(all_required_files)} files to enable the model. Currently uploaded: {uploaded_count}/{len(all_required_files)}")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    run_button = st.button(
        "🚀 RUN PRICING MODEL" if is_ready else "⏳ WAITING FOR FILES...",
        type="primary",
        use_container_width=True,
        disabled=not is_ready
    )

# Process when button is clicked
if run_button:
    try:
        cogs_df = st.session_state.uploaded_files['cogs']
        stocks_df = st.session_state.uploaded_files['stocks']
        
        # Validate required columns
        required_cogs_cols = ['product_id', 'product_name', 'cogs']
        required_stocks_cols = ['product_id', 'stock_level']
        
        if not all(col in cogs_df.columns for col in required_cogs_cols):
            st.error(f"❌ COGS file must contain columns: {', '.join(required_cogs_cols)}")
        elif not all(col in stocks_df.columns for col in required_stocks_cols):
            st.error(f"❌ Stocks file must contain columns: {', '.join(required_stocks_cols)}")
        else:
            # Run model
            with st.spinner("⏳ Running pricing model... Please wait"):
                results_df = run_pricing_model(cogs_df, stocks_df)
            
            st.divider()
            
            # Display success message
            st.success(f"✅ **Model Completed Successfully!** Generated pricing for {len(results_df):,} products", icon="🎉")
            
            # Show summary statistics
            st.markdown('<div class="section-title">📈 Pricing Summary</div>', unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Products", f"{len(results_df):,}")
            with col2:
                st.metric("Average Price", f"${results_df['recommended_price'].mean():.2f}")
            with col3:
                st.metric("Min Price", f"${results_df['recommended_price'].min():.2f}")
            with col4:
                st.metric("Max Price", f"${results_df['recommended_price'].max():.2f}")
            
            st.markdown("")
            
            # Display results table
            st.markdown('<div class="section-title">📋 Detailed Pricing Recommendations</div>', unsafe_allow_html=True)
            st.dataframe(results_df, use_container_width=True, height=400)
            
            st.markdown("")
            
            # Download button
            csv = results_df.to_csv(index=False)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.download_button(
                    label="⬇️ DOWNLOAD PRICING RECOMMENDATIONS (CSV)",
                    data=csv,
                    file_name="pricing_recommendations.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary"
                )
    
    except Exception as e:
        st.error(f"❌ **Error:** {str(e)}")
        st.info("Please check your file formats and column names, then try again.")

# Footer
st.divider()
st.caption("💡 Need help? Expand the 'How to Use This Tool' section at the top of the page")
