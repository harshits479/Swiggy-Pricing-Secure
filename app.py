# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model

# Page config
st.set_page_config(page_title="Pricing Model", page_icon="💰", layout="wide")

# Custom CSS for better styling
st.markdown("""
    <style>
    .upload-section {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .stButton>button {
        height: 3rem;
        font-size: 1.1rem;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    .section-header {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #0e1117;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 Pricing Model")

# Initialize session state for file uploads
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

# Top status bar and run button
col_status1, col_status2, col_button = st.columns([1, 1, 2])

with col_status1:
    st.metric("Files Uploaded", f"{uploaded_count}/{len(all_required_files)}")

with col_status2:
    st.metric("Status", "✅ Ready" if is_ready else "⏳ Pending")

with col_button:
    run_button = st.button("🚀 Run Pricing Model", type="primary", use_container_width=True, disabled=not is_ready)

st.divider()

# Compact file upload sections
st.markdown('<div class="section-header">📥 Scraped Data Inputs</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)

with col1:
    st.caption("**IM Prices**")
    im_prices = st.file_uploader("Upload CSV", type=['csv'], key="im_prices", label_visibility="collapsed")
    if im_prices:
        st.session_state.uploaded_files['im_prices'] = pd.read_csv(im_prices)
        st.success(f"✓ {len(st.session_state.uploaded_files['im_prices'])} rows", icon="✅")

with col2:
    st.caption("**Competition Prices**")
    comp_prices = st.file_uploader("Upload CSV", type=['csv'], key="comp_prices", label_visibility="collapsed")
    if comp_prices:
        st.session_state.uploaded_files['comp_prices'] = pd.read_csv(comp_prices)
        st.success(f"✓ {len(st.session_state.uploaded_files['comp_prices'])} rows", icon="✅")

with col3:
    st.caption("**NECC Prices**")
    necc_prices = st.file_uploader("Upload CSV", type=['csv'], key="necc_prices", label_visibility="collapsed")
    if necc_prices:
        st.session_state.uploaded_files['necc_prices'] = pd.read_csv(necc_prices)
        st.success(f"✓ {len(st.session_state.uploaded_files['necc_prices'])} rows", icon="✅")

st.divider()

st.markdown('<div class="section-header">🧮 Computation Inputs</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    st.caption("**Sales Data**")
    sales_file = st.file_uploader("Upload CSV", type=['csv'], key="sales", label_visibility="collapsed")
    if sales_file:
        st.session_state.uploaded_files['sales'] = pd.read_csv(sales_file)
        st.success(f"✓ {len(st.session_state.uploaded_files['sales'])} rows", icon="✅")

with col2:
    st.caption("**Stocks Data**")
    st.caption("_Required: product_id, stock_level_")
    stocks_file = st.file_uploader("Upload CSV", type=['csv'], key="stocks", label_visibility="collapsed")
    if stocks_file:
        st.session_state.uploaded_files['stocks'] = pd.read_csv(stocks_file)
        st.success(f"✓ {len(st.session_state.uploaded_files['stocks'])} rows", icon="✅")

st.divider()

st.markdown('<div class="section-header">⚙️ Static Inputs</div>', unsafe_allow_html=True)
st.caption("_Upload monthly or when changes occur_")
col1, col2, col3 = st.columns(3)

with col1:
    st.caption("**COGS Inputs**")
    st.caption("_Required: product_id, product_name, cogs_")
    cogs_file = st.file_uploader("Upload CSV", type=['csv'], key="cogs", label_visibility="collapsed")
    if cogs_file:
        st.session_state.uploaded_files['cogs'] = pd.read_csv(cogs_file)
        st.success(f"✓ {len(st.session_state.uploaded_files['cogs'])} rows", icon="✅")

with col2:
    st.caption("**Brand Aligned SDPO**")
    st.caption("_Discount by IM_")
    sdpo_file = st.file_uploader("Upload CSV", type=['csv'], key="sdpo", label_visibility="collapsed")
    if sdpo_file:
        st.session_state.uploaded_files['sdpo'] = pd.read_csv(sdpo_file)
        st.success(f"✓ {len(st.session_state.uploaded_files['sdpo'])} rows", icon="✅")

with col3:
    st.caption("**City Brand Exclusion List**")
    exclusion_file = st.file_uploader("Upload CSV", type=['csv'], key="exclusion", label_visibility="collapsed")
    if exclusion_file:
        st.session_state.uploaded_files['exclusion'] = pd.read_csv(exclusion_file)
        st.success(f"✓ {len(st.session_state.uploaded_files['exclusion'])} rows", icon="✅")

st.divider()

# Process when button is clicked
if run_button:
    if not is_ready:
        st.error(f"⚠️ Please upload all {len(all_required_files)} required files before running the model")
    else:
        try:
            cogs_df = st.session_state.uploaded_files['cogs']
            stocks_df = st.session_state.uploaded_files['stocks']
            
            # Validate required columns
            required_cogs_cols = ['product_id', 'product_name', 'cogs']
            required_stocks_cols = ['product_id', 'stock_level']
            
            if not all(col in cogs_df.columns for col in required_cogs_cols):
                st.error(f"❌ COGS file must contain columns: {required_cogs_cols}")
            elif not all(col in stocks_df.columns for col in required_stocks_cols):
                st.error(f"❌ Stocks file must contain columns: {required_stocks_cols}")
            else:
                # Run model
                with st.spinner("Running pricing model..."):
                    results_df = run_pricing_model(cogs_df, stocks_df)
                
                # Display success message
                st.success(f"✅ Model completed! Generated pricing for {len(results_df)} products")
                
                # Show summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Price", f"${results_df['recommended_price'].mean():.2f}")
                with col2:
                    st.metric("Min Price", f"${results_df['recommended_price'].min():.2f}")
                with col3:
                    st.metric("Max Price", f"${results_df['recommended_price'].max():.2f}")
                
                # Display results table
                st.subheader("📋 Pricing Recommendations")
                st.dataframe(results_df, use_container_width=True, height=400)
                
                # Download button
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download Results CSV",
                    data=csv,
                    file_name="pricing_recommendations.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        except Exception as e:
            st.error(f"❌ Error processing files: {str(e)}")

# Footer with instructions
with st.expander("ℹ️ How to use this tool"):
    st.markdown("""
    ### Quick Start:
    1. Upload all 8 required CSV files in their respective sections
    2. Wait for status to show "✅ Ready" 
    3. Click "🚀 Run Pricing Model" button at the top
    4. Download your pricing recommendations
    
    ### File Requirements:
    
    **Scraped Data Inputs:**
    - IM Prices, Competition Prices, NECC Prices
    
    **Computation Inputs:**
    - Sales Data
    - Stocks Data (columns: `product_id`, `stock_level`)
    
    **Static Inputs (Monthly):**
    - COGS Inputs (columns: `product_id`, `product_name`, `cogs`)
    - Brand Aligned SDPO
    - City Brand Exclusion List
    
    ### Pricing Logic:
    - Low stock (< 50): 40% markup
    - Medium stock (50-200): 30% markup  
    - High stock (> 200): 20% markup
    """)
