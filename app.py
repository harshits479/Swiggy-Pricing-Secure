# app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pricing_engine as engine  # Import the logic file we just made

# Page Config
st.set_page_config(page_title="Swiggy Pricing Commander", page_icon="🥚", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .main-header { font-size: 2rem; font-weight: 700; color: #fc8019; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🥚 Swiggy Instamart: Egg Pricing Commander</div>', unsafe_allow_html=True)

# ==========================================
# 1. SIDEBAR INPUTS
# ==========================================
st.sidebar.header("1. Upload Inputs")
cogs_file = st.sidebar.file_uploader("Upload COGS (cogs.csv)", type="csv")
sdpo_file = st.sidebar.file_uploader("Upload SDPO (brand_aligned_sdpo.csv)", type="csv")

st.sidebar.header("2. Configuration")
nm_target = st.sidebar.slider("Net Margin Target (%)", 0, 50, 15)
simulation_day = st.sidebar.selectbox("Simulation Day (for Sensitivity)", 
                                      ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])

# ==========================================
# 2. DATA LOADING (Google Drive / Local Simulation)
# ==========================================
@st.cache_data
def load_static_data():
    # In a real deployed app, these would be in a 'data/' folder in GitHub
    # For this demo, we check if they exist, otherwise warn user
    folder = "data" # Or root
    try:
        inputs = {
            "im_pricing": pd.read_csv("im_pricing.csv"),
            "comp_pricing": pd.read_csv("competion_pricing.csv"),
            "necc": pd.read_csv("necc_egg_prices_cleaned.csv"),
            "gmv_weights": pd.read_csv("gmv_weights.csv"),
            "stock": pd.read_csv("stock_insights.csv"),
            "exclusion": pd.read_csv("city_brand_exclusion_list.csv"),
            "city_map": pd.read_csv("city_id_mapping.csv"),
            "spin_map": pd.read_csv("spin_id_mapping.csv"),
            "sensitivity": pd.read_csv("price_sensitivity.csv")
        }
        return inputs
    except FileNotFoundError as e:
        st.error(f"❌ Missing File: {e.filename}. Please ensure all static files are in the directory.")
        return None

static_data = load_static_data()

# ==========================================
# 3. RUN MODEL
# ==========================================
if st.button("🚀 Run Pricing Model", type="primary"):
    if static_data and cogs_file and sdpo_file:
        with st.spinner("Crunching numbers... this involves UOM normalization, Matching, and Elasticity checks..."):
            
            # 0. Load Uploads
            cogs_df = pd.read_csv(cogs_file)
            sdpo_df = pd.read_csv(sdpo_file)
            
            # 1. Normalization
            im_norm = engine.normalize_im_data(static_data["im_pricing"])
            comp_norm = engine.normalize_comp_data(static_data["comp_pricing"])
            
            # 2. Matching
            matched_df = engine.run_matching_engine(im_norm, comp_norm)
            
            # 3. Pricing Engine
            pricing_results = engine.run_pricing_engine(
                matched_df, 
                cogs_df, 
                static_data["necc"], 
                static_data["exclusion"], 
                static_data["stock"],
                nm_target
            )
            
            # 4. Performance & GMV Goodness
            final_report = engine.calculate_gmv_goodness(
                pricing_results, 
                static_data["sensitivity"], 
                static_data["gmv_weights"],
                simulation_day
            )
            
            # 5. Generate Upload Files
            upload_file = engine.generate_upload_files(
                final_report, 
                static_data["city_map"], 
                static_data["spin_map"]
            )
            
            st.session_state['results'] = final_report
            st.session_state['upload'] = upload_file
            st.success("✅ Model Run Complete!")
            
    else:
        st.warning("Please upload COGS and SDPO files to proceed.")

# ==========================================
# 4. DISPLAY RESULTS
# ==========================================
if 'results' in st.session_state:
    df = st.session_state['results']
    
    # KPIS
    col1, col2, col3, col4 = st.columns(4)
    avg_nm = df['Projected_Margin'].mean() * 100
    total_goodness = df['GMV_Goodness'].sum()
    price_hikes = len(df[df['Pct_Price_Change'] > 0])
    price_drops = len(df[df['Pct_Price_Change'] < 0])
    
    col1.metric("Avg Net Margin", f"{avg_nm:.1f}%", help="Target vs Actual")
    col2.metric("GMV Goodness (Daily)", f"₹{total_goodness:,.0f}", 
                delta_color="normal" if total_goodness > 0 else "inverse")
    col3.metric("Price Hikes", price_hikes)
    col4.metric("Price Drops", price_drops)
    
    # Detailed Table
    st.subheader("🔍 Detailed Pricing Recommendations")
    
    # Formatting for display
    display_cols = ['City', 'ITEM_NAME', 'Current_Price', 'Recommended_Price', 
                    'Elasticity', 'GMV_Goodness', 'Projected_Margin']
    
    # Color Highlighting for Goodness
    def highlight_goodness(val):
        color = 'green' if val > 0 else 'red' if val < 0 else 'black'
        return f'color: {color}'
    
    st.dataframe(
        df[display_cols].style.format({
            'Current_Price': '₹{:.2f}', 
            'Recommended_Price': '₹{:.2f}',
            'GMV_Goodness': '₹{:,.2f}',
            'Projected_Margin': '{:.1%}',
            'Elasticity': '{:.2f}'
        }).applymap(highlight_goodness, subset=['GMV_Goodness']),
        use_container_width=True
    )
    
    # Downloads
    st.subheader("📥 Downloads")
    c1, c2 = st.columns(2)
    csv = st.session_state['upload'].to_csv(index=False).encode('utf-8')
    c1.download_button("Download Price Upload File", data=csv, file_name="final_upload_prices.csv", mime="text/csv")
    
    full_csv = df.to_csv(index=False).encode('utf-8')
    c2.download_button("Download Full Report", data=full_csv, file_name="pricing_performance_report.csv", mime="text/csv")
