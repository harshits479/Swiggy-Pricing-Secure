# google_drive_integration.py
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pandas as pd
import io
import os

class GoogleDriveLoader:
    def __init__(self, credentials_path=None):
        self.credentials = None
        self.service = None
        self.credentials_path = credentials_path
        
    def authenticate(self):
        """Authenticate with Google Drive using service account"""
        try:
            # Try Streamlit secrets first (for deployment)
            if "google" in st.secrets:
                credentials_dict = dict(st.secrets["google"])
                self.credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
            # Fallback to local file (for development)
            elif self.credentials_path and os.path.exists(self.credentials_path):
                self.credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
            else:
                return False
                
            self.service = build('drive', 'v3', credentials=self.credentials)
            return True
            
        except Exception as e:
            st.error(f"❌ Authentication failed: {e}")
            return False
    
    def find_folder(self, folder_name):
        """Find folder ID by name"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            if not items:
                return None
            return items[0]['id']
            
        except Exception as e:
            st.error(f"Error finding folder: {e}")
            return None
    
    def find_file_in_folder(self, folder_id, file_name):
        """Find file ID by name within a specific folder"""
        try:
            query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)'
            ).execute()
            
            items = results.get('files', [])
            if not items:
                return None
            return items[0]['id']
            
        except Exception as e:
            st.error(f"Error finding file: {e}")
            return None
    
    def download_file(self, file_id):
        """Download file content as bytes"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_buffer.seek(0)
            return file_buffer
            
        except Exception as e:
            st.error(f"Error downloading file: {e}")
            return None
    
    def load_file_by_name(self, folder_name, file_name):
        """Load CSV file from Google Drive by folder and file name"""
        try:
            # Find folder
            folder_id = self.find_folder(folder_name)
            if not folder_id:
                st.warning(f"Folder '{folder_name}' not found")
                return None
            
            # Find file
            file_id = self.find_file_in_folder(folder_id, file_name)
            if not file_id:
                st.warning(f"File '{file_name}' not found in folder '{folder_name}'")
                return None
            
            # Download file
            file_buffer = self.download_file(file_id)
            if not file_buffer:
                return None
            
            # Read as CSV
            df = pd.read_csv(file_buffer)
            return df
            
        except Exception as e:
            st.error(f"Error loading file '{file_name}': {e}")
            return None
