# pricing_model.py
import pandas as pd
import numpy as np
import re
from datetime import datetime
import calendar
from io import BytesIO

class RobustUOMNormalizer:
    """UOM Normalizer for both IM and Competition data"""
    def __init__(self):
        self.knowledge_base = {}
        self.knowledge_base["2 combo"] = "2_combo"

    def normalize(self, uom_val, item_name=None):
        """
        Main logic: Decides between UOM column and Item Name.
        """
        s_uom = str(uom_val).strip().lower()
        
        # 1. Normalize the basic UOM string first
        normalized_uom = self._parse_uom_string(s_uom)
        
        # 2. DECISION TIME: Should we trust the UOM or look at the Name?
        is_weight_or_vol = any(x in normalized_uom for x in ['_g', '_ml', '_kg', '_l'])
        is_missing = normalized_uom in ['', 'nan', 'unknown']
        
        if (is_weight_or_vol or is_missing) and item_name:
            count_from_name = self._extract_count_from_name(item_name)
            if count_from_name:
                return f"{count_from_name}_pieces"
        
        return normalized_uom

    def _parse_uom_string(self, s):
        """Standardizes strings like '1 pack (6 pcs)' -> '6_pieces'"""
        if s in self.knowledge_base: 
            return self.knowledge_base[s]
        
        s = s.replace("i pack", "1 pack")
        
        # Pattern: "Pack (X pcs)"
        match = re.search(r'pack.*\(\s*(\d+)\s*(?:pcs|pieces|pc)\s*\)', s)
        if match: return f"{match.group(1)}_pieces"

        # Pattern: "X Pack"
        match = re.search(r'^(\d+)\s*pack', s)
        if match: return f"{match.group(1)}_pieces"

        # Pattern: Pieces
        match = re.search(r'(\d+)\s*(?:pieces|pcs|piece)', s)
        if match: return f"{match.group(1)}_pieces"
        
        # Pattern: Weight/Vol
        match = re.search(r'(\d+)\s*g', s)
        if match: return f"{match.group(1)}_g"
        match = re.search(r'(\d+)\s*ml', s)
        if match: return f"{match.group(1)}_ml"
        
        # Fallback: Just Number
        if s.isdigit(): return f"{s}_pieces"
        
        return s

    def _extract_count_from_name(self, text):
        """
        Detects counts in names like "Egg Yolk 30 White Eggs" or "Freshen Eggs 18"
        """
        s = str(text).lower()
        
        # 1. Explicit 'pieces' inside name
        match = re.search(r'(\d+)\s*(?:pc|pcs|piece|pieces)', s)
        if match: return int(match.group(1))

        # 2. "30 White Eggs" / "10 Brown Eggs" / "30 Eggs"
        match_eggs = re.search(r'(\d+)\s+(?:(?:\w+\s+){0,3})eggs', s)
        if match_eggs:
            return int(match_eggs.group(1))

        # 3. "Eggs 18" (Number at end of string)
        match_end = re.search(r'eggs\s+(\d+)$', s)
        if match_end:
            return int(match_end.group(1))
            
        return None


