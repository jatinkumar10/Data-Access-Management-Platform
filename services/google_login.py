import streamlit as st
import requests
from urllib.parse import urlencode
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from config import (
        GOOGLE_SSO_CLIENT_ID, 
        GOOGLE_SSO_CLIENT_SECRET, 
        GOOGLE_SSO_REDIRECT_URI,
        GOOGLE_SSO_SCOPES,
        ALLOWED_DOMAINS
    )
except ImportError:
    # Fallback values if config file doesn't exist
    GOOGLE_SSO_CLIENT_ID = "your_google_sso_client_id_here"
    GOOGLE_SSO_CLIENT_SECRET = "your_google_sso_client_secret_here"
    GOOGLE_SSO_REDIRECT_URI = "https://access-request.data.c24mlplatform-qa.com/forms"
    GOOGLE_SSO_SCOPES = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    ALLOWED_DOMAINS = ["cars24.com", "gmail.com"]

class GoogleAuthService:
    """Service class for Google OAuth SSO authentication"""
    
    def __init__(self):
        self.client_id = GOOGLE_SSO_CLIENT_ID
        self.client_secret = GOOGLE_SSO_CLIENT_SECRET
        self.redirect_uri = GOOGLE_SSO_REDIRECT_URI
        self.scopes = GOOGLE_SSO_SCOPES
        self.allowed_domains = ALLOWED_DOMAINS
    
    def generate_oauth_url(self, state=None):
        """Generate Google OAuth URL with optional state parameter"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        # Add state parameter if provided
        if state:
            params['state'] = state
            
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    def get_user_info(self, access_token):
        """Get user information from Google"""
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(userinfo_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    def check_domain_allowed(self, email):
        """Check if user's email domain is allowed"""
        domain = email.split('@')[1] if '@' in email else ''
        return domain in self.allowed_domains
    
    def is_configured(self):
        """Check if Google OAuth SSO is properly configured"""
        return (self.client_id and 
                self.client_id != "your_google_sso_client_id_here" and
                self.client_secret and 
                self.client_secret != "your_google_sso_client_secret_here" and
                self.redirect_uri)
    
    def get_configuration_info(self):
        """Get SSO configuration information for debugging"""
        return {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scopes': self.scopes,
            'allowed_domains': self.allowed_domains,
            'is_configured': self.is_configured()
        }
    
    def authenticate_user(self, code, state=None):
        """Complete SSO authentication flow with authorization code and optional state"""
        # Exchange code for token
        token_data = self.exchange_code_for_token(code)
        if not token_data or 'access_token' not in token_data:
            return None, "Failed to exchange authorization code for token"
        
        # Get user information
        user_info = self.get_user_info(token_data['access_token'])
        if not user_info:
            return None, "Failed to retrieve user information"
        
        # Check domain
        email = user_info.get('email', '')
        if not self.check_domain_allowed(email):
            return None, f"Email domain not allowed: {email}"
        
        # Return success with state
        return {
            'user_info': user_info,
            'token_data': token_data,
            'oauth_response': {
                'authorization_code': code,
                'token_response': token_data,
                'timestamp': st.session_state.get('oauth_timestamp', 'N/A'),
                'state': state
            }
        }, None

# Global service instance
_google_auth_service = None

def get_google_auth_service():
    """Get the global Google Auth service instance"""
    global _google_auth_service
    if _google_auth_service is None:
        _google_auth_service = GoogleAuthService()
    return _google_auth_service

def initialize_session_state():
    """Initialize session state for authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'oauth_response' not in st.session_state:
        st.session_state.oauth_response = None
    if 'oauth_state' not in st.session_state:
        st.session_state.oauth_state = None

def clear_authentication():
    """Clear authentication data from session state"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.user_info = None
    st.session_state.oauth_response = None
    st.session_state.oauth_state = None

def set_authentication(user_info, oauth_response):
    """Set authentication data in session state"""
    st.session_state.authenticated = True
    st.session_state.current_user = user_info.get('email', '')
    st.session_state.user_info = user_info
    st.session_state.oauth_response = oauth_response
    
    # Store state if present in oauth_response
    if oauth_response and 'state' in oauth_response:
        st.session_state.oauth_state = oauth_response['state']

def is_authenticated():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def get_current_user():
    """Get current authenticated user"""
    return st.session_state.get('current_user')

def get_user_info():
    """Get current user info"""
    return st.session_state.get('user_info')

def get_oauth_response():
    """Get OAuth response data"""
    return st.session_state.get('oauth_response')

def get_oauth_state():
    """Get OAuth state data"""
    return st.session_state.get('oauth_state')
