# pricing_engine.py
import pandas as pd
import numpy as np
import re
from datetime import datetime

# ==========================================
# 1. UOM NORMALIZER LOGIC
# ==========================================
class RobustUOMNormalizer:
    def __init__(self):
        self.knowledge_base = {
            "2 combo": "2_combo",
            # Add other known cases here
        }

    def normalize(self, uom_val, item_name=None):
        s_uom = str(uom_val).strip().lower()
        normalized_uom = self._parse_uom_string(s_uom)
        
        is_weight_or_vol = any(x in normalized_uom for x in ['_g', '_ml', '_kg', '_l'])
        is_missing = normalized_uom in ['', 'nan', 'unknown', 'nan_pieces']
        
        if (is_weight_or_vol or is_missing) and item_name:
            count_from_name = self._extract_count_from_name(item_name)
            if count_from_name:
                return f"{count_from_name}_pieces"
        
        return normalized_uom

    def _parse_uom_string(self, s):
        if s in self.knowledge_base: return self.knowledge_base[s]
        s = s.replace("i pack", "1 pack")
        
        match = re.search(r'pack.*\(\s*(\d+)\s*(?:pcs|pieces|pc)\s*\)', s)
        if match: return f"{match.group(1)}_pieces"

        match = re.search(r'^(\d+)\s*pack', s)
        if match: return f"{match.group(1)}_pieces"

        match = re.search(r'(\d+)\s*(?:pieces|pcs|piece)', s)
        if match: return f"{match.group(1)}_pieces"
        
        match = re.search(r'(\d+)\s*g', s)
        if match: return f"{match.group(1)}_g"
        
        if s.isdigit(): return f"{s}_pieces"
        return s

    def _extract_count_from_name(self, text):
        s = str(text).lower()
        match = re.search(r'(\d+)\s*(?:pc|pcs|piece|pieces)', s)
        if match: return int(match.group(1))
        
        match_eggs = re.search(r'(\d+)\s+(?:(?:\w+\s+){0,3})eggs', s)
        if match_eggs: return int(match_eggs.group(1))
        return None

def normalize_im_data(df):
    """Applies UOM Normalizer to Internal Data"""
    normalizer = RobustUOMNormalizer()
    # Assuming columns 'uom' and 'ITEM_NAME' exist
    if 'uom' not in df.columns: df['uom'] = ''
    
    df['Normalized_UOM'] = df.apply(
        lambda row: normalizer.normalize(row.get('uom', ''), row.get('ITEM_NAME', '')), 
        axis=1
    )
    return df

def normalize_comp_data(df):
    """Applies UOM Normalizer to Competitor Data"""
    normalizer = RobustUOMNormalizer()
    # Assuming 'product_name' and 'uom'
    df['Normalized_UOM'] = df.apply(
        lambda row: normalizer.normalize(row.get('uom', ''), row.get('product_name', '')), 
        axis=1
    )
    return df

# ==========================================
# 2. MATCHING ENGINE
# ==========================================
def run_matching_engine(im_df, comp_df):
    """
    Matches IM items to Comp items based on 'City', 'Normalized_UOM' and Name Similarity
    For this hackathon version, we assume a simple exact match on City + UOM + Item Name substring 
    or use the existing 'matched_id' if provided in inputs.
    """
    # Simple direct merge for demonstration if 'Match_Key' exists, 
    # otherwise we generate a key.
    
    # Create a simplified Match Key
    im_df['Match_Key'] = im_df['City'].astype(str) + "_" + im_df['Normalized_UOM'].astype(str)
    comp_df['Match_Key'] = comp_df['City'].astype(str) + "_" + comp_df['Normalized_UOM'].astype(str)
    
    # Merge
    # In a real scenario, this uses fuzzy logic. 
    # Here we simulate the output of the matching engine.
    merged_df = pd.merge(im_df, comp_df, on='Match_Key', how='left', suffixes=('', '_comp'))
    
    # Filter to ensure reasonable matches (optional)
    return merged_df

