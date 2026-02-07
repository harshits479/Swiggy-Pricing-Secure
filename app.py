# app.py
import streamlit as st
import pandas as pd
from pricing_model import run_pricing_model

# Page config
st.set_page_config(page_title="Pricing Model", page_icon="💰", layout="wide")

st.title("💰 Pricing Model")
st.write("Upload your COGS and Stock data to get pricing recommendations")

# Create two columns for file uploaders
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 COGS Data")
    st.write("Required columns: `product_id`, `product_name`, `cogs`")
    cogs_file = st.file_uploader("Upload COGS CSV", type=['csv'], key="cogs")

with col2:
    st.subheader("📦 Stock Data")
    st.write("Required columns: `product_id`, `stock_level`")
    stocks_file = st.file_uploader("Upload Stocks CSV", type=['csv'], key="stocks")

# Add some spacing
st.divider()

# Run button
if st.button("🚀 Run Model", type="primary", use_container_width=True):
    if cogs_file and stocks_file:
        try:
            # Read CSVs
            cogs_df = pd.read_csv(cogs_file)
            stocks_df = pd.read_csv(stocks_file)
            
            # Validate required columns
            required_cogs_cols = ['product_id', 'product_name', 'cogs']
            required_stocks_cols = ['product_id', 'stock_level']
            
            if not all(col in cogs_df.columns for col in required_cogs_cols):
                st.error(f"COGS file must contain columns: {required_cogs_cols}")
            elif not all(col in stocks_df.columns for col in required_stocks_cols):
                st.error(f"Stocks file must contain columns: {required_stocks_cols}")
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
            st.error(f"Error processing files: {str(e)}")
    else:
        st.warning("⚠️ Please upload both COGS and Stocks CSV files")

# Add footer with instructions
st.divider()
with st.expander("ℹ️ How to use this tool"):
    st.markdown("""
    ### Instructions:
    1. **Prepare your COGS CSV** with columns: `product_id`, `product_name`, `cogs`
    2. **Prepare your Stocks CSV** with columns: `product_id`, `stock_level`
    3. Upload both files using the file uploaders above
    4. Click "Run Model" to generate pricing recommendations
    5. Download the results as a CSV file
    
    ### Pricing Logic:
    - **Low stock** (< 50 units): 40% markup
    - **Medium stock** (50-200 units): 30% markup
    - **High stock** (> 200 units): 20% markup

    """)