class PricingEngine:
    """Main Pricing Engine with all logic from the notebook"""
    
    def __init__(self):
        self.normalizer = RobustUOMNormalizer()
        
    def normalize_im_data(self, df_im):
        """UOM Normalizer for IM data"""
        print("📊 Normalizing IM UOM...")
        df = df_im.copy()
        
        df['Normalized_UOM'] = df.apply(
            lambda row: self.normalizer.normalize(
                row.get('uom', ''), 
                row.get('ITEM_NAME', '')
            ), axis=1
        )
        
        print(f"✅ IM UOM Normalized: {len(df)} rows")
        return df
    
    def normalize_comp_data(self, df_comp):
        """UOM Normalizer for Competition data"""
        print("📊 Normalizing Competition UOM...")
        df = df_comp.copy()
        
        df['Normalized_UOM'] = df.apply(
            lambda row: self.normalizer.normalize(
                row.get('uom', ''), 
                row.get('product_name', '')
            ), axis=1
        )
        
        print(f"✅ Competition UOM Normalized: {len(df)} rows")
        return df
    
    def matching_engine(self, df_im_norm, df_comp_norm, df_necc):
        """
        Matching Engine: Matches IM products with Competition and NECC prices
        """
        print("🔗 Running Matching Engine...")
        
        # For demonstration, doing a simple UOM-based match
        # In production, you'd have more sophisticated matching logic
        
        df_im = df_im_norm.copy()
        
        # Match with competition based on UOM
        comp_price_map = df_comp_norm.groupby('Normalized_UOM')['selling_price'].mean().to_dict()
        df_im['comp_avg_price'] = df_im['Normalized_UOM'].map(comp_price_map)
        
        # Match with NECC
        if 'UOM' in df_necc.columns and 'Price' in df_necc.columns:
            necc_price_map = df_necc.groupby('UOM')['Price'].mean().to_dict()
            df_im['necc_price'] = df_im['Normalized_UOM'].map(necc_price_map)
        
        print(f"✅ Matching Complete: {len(df_im)} products matched")
        return df_im
    
    def pricing_engine(self, df_matched, df_cogs, df_sdpo, df_stock, df_gmv_weights, 
                       df_exclusions, target_margin, category):
        """
        Core Pricing Engine Logic
        """
        print("💰 Running Pricing Engine...")
        
        df = df_matched.copy()
        
        # Merge COGS
        if 'ITEM_CODE' in df.columns and 'product_id' in df_cogs.columns:
            df = df.merge(df_cogs[['product_id', 'cogs']], 
                         left_on='ITEM_CODE', right_on='product_id', how='left')
        
        # Merge Stock Insights
        if df_stock is not None and 'ITEM_CODE' in df.columns:
            stock_cols = ['ITEM_CODE', 'stock_level'] if 'stock_level' in df_stock.columns else df_stock.columns[:2]
            df = df.merge(df_stock[stock_cols], on='ITEM_CODE', how='left')
        
        # Calculate base price with target margin
        df['base_price'] = df['cogs'] * (1 + target_margin / 100)
        
        # Apply competitive intelligence
        df['comp_factor'] = 1.0
        if 'comp_avg_price' in df.columns:
            df.loc[df['comp_avg_price'].notna(), 'comp_factor'] = \
                df['comp_avg_price'] / df['base_price']
        
        # Apply stock-based adjustments
        if 'stock_level' in df.columns:
            df['stock_factor'] = df['stock_level'].apply(self._get_stock_factor)
        else:
            df['stock_factor'] = 1.0
        
        # Calculate final price
        df['modeled_price'] = df['base_price'] * df['comp_factor'] * df['stock_factor']
        
        # Apply SDPO (Brand Aligned Discount)
        if df_sdpo is not None and len(df_sdpo) > 0:
            # Merge SDPO data
            df = df.merge(df_sdpo, on='ITEM_CODE', how='left', suffixes=('', '_sdpo'))
        
        # Round to 2 decimals
        df['Final Price'] = df['modeled_price'].round(2)
        
        # Add category
        df['category'] = category
        df['target_margin_%'] = target_margin
        
        print(f"✅ Pricing Complete: {len(df)} products priced")
        return df
    
    def _get_stock_factor(self, stock_level):
        """Stock-based price adjustment"""
        if pd.isna(stock_level):
            return 1.0
        if stock_level < 50:
            return 1.05  # Increase price for low stock
        elif stock_level > 200:
            return 0.95  # Decrease price for high stock
        return 1.0
    
    def performance_reporting(self, df_priced, df_price_sensitivity, df_gmv_weights):
        """
        Calculate Performance Metrics: NM, PI, GMV Goodness
        """
        print("📈 Generating Performance Report...")
        
        df = df_priced.copy()
        
        # Calculate Net Margin (NM)
        if 'cogs' in df.columns and 'Final Price' in df.columns:
            df['net_margin'] = ((df['Final Price'] - df['cogs']) / df['Final Price'] * 100).round(2)
        else:
            df['net_margin'] = 0
        
        # Calculate Price Index (PI) - comparison with competition
        if 'comp_avg_price' in df.columns:
            df['price_index'] = (df['Final Price'] / df['comp_avg_price'] * 100).round(2)
        else:
            df['price_index'] = 100
        
        # GMV Goodness Score (using price sensitivity)
        df['gmv_goodness'] = 0
        if df_price_sensitivity is not None and len(df_price_sensitivity) > 0:
            # Merge price sensitivity data
            if 'ITEM_CODE' in df.columns and 'item_code' in df_price_sensitivity.columns:
                df = df.merge(
                    df_price_sensitivity[['item_code', 'price_sensitivity_score']], 
                    left_on='ITEM_CODE', 
                    right_on='item_code', 
                    how='left'
                )
                df['gmv_goodness'] = df['price_sensitivity_score'].fillna(50)
        
        # Summary metrics
        summary = {
            'avg_net_margin': df['net_margin'].mean(),
            'avg_price_index': df['price_index'].mean(),
            'avg_gmv_goodness': df['gmv_goodness'].mean(),
            'total_products': len(df)
        }
        
        print(f"✅ Performance Metrics Calculated")
        print(f"   📊 Avg Net Margin: {summary['avg_net_margin']:.2f}%")
        print(f"   📊 Avg Price Index: {summary['avg_price_index']:.2f}")
        print(f"   📊 Avg GMV Goodness: {summary['avg_gmv_goodness']:.2f}")
        
        return df, summary
    
    def generate_upload_files(self, df_final, city_mapping, spin_mapping):
        """
        Generate Upload Files (OPP and Branded)
        """
        print("📤 Generating Upload Files...")
        
        # Date logic
        now = datetime.now()
        valid_from = now.strftime("%d-%m-%Y 13:30")
        last_day_of_month = calendar.monthrange(now.year, now.month)[1]
        valid_till = f"{last_day_of_month}-{now.strftime('%m-%Y')} 23:59"
        
        # Create mappings
        def clean_str(x): 
            return str(x).lower().strip()
        
        city_mapping['city_clean'] = city_mapping['CITY'].apply(clean_str)
        city_dict = city_mapping.drop_duplicates('city_clean').set_index('city_clean')['CITY_ID'].to_dict()
        
        spin_mapping['item_code_str'] = spin_mapping['item_code'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        spin_dict = spin_mapping.drop_duplicates('item_code_str').set_index('item_code_str')['spin_id'].to_dict()
        
        df_final['city_clean'] = df_final['CITY'].apply(clean_str) if 'CITY' in df_final.columns else ''
        df_final['item_code_str'] = df_final['ITEM_CODE'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True) if 'ITEM_CODE' in df_final.columns else ''
        
        def create_row(idx, row, d_type, d_val, hierarchy):
            c_id = city_dict.get(row.get('city_clean', ''), '')
            s_id = spin_dict.get(row.get('item_code_str', ''), '')
            
            return {
                'INDEX': idx,
                'STORE_ID': '',
                'SPIN_ID': s_id,
                'CITY_ID': c_id,
                'VALID_FROM': valid_from,
                'VALID_TILL': valid_till,
                'DISCOUNT_TYPE': d_type,
                'DISCOUNT_VALUE': d_val,
                'CUSTOMER_SEGMENTS': '',
                'BRAND_ID': '',
                'CUSTOMER_BRAND_SEGMENTS': '',
                'CATEGORY_ID': '',
                'CUSTOMER_CATEGORY_SEGMENTS': '',
                'BUSINESS_LINE': 7,
                'DAY_OF_THE_WEEK': '',
                'SLOT_START_TIME': '',
                'SLOT_END_TIME': '',
                'REDEMPTION_LIMIT': '',
                'HIERARCHY_TYPE': hierarchy,
                'VIRTUAL_COMBO_ID': '',
                'BRAND_SHARE': ''
            }
        
        # Process OPP (Rounded Prices)
        opp_data = []
        if 'is_opp' in df_final.columns:
            df_opp = df_final[df_final['is_opp'] == True].copy()
        else:
            df_opp = pd.DataFrame()
            
        idx_opp = 1
        for _, row in df_opp.iterrows():
            try: 
                val = int(round(float(row['Final Price'])))
            except: 
                val = 0
            r = create_row(idx_opp, row, "FINAL_PRICE", val, "SDPO_CATM_BAU")
            opp_data.append(r)
            idx_opp += 1
            
        opp_df = pd.DataFrame(opp_data)
        
        # Process Branded (Rounded Percentages)
        brand_data = []
        if 'is_opp' in df_final.columns:
            df_brand = df_final[df_final['is_opp'] == False].copy()
        else:
            df_brand = df_final.copy()

        idx_br = 1
        for _, row in df_brand.iterrows():
            mrp = float(row.get('MRP', 0))
            final_price = float(row.get('Final Price', 0))
            if mrp <= 0: 
                continue
            
            total_disc_amt = max(0, mrp - final_price)
            total_pct = int(round((total_disc_amt / mrp) * 100))
            
            r1 = create_row(idx_br, row, "PERCENT", total_pct, "SDPO_CATM_BAU")
            brand_data.append(r1)
            idx_br += 1
        
        brand_df = pd.DataFrame(brand_data)
        
        print(f"✅ Upload Files Generated")
        print(f"   📄 OPP Prices: {len(opp_df)} rows")
        print(f"   📄 Branded Prices: {len(brand_df)} rows")
        
        return opp_df, brand_df


def run_pricing_model(im_pricing, comp_pricing, necc_pricing, cogs_df, sdpo_df,
                       stock_insights, gmv_weights, price_sensitivity, 
                       city_mapping, spin_mapping, exclusions, 
                       target_margin, category):
    """
    Main entry point for the pricing model
    """
    print("=" * 60)
    print("🚀 STARTING PRICING MODEL")
    print("=" * 60)
    
    engine = PricingEngine()
    
    # Step 1: UOM Normalization
    df_im_norm = engine.normalize_im_data(im_pricing)
    df_comp_norm = engine.normalize_comp_data(comp_pricing)
    
    # Step 2: Matching Engine
    df_matched = engine.matching_engine(df_im_norm, df_comp_norm, necc_pricing)
    
    # Step 3: Pricing Engine
    df_priced = engine.pricing_engine(
        df_matched, cogs_df, sdpo_df, stock_insights, 
        gmv_weights, exclusions, target_margin, category
    )
    
    # Step 4: Performance Reporting
    df_final, summary = engine.performance_reporting(
        df_priced, price_sensitivity, gmv_weights
    )
    
    # Step 5: Generate Upload Files
    opp_upload, branded_upload = engine.generate_upload_files(
        df_final, city_mapping, spin_mapping
    )
    
    print("=" * 60)
    print("✅ PRICING MODEL COMPLETE")
    print("=" * 60)
    
    return df_final, summary, opp_upload, branded_upload
