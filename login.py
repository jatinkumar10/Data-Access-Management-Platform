import streamlit as st
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import *

def get_sheets_service():
    """Initialize and return Google Sheets service with cached credentials"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('sheets', 'v4', credentials=creds)

@st.cache_data(ttl=CACHE_TTL)
def get_user_data():
    """Fetch user data from snf_user sheet"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='snf_user'
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            return {}
        
        header = values[0]
        user_data = {}
        
        try:
            email_col = header.index('EMAIL')
            entity_col = header.index('ENTITY')
            role_col = header.index('DEFAULT_ROLE')
            
            for row in values[1:]:
                if len(row) > email_col and row[email_col].strip():
                    email = row[email_col].strip()
                    entity = row[entity_col] if entity_col < len(row) else ''
                    role = row[role_col] if role_col < len(row) else ''
                    
                    user_data[email] = {
                        'entity': entity,
                        'role': role
                    }
        except ValueError:
            st.error("Required columns not found in snf_user sheet")
            return {}
        
        return user_data
    except Exception as e:
        st.error(f"Error fetching user data: {e}")
        return {}

def verify_user(email):
    """Verify if user exists in snf_user sheet"""
    user_data = get_user_data()
    return email.strip().lower() in [user_email.lower() for user_email in user_data.keys()]

def get_user_info(email):
    """Get user information from snf_user sheet"""
    user_data = get_user_data()
    email_lower = email.strip().lower()
    
    for user_email, info in user_data.items():
        if user_email.lower() == email_lower:
            return info
    return None

def login_page():
    """Display login page"""
    st.set_page_config(
        page_title="Login - Data Access Management System",
        page_icon="🔐",
        layout="centered"
    )
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2c3e50;">🔐 Data Access Management System</h1>
            <p style="color: #7f8c8d; font-size: 18px;">Please login to continue</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form
        with st.form("login_form"):
            email = st.text_input("Email Address", placeholder="Enter your email address")
            submit_button = st.form_submit_button("Login", type="primary")
            
            if submit_button:
                if not email or not email.strip():
                    st.error("Please enter your email address")
                elif not verify_user(email):
                    st.error("❌ Email not found. Please check your email address or contact your administrator.")
                else:
                    # Store user info in session state
                    user_info = get_user_info(email)
                    st.session_state.authenticated = True
                    st.session_state.user_email = email.strip()
                    st.session_state.user_entity = user_info.get('entity', '')
                    st.session_state.user_role = user_info.get('role', '')
                    
                    st.success("✅ Login successful! Redirecting...")
                    st.rerun()
        
        # Add some styling
        st.markdown("""
        <style>
        .stForm {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #dee2e6;
        }
        </style>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    login_page() 