# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model

# Page config
st.set_page_config(page_title="Pricing Model", page_icon="💰", layout="wide")
st.title("💰 Pricing Model")
st.write("Upload your data files to get pricing recommendations")

# Create tabs for better organization
tab1, tab2, tab3 = st.tabs([
    "📥 Scraped Data Inputs", 
    "🧮 Computation Inputs", 
    "⚙️ Static Inputs"
])

# Initialize session state for file uploads
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}

# TAB 1: Scraped Data Inputs
with tab1:
    st.header("📥 Scraped Data Inputs")
    st.write("Upload price data from various sources")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("IM Prices")
        st.write("Internal Market pricing data")
        im_prices = st.file_uploader("Upload IM Prices CSV", type=['csv'], key="im_prices")
        if im_prices:
            st.session_state.uploaded_files['im_prices'] = pd.read_csv(im_prices)
            st.success(f"✓ Uploaded ({len(st.session_state.uploaded_files['im_prices'])} rows)")
    
    with col2:
        st.subheader("Competition Prices")
        st.write("Competitor pricing data")
        comp_prices = st.file_uploader("Upload Competition Prices CSV", type=['csv'], key="comp_prices")
        if comp_prices:
            st.session_state.uploaded_files['comp_prices'] = pd.read_csv(comp_prices)
            st.success(f"✓ Uploaded ({len(st.session_state.uploaded_files['comp_prices'])} rows)")
    
    with col3:
        st.subheader("NECC Prices")
        st.write("National Egg Co-ordination Committee pricing")
        necc_prices = st.file_uploader("Upload NECC Prices CSV", type=['csv'], key="necc_prices")
        if necc_prices:
            st.session_state.uploaded_files['necc_prices'] = pd.read_csv(necc_prices)
            st.success(f"✓ Uploaded ({len(st.session_state.uploaded_files['necc_prices'])} rows)")

# TAB 2: Computation Inputs
with tab2:
    st.header("🧮 Computation Inputs")
    st.write("Upload sales and inventory data for model computation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Sales Data")
        st.write("Historical sales information")
        sales_file = st.file_uploader("Upload Sales CSV", type=['csv'], key="sales")
        if sales_file:
            st.session_state.uploaded_files['sales'] = pd.read_csv(sales_file)
            st.success(f"✓ Uploaded ({len(st.session_state.uploaded_files['sales'])} rows)")
    
    with col2:
        st.subheader("📦 Stocks Data")
        st.write("Required columns: `product_id`, `stock_level`")
        stocks_file = st.file_uploader("Upload Stocks CSV", type=['csv'], key="stocks")
        if stocks_file:
            st.session_state.uploaded_files['stocks'] = pd.read_csv(stocks_file)
            st.success(f"✓ Uploaded ({len(st.session_state.uploaded_files['stocks'])} rows)")

# TAB 3: Static Inputs
with tab3:
    st.header("⚙️ Static Inputs")
    st.info("💡 These files typically need to be uploaded once a month or when changes occur")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("💵 COGS Inputs")
        st.write("Required columns: `product_id`, `product_name`, `cogs`")
        cogs_file = st.file_uploader("Upload COGS CSV", type=['csv'], key="cogs")
        if cogs_file:
            st.session_state.uploaded_files['cogs'] = pd.read_csv(cogs_file)
            st.success(f"✓ Uploaded ({len(st.session_state.uploaded_files['cogs'])} rows)")
    
    with col2:
        st.subheader("🎯 Brand Aligned SDPO")
        st.write("Discount by IM configuration")
        sdpo_file = st.file_uploader("Upload SDPO CSV", type=['csv'], key="sdpo")
        if sdpo_file:
            st.session_state.uploaded_files['sdpo'] = pd.read_csv(sdpo_file)
            st.success(f"✓ Uploaded ({len(st.session_state.uploaded_files['sdpo'])} rows)")
    
    with col3:
        st.subheader("🚫 City Brand Exclusion List")
        st.write("Excluded brands by city")
        exclusion_file = st.file_uploader("Upload Exclusion List CSV", type=['csv'], key="exclusion")
        if exclusion_file:
            st.session_state.uploaded_files['exclusion'] = pd.read_csv(exclusion_file)
            st.success(f"✓ Uploaded ({len(st.session_state.uploaded_files['exclusion'])} rows)")

# Main action area
st.divider()

# Upload status overview
st.subheader("📋 Upload Status")

# Define all required files (all 8 files are required)
all_required_files = [
    'im_prices', 'comp_prices', 'necc_prices',  # Scraped Data
    'sales', 'stocks',  # Computation Inputs
    'cogs', 'sdpo', 'exclusion'  # Static Inputs
]

uploaded_count = sum(1 for key in all_required_files if key in st.session_state.uploaded_files)
is_ready = uploaded_count == len(all_required_files)

status_cols = st.columns(2)

with status_cols[0]:
    st.metric("Total Files Uploaded", f"{uploaded_count}/{len(all_required_files)}")

with status_cols[1]:
    st.metric("Status", "✅ Ready" if is_ready else "⏳ Pending")

st.divider()

# Run button
if st.button("🚀 Run Pricing Model", type="primary", use_container_width=True, disabled=not is_ready):
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

# Add footer with instructions
st.divider()
with st.expander("ℹ️ How to use this tool"):
    st.markdown("""
    ### Instructions:
    
    #### 1. **Scraped Data Inputs** (Required)
    - **IM Prices**: Internal market pricing data
    - **Competition Prices**: Competitor pricing information
    - **NECC Prices**: National Egg Co-ordination Committee pricing
    
    #### 2. **Computation Inputs** (Required)
    - **Sales Data**: Historical sales information
    - **Stocks Data**: Current inventory levels (columns: `product_id`, `stock_level`)
    
    #### 3. **Static Inputs** (Required - Upload Monthly)
    - **COGS Inputs**: Cost of goods sold (columns: `product_id`, `product_name`, `cogs`)
    - **Brand Aligned SDPO**: Discount configuration by IM
    - **City Brand Exclusion List**: Brands excluded by city
    
    #### 4. Run the Model
    - Upload all 8 required files across the three tabs
    - The "Run Pricing Model" button will be enabled once all files are uploaded
    - Click to generate recommendations
    - Download the results as CSV
    
    ### Pricing Logic:
    - **Low stock** (< 50 units): 40% markup
    - **Medium stock** (50-200 units): 30% markup
    - **High stock** (> 200 units): 20% markup
    """)
