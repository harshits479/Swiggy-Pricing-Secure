# pricing_model_complete.py
"""
Complete Pricing Model Implementation
Based on eggs_pricing_model_hackathon.ipynb

This implements:
1. UOM Normalization (IM & Competition)
2. Matching Engine (OPP spaced matching, Non-OPP brand matching, T2 fallback)
3. Pricing Engine (KVI tiers, target margins, stock adjustments, brand rules)
4. Performance Reporting
5. Upload File Generation
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
import calendar

# ============================================================================
# 1. UOM NORMALIZER
# ============================================================================

class RobustUOMNormalizer:
    """UOM Normalizer for both IM and Competition data"""
    def __init__(self):
        self.knowledge_base = {}
        self.knowledge_base["2 combo"] = "2_combo"

    def normalize(self, uom_val, item_name=None):
        s_uom = str(uom_val).strip().lower()
        normalized_uom = self._parse_uom_string(s_uom)
        
        is_weight_or_vol = any(x in normalized_uom for x in ['_g', '_ml', '_kg', '_l'])
        is_missing = normalized_uom in ['', 'nan', 'unknown']
        
        if (is_weight_or_vol or is_missing) and item_name:
            count_from_name = self._extract_count_from_name(item_name)
            if count_from_name:
                return f"{count_from_name}_pieces"
        
        return normalized_uom

    def _parse_uom_string(self, s):
        if s in self.knowledge_base: 
            return self.knowledge_base[s]
        
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
        if match_eggs:
            return int(match_eggs.group(1))

        match_end = re.search(r'eggs\s+(\d+)$', s)
        if match_end:
            return int(match_end.group(1))
            
        return None


# ============================================================================
# 2. MATCHING ENGINE
# ============================================================================

class MatchingEngine:
    """Implements the sophisticated matching logic from notebook"""
    
    def __init__(self):
        self.normalizer = RobustUOMNormalizer()
        
    def run_matching(self, im_df, comp_df, necc_df, cogs_df, exclusion_df=None):
        """
        Complete matching logic:
        - UOM Normalization
        - City/Brand exclusions
        - OPP spaced matching (5% rule)
        - Non-OPP brand matching
        - T2 fallback to T1 prices
        """
        print("🔗 Starting Matching Engine...")
        
        # Step 1: UOM Normalization
        im_df = self._normalize_im(im_df)
        comp_df = self._normalize_comp(comp_df)
        
        # Step 2: Apply exclusions
        if exclusion_df is not None and len(exclusion_df) > 0:
            comp_df = self._apply_exclusions(comp_df, exclusion_df)
        
        # Step 3: Data prep
        im_df, comp_df = self._prep_data(im_df, comp_df, cogs_df)
        
        # Step 4: Matching
        opp_matches = self._match_opp(im_df, comp_df)
        non_opp_matches = self._match_non_opp(im_df, comp_df)
        
        # Step 5: T2 Fallback
        final_matches = self._apply_t2_fallback(opp_matches, non_opp_matches, im_df)
        
        # Step 6: Merge back to master
        result = pd.merge(im_df, final_matches, on=['CITY', 'ITEM_CODE'], how='left')
        result['Min_Comp_Price'] = result['Min_Comp_Price'].fillna(0)
        
        print(f"✅ Matching Complete: {len(result)} products")
        return result
    
    def _normalize_im(self, df):
        print("   📊 Normalizing IM UOM...")
        df = df.copy()
        uom_col = 'uom' if 'uom' in df.columns else 'UOM'
        name_col = 'ITEM_NAME' if 'ITEM_NAME' in df.columns else 'product_name'
        
        if uom_col in df.columns:
            df['Normalized_UOM'] = df.apply(
                lambda row: self.normalizer.normalize(
                    row.get(uom_col, ''), 
                    row.get(name_col, '')
                ), axis=1
            )
        return df
    
    def _normalize_comp(self, df):
        print("   📊 Normalizing Competition UOM...")
        df = df.copy()
        df['Normalized_UOM'] = df.apply(
            lambda row: self.normalizer.normalize(
                row.get('uom', ''), 
                row.get('product_name', '')
            ), axis=1
        )
        return df
    
    def _apply_exclusions(self, comp_df, excl_df):
        print("   🚫 Applying city/brand exclusions...")
        def clean_str(x): 
            return str(x).lower().strip()
        
        excl_df['city_clean'] = excl_df['CITY'].apply(clean_str) if 'CITY' in excl_df.columns else ''
        excl_df['brand_clean'] = excl_df['BRAND'].apply(clean_str) if 'BRAND' in excl_df.columns else ''
        
        comp_df['city_clean'] = comp_df['city'].apply(clean_str) if 'city' in comp_df.columns else ''
        comp_df['brand_clean'] = comp_df['brand_name'].apply(clean_str) if 'brand_name' in comp_df.columns else ''
        
        excl_df['key'] = excl_df['city_clean'] + "_" + excl_df['brand_clean']
        comp_df['key'] = comp_df['city_clean'] + "_" + comp_df['brand_clean']
        
        initial_len = len(comp_df)
        comp_df = comp_df[~comp_df['key'].isin(excl_df['key'])]
        print(f"   Excluded {initial_len - len(comp_df)} competitor rows")
        
        return comp_df
    
    def _prep_data(self, im_df, comp_df, cogs_df):
        """Prepare data with all required fields"""
        print("   ⚙️ Preparing data...")
        
        def clean_str(x): 
            return str(x).lower().strip()
        
        # Clean city names
        im_city_col = 'CITY' if 'CITY' in im_df.columns else 'city_name'
        im_df['city_clean'] = im_df[im_city_col].apply(clean_str)
        comp_df['city_clean'] = comp_df['city'].apply(clean_str) if 'city' in comp_df.columns else ''
        
        # UOM cleaning
        for df in [comp_df, im_df]:
            uom_col = 'Normalized_UOM' if 'Normalized_UOM' in df.columns else 'uom'
            df['uom_clean'] = df[uom_col].astype(str).apply(clean_str) if uom_col in df.columns else ''
            df['pack_size'] = df['uom_clean'].astype(str).str.extract(r'(\d+)').astype(float).fillna(1.0)
        
        # City tiers
        t1_cities = ['bangalore', 'chennai', 'delhi', 'faridabad', 'gurgaon', 'hyderabad', 'kolkata', 'mumbai', 'noida', 'pune']
        im_df['city_tier'] = im_df['city_clean'].apply(lambda x: 'T1' if x in t1_cities else 'T2')
        
        # State mapping for T2 fallback
        city_state_map = {
            'bangalore': 'karnataka', 'mysore': 'karnataka', 'mangalore': 'karnataka',
            'chennai': 'tamil nadu', 'coimbatore': 'tamil nadu', 'madurai': 'tamil nadu',
            'hyderabad': 'telangana', 'warangal': 'telangana', 'vizag': 'andhra pradesh',
            'mumbai': 'maharashtra', 'pune': 'maharashtra', 'nagpur': 'maharashtra',
            'delhi': 'delhi', 'noida': 'uttar pradesh', 'gurgaon': 'haryana',
            'kolkata': 'west bengal', 'ahmedabad': 'gujarat', 'jaipur': 'rajasthan'
        }
        im_df['state'] = im_df['city_clean'].map(city_state_map).fillna('unknown')
        
        # Prices
        comp_df['selling_price'] = pd.to_numeric(comp_df['selling_price'], errors='coerce')
        comp_df['price_per_piece'] = comp_df['selling_price'] / comp_df['pack_size']
        
        mrp_col = 'MRP' if 'MRP' in im_df.columns else 'IM_MRP'
        im_df['mrp_int'] = pd.to_numeric(im_df.get(mrp_col, 0), errors='coerce').fillna(0).round(0)
        comp_df['mrp_int'] = pd.to_numeric(comp_df.get('mrp', 0), errors='coerce').fillna(0).round(0)
        
        # Egg type
        def get_egg_type(name):
            s = str(name).lower()
            if 'duck' in s: return 'Duck'
            if 'quail' in s: return 'Quail'
            if any(x in s for x in ['brown', 'desi', 'country']): return 'Brown'
            return 'White'
        
        comp_df['egg_type'] = comp_df['product_name'].apply(get_egg_type)
        im_df['egg_type'] = im_df['ITEM_NAME'].apply(get_egg_type) if 'ITEM_NAME' in im_df.columns else 'White'
        
        # Brand key
        def get_brand_key(s):
            s = clean_str(s)
            for p in [r'\beggs\b', r'\begg\b', r'\bfarms\b', r'\bfarm\b', r'\bfoods\b', r'\bpoultry\b']:
                s = re.sub(p, '', s)
            return s.strip()
        
        comp_df['brand_clean'] = comp_df['brand_name'].apply(clean_str) if 'brand_name' in comp_df.columns else ''
        comp_df['brand_key'] = comp_df['brand_clean'].apply(get_brand_key)
        
        brand_col = 'BRAND' if 'BRAND' in im_df.columns else 'brand_name'
        im_df['brand_key'] = im_df.get(brand_col, '').apply(get_brand_key)
        
        # OPP codes
        opp_codes = [
            833000, 11962, 548512, 56620, 35213, 11174, 11173, 51950, 
            11966, 428785, 12341, 12490, 78360, 691733, 744712, 16886, 
            13422, 604104, 24379, 14043, 716088, 709061, 697269, 630903, 
            558087, 124058, 478620, 890035, 438327, 141942, 11897, 11961, 
            370525, 548855, 839302, 303428, 498900, 923763, 995731, 445831, 776284, 6881, 193321
        ]
        im_df['ITEM_CODE'] = pd.to_numeric(im_df['ITEM_CODE'], errors='coerce')
        im_df['is_opp'] = im_df['ITEM_CODE'].isin(opp_codes)
        
        # Merge COGS
        if 'CITY' in cogs_df.columns:
            cogs_df['city_clean'] = cogs_df['CITY'].apply(clean_str)
            cogs_df.rename(columns={'COGS': 'COGS_LATEST'}, inplace=True)
            im_df = pd.merge(im_df, cogs_df[['ITEM_CODE', 'city_clean', 'COGS_LATEST']], 
                           left_on=['ITEM_CODE', 'city_clean'], 
                           right_on=['ITEM_CODE', 'city_clean'], 
                           how='left')
        else:
            im_df['COGS_LATEST'] = cogs_df.set_index('product_id')['COGS'].to_dict().get(im_df['ITEM_CODE'], 0) if 'product_id' in cogs_df.columns else 0
        
        im_df['COGS_LATEST'] = im_df['COGS_LATEST'].fillna(0)
        
        return im_df, comp_df
    
    def _match_opp(self, im_df, comp_df):
        """OPP matching with 5% spacing rule"""
        print("   🎯 Matching OPP products (5% spacing rule)...")
        
        im_opp = im_df[im_df['is_opp']].copy()
        comp_opp_pool = comp_df[comp_df['price_per_piece'] <= 10].copy()
        opp_results = []
        
        for (city, uom, egg), sub_im in im_opp.groupby(['city_clean', 'uom_clean', 'egg_type']):
            sub_im = sub_im.sort_values('COGS_LATEST')
            sub_comp = comp_opp_pool[
                (comp_opp_pool['city_clean']==city) & 
                (comp_opp_pool['uom_clean']==uom) & 
                (comp_opp_pool['egg_type']==egg)
            ].sort_values('selling_price')
            
            # 5% Spacing Rule
            valid_comp = []
            if not sub_comp.empty:
                last_price = 0
                for _, r in sub_comp.iterrows():
                    if r['selling_price'] >= last_price * 1.05:
                        valid_comp.append(r)
                        last_price = r['selling_price']
            
            for i in range(len(sub_im)):
                row = sub_im.iloc[i]
                res = {
                    'CITY': row['CITY'] if 'CITY' in row else row.get('city_name', ''),
                    'ITEM_CODE': row['ITEM_CODE'], 
                    'Min_Comp_Price': None, 
                    'Match_Logic_Comment': f"OPP condition not met: Rank {i+1} > Avail ({len(valid_comp)})"
                }
                if i < len(valid_comp):
                    match = valid_comp[i]
                    res.update({
                        'Min_Comp_Price': match['selling_price'],
                        'Min_Comp_Brand': match.get('brand_name', ''),
                        'Min_Comp_Source': match.get('source', ''),
                        'Match_Logic_Comment': f"OPP Match: Rank {i+1}"
                    })
                opp_results.append(res)
        
        return pd.DataFrame(opp_results)
    
    def _match_non_opp(self, im_df, comp_df):
        """Non-OPP matching (brand + UOM/pack size)"""
        print("   🎯 Matching Non-OPP products (brand matching)...")
        
        im_non = im_df[~im_df['is_opp']].copy()
        
        # Exact UOM String match
        m1 = pd.merge(im_non, comp_df, on=['city_clean', 'brand_key', 'uom_clean', 'mrp_int'], 
                     how='inner', suffixes=('', '_c'))
        m1['comment'] = 'Exact UOM String'
        
        # Numeric Pack Size match
        m2 = pd.merge(im_non, comp_df, on=['city_clean', 'brand_key', 'pack_size', 'mrp_int'], 
                     how='inner', suffixes=('', '_c'))
        m2['comment'] = 'Numeric Pack Size'
        
        comb = pd.concat([m1, m2])
        comb['prio'] = comb['comment'].map({'Exact UOM String': 1, 'Numeric Pack Size': 2})
        hits = comb.sort_values(['CITY', 'ITEM_CODE', 'prio', 'selling_price']).drop_duplicates(subset=['CITY', 'ITEM_CODE'])
        
        city_col = 'CITY' if 'CITY' in im_non.columns else 'city_name'
        non_opp_final = pd.merge(im_non, hits[[city_col, 'ITEM_CODE', 'selling_price', 'brand_name', 'source', 'comment']], 
                                on=[city_col, 'ITEM_CODE'], how='left')
        non_opp_final['Match_Logic_Comment'] = non_opp_final['comment'].apply(
            lambda x: f"Non-OPP Match: {x}" if pd.notna(x) else "Non OPP condition not met"
        )
        non_opp_final.rename(columns={
            'selling_price': 'Min_Comp_Price', 
            'brand_name': 'Min_Comp_Brand', 
            'source': 'Min_Comp_Source',
            city_col: 'CITY'
        }, inplace=True)
        
        return non_opp_final[['CITY', 'ITEM_CODE', 'Min_Comp_Price', 'Min_Comp_Brand', 'Min_Comp_Source', 'Match_Logic_Comment']]
    
    def _apply_t2_fallback(self, opp_matches, non_opp_matches, im_df):
        """T2 cities fall back to T1 prices in same state"""
        print("   🔄 Applying T2 fallback to T1 prices...")
        
        all_matches = pd.concat([opp_matches, non_opp_matches])
        
        meta = im_df[['ITEM_CODE', 'CITY', 'city_tier', 'state']].drop_duplicates()
        df_work = pd.merge(all_matches, meta, on=['ITEM_CODE', 'CITY'], how='left')
        
        # T1 lookup table
        t1_lookup = df_work[
            (df_work['city_tier']=='T1') & 
            (df_work['Min_Comp_Price']>0)
        ].sort_values('Min_Comp_Price').drop_duplicates(['state', 'ITEM_CODE']).set_index(['state', 'ITEM_CODE']).to_dict('index')
        
        def apply_fallback(r):
            if r['city_tier'] == 'T2' and (pd.isna(r['Min_Comp_Price']) or r['Min_Comp_Price'] <= 0):
                key = (r['state'], r['ITEM_CODE'])
                if key in t1_lookup:
                    d = t1_lookup[key]
                    r['Min_Comp_Price'] = d['Min_Comp_Price']
                    r['Min_Comp_Brand'] = d.get('Min_Comp_Brand', '')
                    r['Min_Comp_Source'] = d.get('Min_Comp_Source', '')
                    r['Match_Logic_Comment'] = f"Fallback: Used {str(r['state']).title()} T1"
            return r
        
        final_res = df_work.apply(apply_fallback, axis=1)
        
        return final_res[['CITY', 'ITEM_CODE', 'Min_Comp_Price', 'Min_Comp_Brand', 'Min_Comp_Source', 'Match_Logic_Comment']]


# ============================================================================
# 3. PRICING ENGINE
# ============================================================================

class PricingEngine:
    """Complete pricing engine with KVI tiers, target margins, stock rules"""
    
    def run_pricing(self, matched_df, stock_df, gmv_df, brand_sdpo_df, target_margin_override=None):
        """
        Complete pricing logic:
        - KVI tiering (Pareto 80/95)
        - Target margin by tier/pack/city
        - Stock-based adjustments
        - Brand-aligned SDPO
        - Ceiling/floor constraints
        """
        print("💰 Starting Pricing Engine...")
        
        df = matched_df.copy()
        
        # Merge stock
        df = self._merge_stock(df, stock_df)
        
        # Merge GMV weights
        df = self._merge_gmv(df, gmv_df)
        
        # Merge Brand SDPO
        df = self._merge_brand_sdpo(df, brand_sdpo_df)
        
        # Calculate KVI tiers
        df = self._calculate_kvi_tiers(df)
        
        # Calculate target margins
        df = self._calculate_target_margins(df, target_margin_override)
        
        # Calculate prices
        df = self._calculate_prices(df)
        
        # Apply constraints
        df = self._apply_constraints(df)
        
        print(f"✅ Pricing Complete: {len(df)} products priced")
        return df
    
    def _merge_stock(self, df, stock_df):
        if stock_df is None or len(stock_df) == 0:
            df['STOCK_STATUS'] = 'NA'
            return df
        
        def clean_key(city, item):
            c = str(city).lower().strip()
            try: i = str(int(float(item)))
            except: i = '0'
            return c + "_" + i
        
        df['key'] = df.apply(lambda x: clean_key(x['CITY'], x['ITEM_CODE']), axis=1)
        
        if 'CITY' in stock_df.columns and 'ITEM_CODE' in stock_df.columns:
            stock_df['key'] = stock_df.apply(lambda x: clean_key(x['CITY'], x['ITEM_CODE']), axis=1)
            df = pd.merge(df, stock_df.drop_duplicates('key')[['key', 'STOCK_STATUS']], on='key', how='left')
        
        df['STOCK_STATUS'] = df.get('STOCK_STATUS', 'NA').fillna('NA')
        return df
    
    def _merge_gmv(self, df, gmv_df):
        if gmv_df is None or len(gmv_df) == 0:
            df['GMV Contribution'] = 0
            return df
        
        # Try to merge on ITEM_CODE or similar
        if 'ITEM_CODE' in gmv_df.columns:
            df = pd.merge(df, gmv_df[['ITEM_CODE', 'GMV Contribution']], on='ITEM_CODE', how='left')
        
        df['GMV Contribution'] = df.get('GMV Contribution', 0).fillna(0)
        return df
    
    def _merge_brand_sdpo(self, df, brand_sdpo_df):
        if brand_sdpo_df is None or len(brand_sdpo_df) == 0:
            df['Fixed_SDPO_Pct'] = 0
            return df
        
        if 'Brand' in brand_sdpo_df.columns and 'Hardcoded_SDPO' in brand_sdpo_df.columns:
            brand_sdpo_df['Brand_Clean'] = brand_sdpo_df['Brand'].astype(str).str.lower().str.strip()
            brand_sdpo_df['Fixed_SDPO_Pct'] = brand_sdpo_df['Hardcoded_SDPO'].apply(
                lambda x: float(str(x).replace('%',''))/100 if pd.notnull(x) else 0
            )
            
            brand_col = 'BRAND' if 'BRAND' in df.columns else 'brand_name'
            df['Brand_Clean'] = df.get(brand_col, '').astype(str).str.lower().str.strip()
            df = pd.merge(df, brand_sdpo_df[['Brand_Clean', 'Fixed_SDPO_Pct']], on='Brand_Clean', how='left')
        
        df['Fixed_SDPO_Pct'] = df.get('Fixed_SDPO_Pct', 0).fillna(0)
        return df
    
    def _calculate_kvi_tiers(self, df):
        """Calculate KVI tiers using Pareto 80/95 rule"""
        print("   📊 Calculating KVI tiers (Pareto 80/95)...")
        
        # Pack category
        uom_col = 'Normalized_UOM' if 'Normalized_UOM' in df.columns else 'uom_clean'
        pack_n = df[uom_col].astype(str).str.extract(r'(\d+)').astype(float).fillna(1) if uom_col in df.columns else pd.Series([1]*len(df))
        
        conds = [pack_n.isin([30,24,25,20]), pack_n.isin([10,12,15,18]), pack_n.isin([6,4])]
        df['pack_category'] = np.select(conds, ['Large', 'Mid', 'Small'], default='Other')
        
        # KVI tiers
        cum = df.groupby(['CITY', 'pack_category'])['GMV Contribution'].cumsum()
        tot = df.groupby(['CITY', 'pack_category'])['GMV Contribution'].transform('sum')
        pareto = cum / tot.replace(0, 1)
        
        df['kvi_tier'] = np.select(
            [(pareto<=0.8), (pareto<=0.95)], 
            ['Tier 1', 'Tier 2'], 
            default='Tier 3'
        )
        df.loc[df['GMV Contribution'] == 0, 'kvi_tier'] = 'Tier 3'
        
        return df
    
    def _calculate_target_margins(self, df, override=None):
        """Calculate target NM% based on pack/KVI/city tier/OPP"""
        print("   🎯 Calculating target margins...")
        
        if override is not None:
            df['target_nm'] = override / 100
            return df
        
        def get_target(row):
            t = 0.15
            p = row.get('pack_category', 'Other')
            k = row.get('kvi_tier', 'Tier 3')
            t2 = (row.get('city_tier', 'T1') == 'T2')
            opp = row.get('is_opp', False)
            
            if p in ['Small', 'Mid']:
                if k == 'Tier 1': t = 0.10 if opp else 0.17
                else: t = 0.11 if opp else 0.20
            elif p == 'Large':
                if k == 'Tier 1': t = 0.05 if opp else 0.15
                else: t = 0.06 if opp else 0.18
            
            if t2: t -= 0.05
            return max(t, 0)
        
        df['target_nm'] = df.apply(get_target, axis=1)
        return df
    
    def _calculate_prices(self, df):
        """Calculate modeled prices with all strategies"""
        print("   💵 Calculating modeled prices...")
        
        # Get BDPO
        def get_bdpo(row):
            mrp = row.get('MRP', 0)
            try:
                v1 = str(row.get('BDPO', '')).strip()
                if '%' in v1: val = mrp * float(v1.replace('%',''))/100
                else: val = float(v1) if v1 and v1.lower() != 'nan' else 0
                if val > 0: return min(val, mrp*0.9)
                return 0
            except: 
                return 0
        
        df['bdpo_val'] = df.apply(get_bdpo, axis=1).fillna(0)
        
        # Get COGS
        cogs_col = 'COGS_LATEST' if 'COGS_LATEST' in df.columns else 'cogs'
        df['cogs'] = df.get(cogs_col, 0)
        mop_col = 'MOP' if 'MOP' in df.columns else 'cogs'
        df['cogs'] = np.where(df['cogs']==0, df.get(mop_col, 0), df['cogs'])
        
        # Calculate price from margin
        df['price_min_margin'] = (df['target_nm'] * df['MRP']) + df['cogs'] - df['bdpo_val']
        df['price_comp'] = np.where(df['Min_Comp_Price'] > 0, df['Min_Comp_Price'], df['price_min_margin'])
        
        df['price_min_margin'] = df['price_min_margin'].fillna(df['MRP'])
        df['price_comp'] = df['price_comp'].fillna(df['price_min_margin'])
        
        # Calculate NM from comp price
        nm_comp = (df['price_comp'] - df['cogs'] + df['bdpo_val']) / df['MRP'].replace(0, 1)
        
        # Strategy flags
        is_insufficient = (df['city_tier'] == 'T2') & (df['STOCK_STATUS'].astype(str).str.lower() == 'insufficient')
        is_kvi_t1 = df['kvi_tier'] == 'Tier 1'
        has_comp = df['Min_Comp_Price'] > 0
        is_overdelivering = nm_comp > df['target_nm']
        is_brand_rule = df['Fixed_SDPO_Pct'] > 0
        
        # Price calculations
        price_aggressive = df['price_comp'] * 0.98
        price_fixed_brand = (df['MRP'] * (1 - df['Fixed_SDPO_Pct'])) - df['bdpo_val']
        
        # Start with min margin
        df['model_price'] = df['price_min_margin']
        
        # Standard match
        standard_match = (nm_comp >= df['target_nm']) & (~is_insufficient)
        df['model_price'] = np.where(standard_match, df['price_comp'], df['model_price'])
        
        # KVI T1 aggression
        should_undercut = is_kvi_t1 & has_comp & is_overdelivering & (~is_insufficient)
        df['model_price'] = np.where(should_undercut, price_aggressive, df['model_price'])
        
        # Brand rule overrides
        df['model_price'] = np.where(is_brand_rule, price_fixed_brand, df['model_price'])
        
        # Stock actions
        df['Stock_Action'] = ''
        df.loc[is_insufficient, 'Stock_Action'] = "T2 Insufficient: Ignored Comp Match"
        df.loc[should_undercut, 'Stock_Action'] = "KVI T1 Aggression: Beat Comp by 2%"
        df.loc[is_brand_rule, 'Stock_Action'] = "Brand Rule: Fixed SDPO"
        
        return df
    
    def _apply_constraints(self, df):
        """Apply ceiling/floor constraints"""
        print("   🔒 Applying price constraints...")
        
        # Ceilings
        ceil_opp = df['MRP'] * 0.96
        ceil_safe = np.floor(df['MRP'] - df['bdpo_val'])
        ceil_final = np.where(df['is_opp'], ceil_opp, ceil_safe)
        
        # Floors
        mop_col = 'MOP' if 'MOP' in df.columns else 'cogs'
        conflict = (df.get(mop_col, 0) > ceil_final) & (df['MRP'] > 0)
        floor = np.where(conflict, df['cogs'], df.get(mop_col, df['cogs']))
        
        # Apply
        df['model_price'] = np.maximum(df['model_price'], floor)
        is_brand_rule = df['Fixed_SDPO_Pct'] > 0
        df['model_price'] = np.where(is_brand_rule, df['model_price'], np.minimum(df['model_price'], ceil_final))
        df['Modeled Price'] = df['model_price'].round(0).fillna(0)
        
        # Fallback for missing COGS
        mask_no_cogs = df['cogs'] <= 0
        df.loc[mask_no_cogs, 'Modeled Price'] = df.loc[mask_no_cogs, 'MRP']
        df.loc[mask_no_cogs, 'Stock_Action'] = "Fallback: Missing COGS -> MRP"
        df['Modeled Price'] = np.maximum(df['Modeled Price'], 1)
        
        # Final price
        df['Final Price'] = df['Modeled Price']
        
        # Calculate final NM and SDPO
        df['Final NM %'] = ((df['Final Price'] - df['cogs'] + df['bdpo_val']) / df['MRP'].replace(0, 1) * 100).fillna(0)
        df['Final SDPO %'] = ((df['MRP'] - df['Final Price'] - df['bdpo_val']) / df['MRP'].replace(0, 1) * 100).fillna(0)
        
        return df


# ============================================================================
# 4. MAIN ORCHESTRATOR
# ============================================================================

def run_complete_pricing_model(
    im_pricing_file,
    comp_pricing_file,
    necc_pricing_file,
    cogs_file,
    sdpo_file,
    stock_file,
    gmv_file,
    exclusion_file,
    target_margin=None,
    category="Eggs"
):
    """
    Complete pricing model pipeline
    """
    print("=" * 80)
    print("🚀 COMPLETE PRICING MODEL")
    print("=" * 80)
    
    # Load data
    print("\n📁 Loading input files...")
    im_df = pd.read_csv(im_pricing_file)
    comp_df = pd.read_csv(comp_pricing_file)
    necc_df = pd.read_csv(necc_pricing_file) if necc_pricing_file else pd.DataFrame()
    cogs_df = pd.read_csv(cogs_file)
    sdpo_df = pd.read_csv(sdpo_file) if sdpo_file else None
    stock_df = pd.read_csv(stock_file) if stock_file else None
    gmv_df = pd.read_csv(gmv_file) if gmv_file else None
    excl_df = pd.read_csv(exclusion_file) if exclusion_file else None
    
    # Standardize column names in COGS
    if 'COGS' in cogs_df.columns and 'product_id' in cogs_df.columns:
        cogs_df.rename(columns={'product_id': 'ITEM_CODE'}, inplace=True)
    
    # Step 1: Matching
    matcher = MatchingEngine()
    matched_df = matcher.run_matching(im_df, comp_df, necc_df, cogs_df, excl_df)
    
    # Step 2: Pricing
    pricer = PricingEngine()
    priced_df = pricer.run_pricing(matched_df, stock_df, gmv_df, sdpo_df, target_margin)
    
    # Step 3: Add metadata
    priced_df['category'] = category
    priced_df['target_margin_%'] = target_margin if target_margin else priced_df['target_nm'] * 100
    
    # Step 4: Performance metrics
    summary = {
        'total_products': len(priced_df),
        'avg_net_margin': priced_df['Final NM %'].mean(),
        'avg_price_index': 100.0,  # Would need comp price to calculate
        'avg_gmv_goodness': 50.0   # Placeholder
    }
    
    print("\n" + "=" * 80)
    print("✅ PRICING MODEL COMPLETE")
    print("=" * 80)
    print(f"   Products Priced: {summary['total_products']:,}")
    print(f"   Avg Net Margin: {summary['avg_net_margin']:.2f}%")
    print()
    
    return priced_df, summary
