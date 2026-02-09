# app.py
import streamlit as st
import pandas as pd
from pricing_model_complete import run_complete_pricing_model
from google_drive_integration import GoogleDriveLoader
import io
import tempfile
import os

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
if 'gdrive_authenticated' not in st.session_state:
    st.session_state.gdrive_authenticated = False
if 'gdrive_loader' not in st.session_state:
    st.session_state.gdrive_loader = None

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
    - IM Pricing data (`{category}_im_pricing.csv`)
    - Competition Pricing (`{category}_pricing_comp.csv`)
    - NECC Egg Prices (`necc_egg_prices_cleaned.csv`)
    - GMV Weights (`gmv_weights.csv`)
    - Stock Insights (`stock_insights.csv`)
    - City Brand Exclusion List (`city_brand_exclusion_list.csv`)
    
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

# ==================== GOOGLE DRIVE CONNECTION ====================
st.markdown('<div class="upload-card"><div class="section-title">☁️ Google Drive Connection</div>', unsafe_allow_html=True)

# Initialize Google Drive Loader
if st.session_state.gdrive_loader is None:
    st.session_state.gdrive_loader = GoogleDriveLoader()
    
# Authenticate
if not st.session_state.gdrive_authenticated:
    with st.spinner("🔐 Authenticating with Google Drive..."):
        if st.session_state.gdrive_loader.authenticate():
            st.session_state.gdrive_authenticated = True
            st.success("✅ Connected to Google Drive successfully!")
        else:
            st.warning("⚠️ Google Drive not configured. Please upload files manually below.")

if st.session_state.gdrive_authenticated:
    st.info("""
    📁 **Connected to Google Drive**: The app will fetch pricing input files from your **"Pricing Inputs"** folder.
    
    **Required files in Google Drive:**
    - `{category}_im_pricing.csv` (e.g., `eggs_im_pricing.csv`)
    - `{category}_pricing_comp.csv` (e.g., `eggs_pricing_comp.csv`)
    - `necc_egg_prices_cleaned.csv`
    - `gmv_weights.csv`
    - `stock_insights.csv`
    - `city_brand_exclusion_list.csv`
    """)
