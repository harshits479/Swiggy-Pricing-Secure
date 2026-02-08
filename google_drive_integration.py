# google_drive_integration.py
"""
Google Drive Integration Module for Pricing Model

This module handles fetching files from Google Drive folder "Pricing Inputs"
"""

import os
import io
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

class GoogleDriveLoader:
    """
    Loads pricing input files from Google Drive
    """
    
    def __init__(self, credentials_path=None):
        """
        Initialize Google Drive connection
        
        Args:
            credentials_path: Path to service account JSON credentials file
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.service = None
        self.folder_id = None
        
    def authenticate(self):
        """Authenticate with Google Drive API"""
        try:
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
                self.service = build('drive', 'v3', credentials=credentials)
                print("✅ Google Drive authentication successful")
                return True
            else:
                print("⚠️ Google Drive credentials not found. Using local files.")
                return False
        except Exception as e:
            print(f"❌ Google Drive authentication failed: {e}")
            return False
    
    def find_folder(self, folder_name="Pricing Inputs"):
        """Find the Pricing Inputs folder in Google Drive"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            items = results.get('files', [])
            if items:
                self.folder_id = items[0]['id']
                print(f"✅ Found folder '{folder_name}' (ID: {self.folder_id})")
                return self.folder_id
            else:
                print(f"⚠️ Folder '{folder_name}' not found in Google Drive")
                return None
        except Exception as e:
            print(f"❌ Error finding folder: {e}")
            return None
    
    def download_file(self, file_name):
        """Download a CSV file from the Pricing Inputs folder"""
        try:
            # Search for file in the folder
            query = f"'{self.folder_id}' in parents and name='{file_name}' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            items = results.get('files', [])
            if not items:
                print(f"⚠️ File '{file_name}' not found in folder")
                return None
            
            file_id = items[0]['id']
            
            # Download file content
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Convert to pandas DataFrame
            file_buffer.seek(0)
            df = pd.read_csv(file_buffer)
            print(f"✅ Downloaded '{file_name}': {len(df)} rows")
            return df
            
        except Exception as e:
            print(f"❌ Error downloading '{file_name}': {e}")
            return None
    
    def load_all_pricing_inputs(self):
        """
        Load all required pricing input files from Google Drive
        
        Returns:
            dict: Dictionary containing all input DataFrames
        """
        files_to_load = {
            'im_pricing': 'im_pricing.csv',
            'competition_pricing': 'competition_pricing.csv',
            'necc_pricing': 'necc_egg_prices_cleaned.csv',
            'gmv_weights': 'gmv_weights.csv',
            'stock_insights': 'stock_insights.csv',
            'city_brand_exclusion': 'city_brand_exclusion_list.csv',
            'city_mapping': 'city_id_mapping.csv',
            'spin_mapping': 'spin_id_mapping.csv',
            'price_sensitivity': 'price_sensitivity.csv'
        }
        
        data = {}
        
        # Authenticate
        if not self.authenticate():
            print("⚠️ Skipping Google Drive - will need manual file uploads")
            return None
        
        # Find folder
        if not self.find_folder():
            print("⚠️ Cannot proceed without 'Pricing Inputs' folder")
            return None
        
        # Download each file
        print("\n📥 Downloading files from Google Drive...")
        for key, filename in files_to_load.items():
            df = self.download_file(filename)
            if df is not None:
                data[key] = df
            else:
                print(f"⚠️ Warning: {filename} could not be loaded")
        
        print(f"\n✅ Loaded {len(data)}/{len(files_to_load)} files from Google Drive")
        return data


# Alternative: Load from local directory (fallback)
def load_from_local_directory(directory_path="pricing_inputs"):
    """
    Load pricing input files from local directory (fallback method)
    
    Args:
        directory_path: Path to local directory containing input files
        
    Returns:
        dict: Dictionary containing all input DataFrames
    """
    files_to_load = {
        'im_pricing': 'im_pricing.csv',
        'competition_pricing': 'competition_pricing.csv',
        'necc_pricing': 'necc_egg_prices_cleaned.csv',
        'gmv_weights': 'gmv_weights.csv',
        'stock_insights': 'stock_insights.csv',
        'city_brand_exclusion': 'city_brand_exclusion_list.csv',
        'city_mapping': 'city_id_mapping.csv',
        'spin_mapping': 'spin_id_mapping.csv',
        'price_sensitivity': 'price_sensitivity.csv'
    }
    
    data = {}
    
    print(f"\n📁 Loading files from local directory: {directory_path}")
    
    for key, filename in files_to_load.items():
        filepath = os.path.join(directory_path, filename)
        try:
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                data[key] = df
                print(f"✅ Loaded '{filename}': {len(df)} rows")
            else:
                print(f"⚠️ File not found: {filepath}")
        except Exception as e:
            print(f"❌ Error loading '{filename}': {e}")
    
    print(f"\n✅ Loaded {len(data)}/{len(files_to_load)} files from local directory")
    return data


# Example usage
if __name__ == "__main__":
    # Method 1: Google Drive
    loader = GoogleDriveLoader(credentials_path="google_credentials.json")
    data = loader.load_all_pricing_inputs()
    
    # Method 2: Local directory (fallback)
    if data is None or len(data) == 0:
        print("\n🔄 Falling back to local directory...")
        data = load_from_local_directory("pricing_inputs")
    
    if data:
        print("\n📊 Available datasets:")
        for key, df in data.items():
            print(f"  - {key}: {len(df)} rows")
