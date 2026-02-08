import streamlit as st

class GoogleDriveLoader:
    def __init__(self, credentials_path=None):
        self.credentials = None
        
    def authenticate(self):
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
                st.warning("⚠️ Google Drive credentials not configured")
                return False
                
            self.service = build('drive', 'v3', credentials=self.credentials)
            return True
        except Exception as e:
            st.error(f"❌ Authentication failed: {e}")
            return False
