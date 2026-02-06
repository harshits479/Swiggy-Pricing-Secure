# pricing_model.py
import pandas as pd
import numpy as np

def run_pricing_model(cogs_df, stocks_df):
    """
    Simple pricing model that recommends prices based on COGS and stock levels
    
    Logic:
    - Low stock (< 50): Higher markup (40%)
    - Medium stock (50-200): Standard markup (30%)
    - High stock (> 200): Lower markup (20%) to move inventory
    """
    
    # Merge the dataframes on product_id
    merged = cogs_df.merge(stocks_df, on='product_id', how='inner')
    
    # Calculate markup based on stock levels
    def calculate_markup(stock_level):
        if stock_level < 50:
            return 1.40  # 40% markup
        elif stock_level <= 200:
            return 1.30  # 30% markup
        else:
            return 1.20  # 20% markup
    
    # Apply pricing logic
    merged['markup_multiplier'] = merged['stock_level'].apply(calculate_markup)
    merged['recommended_price'] = (merged['cogs'] * merged['markup_multiplier']).round(2)
    merged['markup_percentage'] = ((merged['markup_multiplier'] - 1) * 100).round(1)
    
    # Select and rename columns for output
    result = merged[[
        'product_id', 
        'product_name', 
        'cogs', 
        'stock_level',
        'markup_percentage',
        'recommended_price'
    ]]
    
    return result