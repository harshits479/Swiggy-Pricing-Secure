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
    st.markdown("**📦 Select Product Category**")
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

st.markdown("---")

# Create placeholder containers for proper ordering
progress_container = st.container()
results_container = st.container()
uploads_container = st.container()

# ==================== FILE UPLOADS ====================
with uploads_container:
    # Dictionary to store uploaded files
    uploaded_files = {}

    # Upload Inputs Section
    st.markdown('<div class="upload-card"><div class="section-title">📥 Upload Inputs</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**COGS** _(Required: product_id, product_name, cogs)_")
        cogs_file = st.file_uploader("COGS", type=['csv'], key="cogs", label_visibility="collapsed")
        if cogs_file:
            uploaded_files['cogs'] = pd.read_csv(cogs_file)
            st.success(f"✓ {len(uploaded_files['cogs']):,} rows")

    with col2:
        st.caption("**Brand Aligned Discount** _(Optional)_")
        discount_file = st.file_uploader("Discount", type=['csv'], key="discount", label_visibility="collapsed")
        if discount_file:
            uploaded_files['discount'] = pd.read_csv(discount_file)
            st.success(f"✓ {len(uploaded_files['discount']):,} rows")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================== PROGRESS TRACKER & RUN BUTTON ====================
with progress_container:
    # Check if required file is uploaded
    is_ready = 'cogs' in uploaded_files

    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        st.metric("📂 Files Uploaded", f"{len(uploaded_files)}/2")

    with col2:
        st.metric("✅ Status", "Ready" if is_ready else "Upload COGS")

    with col3:
        run_button = st.button(
            "🚀 RUN MODEL" if is_ready else "⏳ UPLOAD COGS FILE",
            type="primary",
            use_container_width=True,
            disabled=not is_ready
        )

    # Progress bar
    progress = len(uploaded_files) / 2
    st.progress(progress)

    # Display selected parameters
    st.info(f"**Category:** {selected_category} | **Target Margin:** {target_margin}%")

    # ==================== PROCESS MODEL ====================
    if run_button:
        try:
            cogs_df = uploaded_files['cogs']
            
            # Validate required columns
            required_cogs_cols = ['product_id', 'product_name', 'cogs']
            
            if not all(col in cogs_df.columns for col in required_cogs_cols):
                st.error(f"❌ COGS must contain: {', '.join(required_cogs_cols)}")
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
with results_container:
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
            file_name=f"modeled_prices_{selected_category.replace(' ', '_').lower()}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary"
        )
        
        st.markdown("---")