else:
    st.info("""
    📁 **Manual Upload Mode**: Upload all required files below.
    
    To enable Google Drive auto-fetch, add your service account credentials to Streamlit secrets.
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

if st.session_state.gdrive_authenticated:
    st.info(f"📊 **Selected:** {selected_category} | **Target NM:** {target_margin}% | **Source:** Google Drive")
else:
    st.info(f"📊 **Selected:** {selected_category} | **Target NM:** {target_margin}% | **Source:** Manual Upload")

run_button = st.button(
    "🚀 RUN PRICING MODEL" if is_ready else "⏳ WAITING FOR COGS FILE...",
    type="primary",
    use_container_width=True,
    disabled=not is_ready
)

# ==================== PROCESS MODEL ====================
if run_button:
    try:
        with st.spinner("⏳ Loading data and processing..."):
            
            # Create temporary directory for all files
            with tempfile.TemporaryDirectory() as tmpdir:
                
                # Prepare file paths dictionary
                file_paths = {}
                
                # Category-specific file names
                category_slug = selected_category.lower().replace(' ', '_')
                
                # Define required files from Google Drive
                gdrive_files = {
                    'im_pricing': f'{category_slug}_im_pricing.csv',
                    'comp_pricing': f'{category_slug}_pricing_comp.csv',
                    'necc_pricing': 'necc_egg_prices_cleaned.csv',
                    'stock': 'stock_insights.csv',
                    'gmv': 'gmv_weights.csv',
                    'exclusion': 'city_brand_exclusion_list.csv'
                }
                
                # Fetch files from Google Drive if authenticated
                if st.session_state.gdrive_authenticated:
                    st.write("📥 Fetching files from Google Drive...")
                    
                    folder_name = "Pricing Inputs"
                    
                    for key, filename in gdrive_files.items():
                        try:
                            st.write(f"   Downloading {filename}...")
                            df = st.session_state.gdrive_loader.load_file_by_name(folder_name, filename)
                            
                            if df is not None and not df.empty:
                                # Save to temp directory
                                temp_path = os.path.join(tmpdir, filename)
                                df.to_csv(temp_path, index=False)
                                file_paths[key] = temp_path
                                st.success(f"   ✓ {filename} loaded ({len(df):,} rows)")
                            else:
                                st.warning(f"   ⚠️ {filename} not found or empty")
                                file_paths[key] = None
                        except Exception as e:
                            st.warning(f"   ⚠️ Could not load {filename}: {str(e)}")
                            file_paths[key] = None
                else:
                    # Manual upload mode - all files must be uploaded
                    st.warning("⚠️ Google Drive not connected. Please ensure all required files are available.")
                    # Set paths to None for now
                    for key in gdrive_files.keys():
                        file_paths[key] = None
                
                # Handle uploaded COGS file
                if 'cogs' in uploaded_files:
                    cogs_df = uploaded_files['cogs']
                    
                    # Validate COGS file columns
                    required_cogs_cols = ['product_id', 'COGS']
                    if not all(col in cogs_df.columns for col in required_cogs_cols):
                        st.error(f"❌ COGS file must contain columns: {', '.join(required_cogs_cols)}")
                        st.error(f"Found columns: {', '.join(cogs_df.columns.tolist())}")
                        st.stop()
                    
                    # Prepare COGS data
                    if 'product_name' not in cogs_df.columns:
                        cogs_df['product_name'] = 'Product ' + cogs_df['product_id'].astype(str)
                    
                    if 'COGS' in cogs_df.columns and 'cogs' not in cogs_df.columns:
                        cogs_df['cogs'] = cogs_df['COGS']
                    
                    # Save COGS to temp directory
                    cogs_path = os.path.join(tmpdir, 'cogs.csv')
                    cogs_df.to_csv(cogs_path, index=False)
                    file_paths['cogs'] = cogs_path
                
                # Handle uploaded SDPO file
                sdpo_path = None
                if 'sdpo' in uploaded_files:
                    sdpo_df = uploaded_files['sdpo']
                    sdpo_path = os.path.join(tmpdir, 'sdpo.csv')
                    sdpo_df.to_csv(sdpo_path, index=False)
                    file_paths['sdpo'] = sdpo_path
                
                # Validate that we have minimum required files
                if file_paths.get('im_pricing') is None or file_paths.get('comp_pricing') is None:
                    st.error("❌ Missing required files: IM Pricing and Competition Pricing must be available")
                    st.stop()
                
                # Run the complete pricing model
                st.write("🔄 Running pricing model...")
                results_df, summary = run_complete_pricing_model(
                    im_pricing_file=file_paths['im_pricing'],
                    comp_pricing_file=file_paths['comp_pricing'],
                    necc_pricing_file=file_paths.get('necc_pricing'),
                    cogs_file=file_paths['cogs'],
                    sdpo_file=file_paths.get('sdpo'),
                    stock_file=file_paths.get('stock'),
                    gmv_file=file_paths.get('gmv'),
                    exclusion_file=file_paths.get('exclusion'),
                    target_margin=target_margin,
                    category=selected_category
                )
            
            # Store in session state
            st.session_state.results_df = results_df
            st.session_state.summary = summary
            st.session_state.model_run = True
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# ==================== DISPLAY RESULTS ====================
if st.session_state.model_run and st.session_state.results_df is not None:
    results_df = st.session_state.results_df
    summary = st.session_state.summary
    
    st.success(f"✅ Model completed! Generated {len(results_df):,} prices")
    
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
    
    display_cols = ['ITEM_CODE', 'ITEM_NAME', 'cogs', 'Final Price', 'Final NM %', 
                   'Final SDPO %', 'category', 'target_margin_%']
    available_cols = [col for col in display_cols if col in results_df.columns]
    
    st.dataframe(
        results_df[available_cols].head(10), 
        use_container_width=True, 
        height=350,
        hide_index=True
    )
    
    # Download Button
    st.markdown("### 📥 Download Modeled Prices")
    
    # Modeled Prices CSV
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="📊 DOWNLOAD MODELED PRICES (CSV)",
        data=csv,
        file_name=f"modeled_prices_{selected_category.replace(' ', '_').lower()}.csv",
        mime="text/csv",
        use_container_width=True,
        type="primary"
    )