# ==========================================
# 3. PRICING ENGINE
# ==========================================
def run_pricing_engine(matched_df, cogs_df, necc_df, exclusion_df, stock_df, nm_target):
    """
    Core Pricing Logic
    1. Calculate Base Costs (COGS)
    2. Check Competitor Prices (Min/Avg)
    3. Check Stock Levels (from stock_df)
    4. Apply Net Margin Rules
    """
    # 1. Merge COGS
    # Ensure join keys are strings
    matched_df['Item Code'] = matched_df['Item Code'].astype(str)
    cogs_df['Item Code'] = cogs_df['Item Code'].astype(str)
    
    df = pd.merge(matched_df, cogs_df, on='Item Code', how='left')
    df['COGS'] = df['COGS'].fillna(0)
    
    # 2. Merge NECC Data (Benchmark)
    # Assuming NECC has 'City' and 'Price'
    if not necc_df.empty:
        necc_df['City'] = necc_df['City'].astype(str)
        df = pd.merge(df, necc_df[['City', 'NECC_Price']], on='City', how='left')
    
    # 3. Pricing Logic
    def calculate_price(row):
        cogs = row['COGS']
        if cogs == 0: return row.get('selling_price', 0) # Fallback
        
        # Target Price based on Margin
        target_price = cogs / (1 - (nm_target / 100))
        
        # Competitor Check (Don't be too expensive)
        comp_price = row.get('selling_price_comp', np.nan)
        if pd.notna(comp_price) and comp_price > 0:
            # Cap price at 110% of competitor
            target_price = min(target_price, comp_price * 1.10)
            
        return round(target_price, 2)

    df['Recommended_Price'] = df.apply(calculate_price, axis=1)
    
    # 4. Calculate Expected Metrics
    df['Projected_Margin'] = (df['Recommended_Price'] - df['COGS']) / df['Recommended_Price']
    df['Projected_Margin'] = df['Projected_Margin'].fillna(0)
    
    return df

# ==========================================
# 4. GMV GOODNESS & REPORTING
# ==========================================
def calculate_gmv_goodness(pricing_df, sensitivity_df, gmv_weights_df, day_of_week):
    """
    Calculates the 'Goodness' (Revenue Lift) using Price Sensitivity
    """
    # 1. Merge Sensitivity (Elasticity)
    sensitivity_df['Item Code'] = sensitivity_df['Item Code'].astype(str)
    pricing_df['Item Code'] = pricing_df['Item Code'].astype(str)
    
    # Filter sensitivity for the specific Day
    sens_day = sensitivity_df[sensitivity_df['Day'] == day_of_week]
    
    merged = pd.merge(pricing_df, sens_day[['Item Code', 'City', 'Price Senstitivity']], 
                      on=['Item Code', 'City'], how='left')
    
    # Default Elasticity if missing (Conservative -1.0)
    merged['Elasticity'] = merged['Price Senstitivity'].fillna(-1.0)
    
    # 2. Get Base Volume (from GMV Weights or assumption)
    # If GMV Weights has 'Daily_Avg_Qty', use it. Else assume 10.
    if not gmv_weights_df.empty and 'Daily_Avg_Qty' in gmv_weights_df.columns:
        gmv_weights_df['Item Code'] = gmv_weights_df['Item Code'].astype(str)
        merged = pd.merge(merged, gmv_weights_df[['Item Code', 'City', 'Daily_Avg_Qty']], 
                          on=['Item Code', 'City'], how='left')
        merged['Base_Qty'] = merged['Daily_Avg_Qty'].fillna(10)
    else:
        merged['Base_Qty'] = 10 # Fallback
        
    # 3. Calculate Goodness
    # Formula: New_Qty = Base_Qty * (1 + (Elasticity * %Price_Change))
    merged['Current_Price'] = merged['selling_price'].replace(0, 1) # Avoid div/0
    merged['Pct_Price_Change'] = (merged['Recommended_Price'] - merged['Current_Price']) / merged['Current_Price']
    
    merged['Pct_Qty_Change'] = merged['Elasticity'] * merged['Pct_Price_Change']
    merged['New_Qty'] = merged['Base_Qty'] * (1 + merged['Pct_Qty_Change'])
    
    # GMV Calculation
    merged['Old_GMV'] = merged['Current_Price'] * merged['Base_Qty']
    merged['New_GMV'] = merged['Recommended_Price'] * merged['New_Qty']
    merged['GMV_Goodness'] = merged['New_GMV'] - merged['Old_GMV']
    
    return merged

# ==========================================
# 5. FILE GENERATOR
# ==========================================
def generate_upload_files(final_df, city_map, spin_map):
    # Map City IDs and Spin IDs for the final upload format
    # This is a placeholder for your specific V5 logic
    
    upload_df = final_df[['City', 'Item Code', 'Recommended_Price']].copy()
    upload_df.columns = ['City', 'Item_Code', 'New_Price']
    
    return upload_df
