# pricing_model.py
import pandas as pd
import numpy as np
import re
from datetime import datetime
import calendar

class RobustUOMNormalizer:
    """UOM Normalizer for both IM and Competition data"""
    def __init__(self):
        self.knowledge_base = {}
        self.knowledge_base["2 combo"] = "2_combo"

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
        match = re.search(r'(\d+)\s*ml', s)
        if match: return f"{match.group(1)}_ml"
        
        if s.isdigit(): return f"{s}_pieces"
        return s

    def _extract_count_from_name(self, text):
        s = str(text).lower()
        match = re.search(r'(\d+)\s*(?:pc|pcs|piece|pieces)', s)
        if match: return int(match.group(1))
        
        match_eggs = re.search(r'(\d+)\s+(?:(?:\w+\s+){0,3})eggs', s)
        if match_eggs: return int(match_eggs.group(1))
        return None

class PricingEngine:
    """Main Pricing Engine"""
    
    def __init__(self):
        self.normalizer = RobustUOMNormalizer()
        
    def _standardize_cols(self, df):
        """Helper to standardize column names across different input files"""
        if df is None or df.empty: return df
        df = df.copy()
        
        df.columns = [str(c).strip() for c in df.columns]
        
        mapping_logic = {
            'Item Code': ['product_id', 'item_code', 'item code', 'sku', 'sku_id', 'article_id', 'material', 'item_id'],
            'City': ['city', 'city_name', 'location'],
            'UOM': ['uom', 'pack_size', 'quantity', 'unit'],
            'Item Name': ['product_name', 'item_name', 'item name', 'description', 'sku_name'],
            'MRP': ['mrp', 'max_price'],
            'Selling Price': ['selling_price', 'selling price', 'sp', 'current_price', 'price'],
            'COGS': ['cogs', 'cost', 'base_cost', 'cost_price', 'cp'],
            'Stock Level': ['stock_level', 'stock', 'inventory', 'qty_available', 'soh'],
            'Sensitivity Score': ['price_sensitivity_score', 'sensitivity_score', 'price senstitivity', 'elasticity']
        }
        
        new_names = {}
        for col in df.columns:
            col_lower = col.lower()
            for target, possible_matches in mapping_logic.items():
                if col_lower in possible_matches:
                    new_names[col] = target
                    break
        
        df.rename(columns=new_names, inplace=True)
        return df

    def normalize_im_data(self, df_im):
        print("📊 Normalizing IM UOM...")
        df = self._standardize_cols(df_im)
        if 'UOM' not in df.columns: df['UOM'] = ''
        if 'Item Name' not in df.columns: df['Item Name'] = ''
        df['Normalized_UOM'] = df.apply(lambda row: self.normalizer.normalize(row['UOM'], row['Item Name']), axis=1)
        return df
    
    def normalize_comp_data(self, df_comp):
        print("📊 Normalizing Competition UOM...")
        df = self._standardize_cols(df_comp)
        if 'UOM' not in df.columns: df['UOM'] = ''
        if 'Item Name' not in df.columns: df['Item Name'] = ''
        df['Normalized_UOM'] = df.apply(lambda row: self.normalizer.normalize(row['UOM'], row['Item Name']), axis=1)
        return df
    
    def matching_engine(self, df_im_norm, df_comp_norm, df_necc):
        print("🔗 Running Matching Engine...")
        df_im = df_im_norm.copy()
        
        if not df_comp_norm.empty and 'Selling Price' in df_comp_norm.columns:
            comp_price_map = df_comp_norm.groupby('Normalized_UOM')['Selling Price'].mean().to_dict()
            df_im['comp_avg_price'] = df_im['Normalized_UOM'].map(comp_price_map)
        else:
            df_im['comp_avg_price'] = np.nan
        
        if df_necc is not None:
            df_necc = self._standardize_cols(df_necc)
            if 'UOM' in df_necc.columns and 'Price' in df_necc.columns:
                necc_price_map = df_necc.groupby('UOM')['Price'].mean().to_dict()
                df_im['necc_price'] = df_im['Normalized_UOM'].map(necc_price_map)
        
        return df_im
    
    def pricing_engine(self, df_matched, df_cogs, df_sdpo, df_stock, df_gmv_weights, 
                       df_exclusions, target_margin, category):
        print("💰 Running Pricing Engine...")
        
        df = df_matched.copy()
        
        df_cogs = self._standardize_cols(df_cogs)
        df_stock = self._standardize_cols(df_stock)
        df_sdpo = self._standardize_cols(df_sdpo)

        if 'Item Code' in df.columns and 'Item Code' in df_cogs.columns:
            df['Item Code'] = df['Item Code'].astype(str)
            df_cogs['Item Code'] = df_cogs['Item Code'].astype(str)
            df = df.merge(df_cogs[['Item Code', 'COGS']], on='Item Code', how='left')
            df['COGS'] = df['COGS'].fillna(0)
        else:
            df['COGS'] = 0
            print("⚠️ Warning: COGS merge failed. Check Item Code columns.")

        if df_stock is not None and 'Item Code' in df.columns and 'Item Code' in df_stock.columns:
            df_stock['Item Code'] = df_stock['Item Code'].astype(str)
            df = df.merge(df_stock[['Item Code', 'Stock Level']], on='Item Code', how='left')
        
        df['base_price'] = df['COGS'] * (1 + target_margin / 100)
        
        df['comp_factor'] = 1.0
        if 'comp_avg_price' in df.columns:
             mask = (df['comp_avg_price'] > 0) & (df['base_price'] > df['comp_avg_price'] * 1.2)
             df.loc[mask, 'comp_factor'] = 0.95 
        
        if 'Stock Level' in df.columns:
            df['stock_factor'] = df['Stock Level'].apply(lambda x: 1.05 if x < 50 else (0.95 if x > 200 else 1.0))
        else:
            df['stock_factor'] = 1.0
            
        df['modeled_price'] = df['base_price'] * df['comp_factor'] * df['stock_factor']
        
        if df_sdpo is not None and not df_sdpo.empty:
             if 'Item Code' in df_sdpo.columns:
                 df_sdpo['Item Code'] = df_sdpo['Item Code'].astype(str)
                 df = df.merge(df_sdpo, on='Item Code', how='left', suffixes=('', '_sdpo'))
        
        df['Final Price'] = df['modeled_price'].round(2)
        df['category'] = category
        df['target_margin_%'] = target_margin
        
        return df

    def performance_reporting(self, df_priced, df_price_sensitivity, df_gmv_weights):
        print("📈 Generating Performance Report...")
        df = df_priced.copy()
        
        # Net Margin
        df['net_margin'] = 0.0
        mask = df['Final Price'] > 0
        df.loc[mask, 'net_margin'] = ((df.loc[mask, 'Final Price'] - df.loc[mask, 'COGS']) / df.loc[mask, 'Final Price'] * 100).round(2)
        
        # GMV Goodness Calculation (Actual Uplift %)
        df_sens = self._standardize_cols(df_price_sensitivity)
        df['gmv_uplift_pct'] = 0.0
        
        # We need Elasticity (Sensitivity) and Old Price (Selling Price)
        if df_sens is not None and not df_sens.empty:
            if 'Item Code' in df_sens.columns:
                df_sens['Item Code'] = df_sens['Item Code'].astype(str)
                df['Item Code'] = df['Item Code'].astype(str)
                # Average elasticity per item
                df_sens_unique = df_sens.groupby('Item Code')['Sensitivity Score'].mean().reset_index()
                df = df.merge(df_sens_unique, on='Item Code', how='left')
                
                # Default elasticity if missing
                df['Sensitivity Score'] = df['Sensitivity Score'].fillna(-1.0)
                
                # Formula:
                # % Price Change = (New - Old) / Old
                # % Vol Change = Elasticity * % Price Change
                # New Vol = 1 * (1 + % Vol Change)  [Assuming Base Vol = 1 for % calculation]
                # Old GMV = Old Price * 1
                # New GMV = New Price * New Vol
                # % GMV Uplift = (New GMV - Old GMV) / Old GMV * 100
                
                # Ensure we have Selling Price (Old Price)
                if 'Selling Price' not in df.columns:
                    # Fallback if Selling Price missing: use COGS + 10% as dummy old price
                    df['Selling Price'] = df['COGS'] * 1.10
                
                # Avoid div/0
                df['Selling Price'] = df['Selling Price'].replace(0, df['COGS'] * 1.10)
                
                df['pct_price_change'] = (df['Final Price'] - df['Selling Price']) / df['Selling Price']
                df['pct_vol_change'] = df['Sensitivity Score'] * df['pct_price_change']
                df['new_vol_proxy'] = 1 * (1 + df['pct_vol_change'])
                
                df['old_gmv_proxy'] = df['Selling Price'] * 1
                df['new_gmv_proxy'] = df['Final Price'] * df['new_vol_proxy']
                
                df['gmv_uplift_pct'] = ((df['new_gmv_proxy'] - df['old_gmv_proxy']) / df['old_gmv_proxy'] * 100).fillna(0)

        # Average of the percentages
        avg_uplift = df['gmv_uplift_pct'].mean()

        summary = {
            'avg_net_margin': df['net_margin'].mean(),
            'avg_gmv_uplift': avg_uplift,
            'total_products': len(df)
        }
        return df, summary

    def generate_upload_files(self, df_final, city_mapping, spin_mapping):
        print("📤 Generating Upload Files...")
        
        city_mapping = self._standardize_cols(city_mapping)
        spin_mapping = self._standardize_cols(spin_mapping)
        
        if 'City' in city_mapping.columns:
            city_mapping['city_clean'] = city_mapping['City'].astype(str).str.lower().str.strip()
            city_dict = city_mapping.drop_duplicates('city_clean').set_index('city_clean')['CITY_ID'].to_dict()
        else:
            city_dict = {}

        if 'Item Code' in spin_mapping.columns:
            spin_mapping['item_code_str'] = spin_mapping['Item Code'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            spin_dict = spin_mapping.drop_duplicates('item_code_str').set_index('item_code_str')['spin_id'].to_dict()
        else:
            spin_dict = {}
        
        if 'City' in df_final.columns:
            df_final['city_clean'] = df_final['City'].astype(str).str.lower().str.strip()
        else:
            df_final['city_clean'] = ''
            
        if 'Item Code' in df_final.columns:
            df_final['item_code_str'] = df_final['Item Code'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        else:
            df_final['item_code_str'] = ''
        
        now = datetime.now()
        valid_from = now.strftime("%d-%m-%Y 13:30")
        last_day = calendar.monthrange(now.year, now.month)[1]
        valid_till = f"{last_day}-{now.strftime('%m-%Y')} 23:59"

        def create_rows(df_subset, is_opp):
            rows = []
            idx = 1
            for _, row in df_subset.iterrows():
                c_id = city_dict.get(row.get('city_clean', ''), '')
                s_id = spin_dict.get(row.get('item_code_str', ''), '')
                
                if is_opp:
                    disc_type = "FINAL_PRICE"
                    disc_val = int(round(row.get('Final Price', 0)))
                else:
                    disc_type = "PERCENT"
                    mrp = row.get('MRP', 0)
                    fp = row.get('Final Price', 0)
                    disc_val = int(round(((mrp - fp)/mrp * 100))) if mrp > 0 else 0
                
                rows.append({
                    'INDEX': idx,
                    'SPIN_ID': s_id,
                    'CITY_ID': c_id,
                    'VALID_FROM': valid_from,
                    'VALID_TILL': valid_till,
                    'DISCOUNT_TYPE': disc_type,
                    'DISCOUNT_VALUE': disc_val,
                    'HIERARCHY_TYPE': "SDPO_CATM_BAU",
                    'BUSINESS_LINE': 7
                })
                idx += 1
            return pd.DataFrame(rows)

        if 'is_opp' in df_final.columns:
            opp_df = create_rows(df_final[df_final['is_opp'] == True], is_opp=True)
            brand_df = create_rows(df_final[df_final['is_opp'] == False], is_opp=False)
        else:
            opp_df = pd.DataFrame()
            brand_df = create_rows(df_final, is_opp=False)
            
        return opp_df, brand_df

def run_pricing_model(im_pricing, comp_pricing, necc_pricing, cogs_df, sdpo_df,
                      stock_insights, gmv_weights, price_sensitivity, 
                      city_mapping, spin_mapping, exclusions, 
                      target_margin, category):
    
    engine = PricingEngine()
    df_im_norm = engine.normalize_im_data(im_pricing)
    df_comp_norm = engine.normalize_comp_data(comp_pricing)
    df_matched = engine.matching_engine(df_im_norm, df_comp_norm, necc_pricing)
    df_priced = engine.pricing_engine(df_matched, cogs_df, sdpo_df, stock_insights, 
                                      gmv_weights, exclusions, target_margin, category)
    df_final, summary = engine.performance_reporting(df_priced, price_sensitivity, gmv_weights)
    opp_upload, branded_upload = engine.generate_upload_files(df_final, city_mapping, spin_mapping)
    
    return df_final, summary, opp_upload, branded_upload
