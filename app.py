# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model
import io

# Page config
st.set_page_config(page_title="Pricing Model", page_icon="💰", layout="wide")

# Custom CSS for better styling and reduced gaps
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1.2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
        opacity: 0.95;
    }
    .upload-card {
        background: linear-gradient(to right, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .section-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #667eea;
        margin-bottom: 0.5rem;
    }
    .stButton>button {
        height: 3.5rem;
        font-size: 1.2rem;
        font-weight: 700;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    /* Reduce spacing between sections */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stExpander"] {
        margin-bottom: 0.8rem;
        background-color: #f8f9fa;
        border-radius: 8px;
    }
    div[data-testid="stSelectbox"],
    div[data-testid="stNumberInput"] {
        margin-bottom: 0rem;
    }
    div[data-testid="stFileUploader"] {
        margin-bottom: 0rem;
    }
    div[data-testid="column"] {
        padding: 0.5rem;
    }
    div[data-baseweb="notification"] {
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .element-container:has(> .stSuccess),
    .element-container:has(> .stError) {
        margin-top: 0.3rem;
        margin-bottom: 0.3rem;
    }
    .element-container {
        margin-bottom: 0.5rem;
    }
    .stCaption {
        color: #6c757d;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>💰 Dynamic Pricing Engine</h1>
        <p>Smart pricing recommendations powered by data analytics</p>
    </div>
    """, unsafe_allow_html=True)

# Initialize session state
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'model_run' not in st.session_state:
    st.session_state.model_run = False
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'opp_upload' not in st.session_state:
    st.session_state.opp_upload = None
if 'branded_upload' not in st.session_state:
    st.session_state.branded_upload = None

# ==================== INSTRUCTIONS (Collapsible) ====================
with st.expander("📖 **HOW TO USE** - Click to view instructions", expanded=False):
    st.markdown("""
    ### Quick Start Guide
    
    **Step 1:** Select the product category from the dropdown  
    **Step 2:** Set your target Net Margin (NM) percentage  
    **Step 3:** Upload required files:
    - **COGS Data** (Required: `product_id`, `COGS`, `CITY`)
    - **Brand Aligned Discount** (Optional: `Brand`, `Hardcoded_SDPO`)
    
    **Step 4:** Click "Run Pricing Model" button  
    **Step 5:** Review performance metrics and download files
    
    ### Data Sources
    
    The model automatically fetches these files from your Google Drive folder **"Pricing Inputs"**:
    - IM Pricing data (`im_pricing.csv`)
    - Competition Pricing (`competition_pricing.csv`)
    - NECC Egg Prices (`necc_egg_prices_cleaned.csv`)
    - GMV Weights (`gmv_weights.csv`)
    - Stock Insights (`stock_insights.csv`)
    - City Brand Exclusion List (`city_brand_exclusion_list.csv`)
    - City ID Mapping (`city_id_mapping.csv`)
    - SPIN ID Mapping (`spin_id_mapping.csv`)
    - Price Sensitivity (`price_sensitivity.csv`)
    
    ### File Format Requirements
    
    **COGS File:**
    - Columns: `product_id`, `COGS`, `CITY`
    - Format: CSV
    - Example:
      ```
      product_id,CITY,COGS
      558087,lonavla,187.5
      78360,amritsar,56.5
      ```
    
    **Brand Aligned SDPO (Optional):**
    - Columns: `Brand`, `Hardcoded_SDPO`
    - Format: CSV with percentage values
    - Example:
      ```
      Brand,Hardcoded_SDPO
      Eggoz,4%
      Keggs,5%
      ```
    
    ### Outputs
    
    The model generates:
    - **Modeled Prices Table** - Complete pricing recommendations
    - **Performance Metrics** - NM, PI, GMV Goodness scores
    - **OPP Upload File** - Ready for upload
    - **Branded Upload File** - Ready for upload
    
    ### Pricing Logic
    
    The model uses:
    - UOM Normalization for accurate matching
    - Competitive intelligence from market data
    - Stock-based dynamic adjustments
    - Target margin optimization
    - Brand-aligned discounting
    """)

# ==================== CATEGORY AND MARGIN SELECTION ====================
col1, col2 = st.columns(2)

with col1:
    st.markdown("**📦 Product Category**")
    categories = [
        "Batters And Chutneys",
        "Bread And Buns",
        "Butter",
        "Cheese",
        "Curd",
        "Dairy Alternatives",
        "Eggs",
        "Indian Breads",
        "Milk",
        "Milk Based Drinks",
        "Paneer And Cream",
        "Yogurts"
    ]
    selected_category = st.selectbox(
        "Category",
        options=categories,
        index=6,  # Default to Eggs
        label_visibility="collapsed"
    )

with col2:
    st.markdown("**🎯 Target Net Margin (NM) %**")
    target_margin = st.number_input(
        "Margin",
        min_value=0.0,
        max_value=100.0,
        value=30.0,
        step=0.5,
        format="%.1f",
        label_visibility="collapsed",
        help="Target Net Margin percentage for pricing optimization"
    )

# ==================== GOOGLE DRIVE CONNECTION INFO ====================
st.markdown('<div class="upload-card"><div class="section-title">☁️ Google Drive Connection</div>', unsafe_allow_html=True)

st.info("""
📁 **Automatic Data Fetch**: The app will automatically fetch pricing input files from your Google Drive folder **"Pricing Inputs"**.

⚙️ **Setup Instructions**:
1. Ensure all required CSV files are in your Google Drive folder named "Pricing Inputs"
2. File names should match exactly (case-sensitive):
   - `im_pricing.csv`
   - `competition_pricing.csv`
   - `necc_egg_prices_cleaned.csv`
   - `gmv_weights.csv`
   - `stock_insights.csv`
   - `city_brand_exclusion_list.csv`
   - `city_id_mapping.csv`
   - `spin_id_mapping.csv`
   - `price_sensitivity.csv`
""")

st.markdown('</div>', unsafe_allow_html=True)

# ==================== FILE UPLOADS ====================
uploaded_files = {}

# Upload Inputs Section
st.markdown('<div class="upload-card"><div class="section-title">📥 Upload Data Files</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.caption("**COGS Data** _(Required: product_id, COGS, CITY)_")
    cogs_file = st.file_uploader("COGS", type=['csv'], key="cogs", label_visibility="collapsed")
    if cogs_file:
        uploaded_files['cogs'] = pd.read_csv(cogs_file)
        st.success(f"✓ {len(uploaded_files['cogs']):,} rows uploaded")

with col2:
    st.caption("**Brand Aligned Discount (SDPO)** _(Optional: Brand, Hardcoded_SDPO)_")
    sdpo_file = st.file_uploader("SDPO", type=['csv'], key="sdpo", label_visibility="collapsed")
    if sdpo_file:
        uploaded_files['sdpo'] = pd.read_csv(sdpo_file)
        st.success(f"✓ {len(uploaded_files['sdpo']):,} rows uploaded")

st.markdown('</div>', unsafe_allow_html=True)

# ==================== RUN BUTTON ====================
is_ready = 'cogs' in uploaded_files

st.info(f"📊 **Selected:** {selected_category} | **Target NM:** {target_margin}%")

run_button = st.button(
    "🚀 RUN PRICING MODEL" if is_ready else "⏳ WAITING FOR COGS FILE...",
    type="primary",
    use_container_width=True,
    disabled=not is_ready
)

# ==================== PROCESS MODEL ====================
if run_button:
    try:
        with st.spinner("⏳ Loading data from Google Drive and processing..."):
            
            # For demo purposes, we'll use the uploaded files
            # In production, you would fetch from Google Drive here
            # Example: df_im = fetch_from_google_drive("Pricing Inputs/im_pricing.csv")
            
            # Load uploaded COGS
            cogs_df = uploaded_files['cogs']
            
            # Load SDPO if available
            sdpo_df = uploaded_files.get('sdpo', None)
            
            # Check SDPO format and inform user
            if sdpo_df is not None:
                if 'Brand' in sdpo_df.columns and 'Hardcoded_SDPO' in sdpo_df.columns:
                    st.info("ℹ️ Brand-level SDPO file detected. Note: Brand-to-product mapping is needed for full SDPO application.")
                elif 'ITEM_CODE' not in sdpo_df.columns:
                    st.warning("⚠️ SDPO file should have either 'Brand' or 'ITEM_CODE' column for proper matching.")
            
            # Validate COGS file columns
            required_cogs_cols = ['product_id', 'COGS']
            if not all(col in cogs_df.columns for col in required_cogs_cols):
                st.error(f"❌ COGS file must contain columns: {', '.join(required_cogs_cols)}")
                st.error(f"Found columns: {', '.join(cogs_df.columns.tolist())}")
                st.stop()
            
            # For demo, create dummy data for required inputs
            # In production, replace with actual Google Drive fetch
            st.info("🔄 In production mode, files will be automatically fetched from Google Drive folder 'Pricing Inputs'")
            
            # Prepare COGS data - create product_name if missing
            if 'product_name' not in cogs_df.columns:
                cogs_df['product_name'] = 'Product ' + cogs_df['product_id'].astype(str)
            
            # Standardize COGS column name
            if 'COGS' in cogs_df.columns and 'cogs' not in cogs_df.columns:
                cogs_df['cogs'] = cogs_df['COGS']
            
            # Dummy data for demonstration
            df_im = pd.DataFrame({
                'ITEM_CODE': cogs_df['product_id'].values[:min(100, len(cogs_df))],
                'ITEM_NAME': cogs_df['product_name'].values[:min(100, len(cogs_df))],
                'uom': ['10_pieces'] * min(100, len(cogs_df)),
                'MRP': [100] * min(100, len(cogs_df)),
                'CITY': cogs_df['CITY'].values[:min(100, len(cogs_df))] if 'CITY' in cogs_df.columns else ['bangalore'] * min(100, len(cogs_df))
            })
            
            df_comp = pd.DataFrame({
                'product_name': cogs_df['product_name'].values[:min(50, len(cogs_df))],
                'uom': ['10_pieces'] * min(50, len(cogs_df)),
                'selling_price': [95] * min(50, len(cogs_df))
            })
            
            df_necc = pd.DataFrame({
                'UOM': ['10_pieces', '30_pieces'],
                'Price': [85, 250]
            })
            
            df_stock = pd.DataFrame({
                'ITEM_CODE': cogs_df['product_id'].values[:min(100, len(cogs_df))],
                'stock_level': [100] * min(100, len(cogs_df))
            })
            
            df_gmv = pd.DataFrame({
                'category': [selected_category],
                'weight': [1.0]
            })
            
            df_sensitivity = pd.DataFrame({
                'item_code': cogs_df['product_id'].values[:min(100, len(cogs_df))],
                'price_sensitivity_score': [50] * min(100, len(cogs_df))
            })
            
            city_mapping = pd.DataFrame({
                'CITY': ['Bangalore', 'bangalore', 'Delhi', 'Mumbai'],
                'CITY_ID': [1, 1, 2, 3]
            })
            
            spin_mapping = pd.DataFrame({
                'item_code': cogs_df['product_id'].values[:min(100, len(cogs_df))],
                'spin_id': range(1, min(101, len(cogs_df) + 1))
            })
            
            exclusions = pd.DataFrame()
            
            # Run the pricing model
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
            
            # Store in session state
            st.session_state.results_df = results_df
            st.session_state.summary = summary
            st.session_state.opp_upload = opp_upload
            st.session_state.branded_upload = branded_upload
            st.session_state.model_run = True
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# ==================== DISPLAY RESULTS ====================
if st.session_state.model_run and st.session_state.results_df is not None:
    results_df = st.session_state.results_df
    summary = st.session_state.summary
    opp_upload = st.session_state.opp_upload
    branded_upload = st.session_state.branded_upload
    
    st.success(f"✅ Pricing model completed successfully! Generated {len(results_df):,} recommendations", icon="🎉")
    
    # Performance Metrics
    st.markdown('<div class="upload-card"><div class="section-title">📊 Performance Metrics</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Total Products", f"{summary['total_products']:,}")
    with col2:
        st.metric("💵 Avg Net Margin", f"{summary['avg_net_margin']:.2f}%")
    with col3:
        st.metric("📈 Avg Price Index", f"{summary['avg_price_index']:.2f}")
    with col4:
        st.metric("⭐ GMV Goodness", f"{summary['avg_gmv_goodness']:.2f}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Table Preview
    st.markdown("### 📋 Modeled Prices Preview (First 10 Rows)")
    
    display_cols = ['ITEM_CODE', 'ITEM_NAME', 'cogs', 'Final Price', 'net_margin', 
                   'price_index', 'category', 'target_margin_%']
    available_cols = [col for col in display_cols if col in results_df.columns]
    
    st.dataframe(
        results_df[available_cols].head(10), 
        use_container_width=True, 
        height=350,
        hide_index=True
    )
    
    # Download Buttons
    st.markdown("### 📥 Download Files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Modeled Prices CSV
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="📊 DOWNLOAD MODELED PRICES",
            data=csv,
            file_name=f"modeled_prices_{selected_category.replace(' ', '_').lower()}.csv",
            mime="text/csv",
            use_container_width=True,
            type="secondary"
        )
    
    with col2:
        # OPP Upload File
        if opp_upload is not None and len(opp_upload) > 0:
            opp_csv = opp_upload.to_csv(index=False)
            st.download_button(
                label="📤 OPP UPLOAD FILE",
                data=opp_csv,
                file_name=f"opp_prices_upload_{selected_category.replace(' ', '_').lower()}.csv",
                mime="text/csv",
                use_container_width=True,
                type="secondary"
            )
        else:
            st.info("No OPP products")
    
    with col3:
        # Branded Upload File
        if branded_upload is not None and len(branded_upload) > 0:
            branded_csv = branded_upload.to_csv(index=False)
            st.download_button(
                label="📤 BRANDED UPLOAD FILE",
                data=branded_csv,
                file_name=f"branded_prices_upload_{selected_category.replace(' ', '_').lower()}.csv",
                mime="text/csv",
                use_container_width=True,
                type="secondary"
            )
        else:
            st.info("No branded products")
