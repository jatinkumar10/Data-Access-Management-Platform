"""
OAuth Credentials Service
Handles retrieval of OAuth credentials from imported JSON file
"""

import sys
sys.path.append('/home/ubuntu/BI')

try:
    import STREAMLIT_ACCESS_REQUEST_QA_OAUTH_JSON
    OAUTH_CREDS_QA = STREAMLIT_ACCESS_REQUEST_QA_OAUTH_JSON.OAUTH_CREDS_QA
except ImportError as e:
    print(f"❌ Error importing OAuth credentials: {e}")
    OAUTH_CREDS_QA = {}


class SecretManagerService:
    """Service to handle OAuth credentials operations"""
    
    def __init__(self, project_id: str = "941299108492"):
        self.project_id = project_id
    
    def get_oauth_credentials(self):
        """Get OAuth credentials from imported JSON file"""
        try:
            # Extract credentials from the 'web' section
            web_creds = OAUTH_CREDS_QA.get('web', {})
            
            # Get redirect URI from the list (first one)
            redirect_uris = web_creds.get('redirect_uris', [])
            redirect_uri = redirect_uris[0] if redirect_uris else 'https://access-request.data.c24mlplatform-qa.com/forms'
            
            # Build credentials dict with expected keys
            creds = {
                'client_id': web_creds.get('client_id', ''),
                'client_secret': web_creds.get('client_secret', ''),
                'redirect_uri': redirect_uri,
                'scopes': [
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile"
                ]
            }
            
            return creds
        except Exception as e:
            print(f"❌ Error accessing OAuth credentials: {e}")
            return {}
    
    def get_google_sso_config(self):
        """Get Google SSO configuration"""
        oauth_creds = self.get_oauth_credentials()
        
        if oauth_creds:
            return {
                "client_id": oauth_creds.get("client_id", ""),
                "client_secret": oauth_creds.get("client_secret", ""),
                "redirect_uri": oauth_creds.get("redirect_uri", "https://access-request.data.c24mlplatform-qa.com/forms"),
                "scopes": oauth_creds.get("scopes", [
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile"
                ])
            }
        else:
            return {
                "client_id": "",
                "client_secret": "",
                "redirect_uri": "https://access-request.data.c24mlplatform-qa.com/forms",
                "scopes": [
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile"
                ]
            }


# Global instance
secret_manager_service = SecretManagerService()