# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model

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
    .stProgress > div > div {
        height: 6px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    /* Reduce gap after selectbox and number input */
    div[data-testid="stSelectbox"],
    div[data-testid="stNumberInput"] {
        margin-bottom: 0rem;
    }
    /* Reduce gap after file uploader */
    div[data-testid="stFileUploader"] {
        margin-bottom: 0rem;
    }
    /* Reduce gap between columns */
    div[data-testid="column"] {
        padding: 0.5rem;
    }
    /* Info box styling */
    div[data-baseweb="notification"] {
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    /* Metric styling */
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    /* Success/error message */
    .element-container:has(> .stSuccess),
    .element-container:has(> .stError) {
        margin-top: 0.3rem;
        margin-bottom: 0.3rem;
    }
    /* Reduce spacing in markdown */
    .element-container {
        margin-bottom: 0.5rem;
    }
    /* Caption styling */
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

# ==================== INSTRUCTIONS (Collapsible) ====================
with st.expander("📖 **HOW TO USE** - Click to view instructions", expanded=False):
    st.markdown("""
    **Step 1:** Select the product category from the dropdown  
    **Step 2:** Set your target margin percentage  
    **Step 3:** Upload COGS file (Required columns: `product_id`, `product_name`, `cogs`)  
    **Step 4:** Upload Brand Aligned Discount file (if any)  
    **Step 5:** Click "Run Pricing Model" button  
    **Step 6:** Download pricing recommendations
    
    **⚙️ Pricing Logic:**
    - Low stock (< 50): 40% markup
    - Medium (50-200): 30% markup
    - High stock (> 200): 20% markup
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
        label_visibility="collapsed"
    )

with col2:
    st.markdown("**🎯 Target Margin %**")
    target_margin = st.number_input(
        "Margin",
        min_value=0.0,
        max_value=100.0,
        value=30.0,
        step=0.5,
        format="%.1f",
        label_visibility="collapsed"
    )

# ==================== FILE UPLOADS ====================
# Dictionary to store uploaded files
uploaded_files = {}

# Upload Inputs Section
st.markdown('<div class="upload-card"><div class="section-title">📥 Upload Data Files</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.caption("**COGS Data** _(product_id, product_name, cogs)_")
    cogs_file = st.file_uploader("COGS", type=['csv'], key="cogs", label_visibility="collapsed")
    if cogs_file:
        uploaded_files['cogs'] = pd.read_csv(cogs_file)
        st.success(f"✓ {len(uploaded_files['cogs']):,} rows uploaded")

with col2:
    st.caption("**Brand Aligned Discount** _(Optional)_")
    discount_file = st.file_uploader("Discount", type=['csv'], key="discount", label_visibility="collapsed")
    if discount_file:
        uploaded_files['discount'] = pd.read_csv(discount_file)
        st.success(f"✓ {len(uploaded_files['discount']):,} rows uploaded")

st.markdown('</div>', unsafe_allow_html=True)

# ==================== RUN BUTTON ====================
# Check if required file is uploaded
is_ready = 'cogs' in uploaded_files

# Display selected parameters
st.info(f"📊 **Selected:** {selected_category} | **Target Margin:** {target_margin}%")

run_button = st.button(
    "🚀 RUN PRICING MODEL" if is_ready else "⏳ WAITING FOR COGS FILE...",
    type="primary",
    use_container_width=True,
    disabled=not is_ready
)

# ==================== PROCESS MODEL ====================
if run_button:
    try:
        cogs_df = uploaded_files['cogs']
        
        # Validate required columns
        required_cogs_cols = ['product_id', 'product_name', 'cogs']
        
        if not all(col in cogs_df.columns for col in required_cogs_cols):
            st.error(f"❌ COGS file must contain: {', '.join(required_cogs_cols)}")
        else:
            with st.spinner("⏳ Running pricing model..."):
                # You can pass selected_category and target_margin to your pricing model
                # For now, using dummy stocks data
                stocks_df = pd.DataFrame({
                    'product_id': cogs_df['product_id'],
                    'stock_level': 100  # Default stock level
                })
                
                results_df = run_pricing_model(cogs_df, stocks_df)
                
                # Add category and margin to results
                results_df['category'] = selected_category
                results_df['target_margin_%'] = target_margin
                
                st.session_state.results_df = results_df
                st.session_state.model_run = True
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# ==================== DISPLAY RESULTS ====================
if st.session_state.model_run and st.session_state.results_df is not None:
    results_df = st.session_state.results_df
    
    st.success(f"✅ Pricing model completed successfully! Generated {len(results_df):,} recommendations", icon="🎉")
    
    # Modeled Prices Insights
    st.markdown('<div class="upload-card"><div class="section-title">📊 Pricing Insights</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Total Products", f"{len(results_df):,}")
    with col2:
        st.metric("💵 Average Price", f"${results_df['recommended_price'].mean():.2f}")
    with col3:
        st.metric("⬇️ Min Price", f"${results_df['recommended_price'].min():.2f}")
    with col4:
        st.metric("⬆️ Max Price", f"${results_df['recommended_price'].max():.2f}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Table Preview
    st.markdown("### 📋 Sample Pricing Data (First 10 Rows)")
    st.dataframe(
        results_df.head(10), 
        use_container_width=True, 
        height=350,
        hide_index=True
    )
    
    # Download button
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="📥 DOWNLOAD COMPLETE PRICING TABLE (CSV)",
        data=csv,
        file_name=f"modeled_prices_{selected_category.replace(' ', '_').lower()}.csv",
        mime="text/csv",
        use_container_width=True,
        type="primary"
    )
