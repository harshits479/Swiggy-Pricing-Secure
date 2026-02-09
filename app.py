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
