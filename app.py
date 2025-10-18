import streamlit as st
import sys
import os

# Add services directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))

from services.google_login import (
    get_google_auth_service,
    initialize_session_state,
    clear_authentication,
    set_authentication,
    is_authenticated,
    get_current_user,
    get_user_info
)

# Page configuration
st.set_page_config(
    page_title="Authentication - Access Management Portal",
    page_icon="🔐",
    layout="centered"
)

# Hide sidebar completely
st.markdown("""
<style>
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    .stSidebar {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        display: none !important;
    }
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    .stApp > div:first-child {
        padding-left: 0 !important;
    }
    .stApp > div:first-child > div:first-child {
        padding-left: 0 !important;
    }
    /* Additional CSS to ensure sidebar is hidden */
    .css-1d391kg {
        display: none !important;
    }
    .css-1lcbmhc {
        display: none !important;
    }
    .css-17eq0hr {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
initialize_session_state()

# Check for navigation requests
if hasattr(st.session_state, 'navigate_to_forms') and st.session_state.navigate_to_forms:
    st.session_state.navigate_to_forms = False
    # Use JavaScript to navigate to forms page
    st.markdown('<script>window.location.href = "/2_forms";</script>', unsafe_allow_html=True)
    st.stop()

# Get Google Auth service
auth_service = get_google_auth_service()

# Main title
st.markdown('<h1 class="auth-title">Access Management Portal</h1>', unsafe_allow_html=True)

# Custom CSS for styling
st.markdown("""
<style>
    .auth-title {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .config-info {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 4px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Dark theme support for form fields - More specific selectors */
    .stApp .stTextInput > div > div > input,
    .stApp .stTextArea > div > div > textarea,
    .stApp .stSelectbox > div > div > select,
    .stApp .stMultiSelect > div > div > div,
    .stApp .stNumberInput > div > div > input,
    .stApp .stDateInput > div > div > input,
    .stApp .stTimeInput > div > div > input,
    .stApp .stFileUploader > div > div > input,
    .stApp input[type="text"],
    .stApp input[type="email"],
    .stApp input[type="number"],
    .stApp textarea,
    .stApp select {
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--border-color) !important;
    }
    
    /* Dark theme support for selectbox dropdown */
    .stApp .stSelectbox > div > div > div[data-baseweb="select"],
    .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div {
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
    }
    
    /* Dark theme support for multiselect */
    .stApp .stMultiSelect > div > div > div[data-baseweb="select"],
    .stApp .stMultiSelect > div > div > div[data-baseweb="select"] > div {
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
    }
    
    /* Additional dark theme support for input elements */
    .stApp div[data-testid="stTextInput"] input,
    .stApp div[data-testid="stTextArea"] textarea,
    .stApp div[data-testid="stSelectbox"] select,
    .stApp div[data-testid="stNumberInput"] input {
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--border-color) !important;
    }
    
    /* Theme-aware styling - only apply dark theme when actually in dark mode */
    [data-theme="dark"] .stApp input,
    [data-theme="dark"] .stApp textarea,
    [data-theme="dark"] .stApp select {
        background-color: #0e1117 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Theme-aware Streamlit widget styling */
    [data-theme="dark"] .stApp .stTextInput input,
    [data-theme="dark"] .stApp .stTextArea textarea,
    [data-theme="dark"] .stApp .stSelectbox select,
    [data-theme="dark"] .stApp .stNumberInput input {
        background-color: #0e1117 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Theme-aware widget container styling */
    [data-theme="dark"] .stApp [data-testid="stTextInput"] input,
    [data-theme="dark"] .stApp [data-testid="stTextArea"] textarea,
    [data-theme="dark"] .stApp [data-testid="stSelectbox"] select,
    [data-theme="dark"] .stApp [data-testid="stNumberInput"] input {
        background-color: #0e1117 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Theme-aware comprehensive input styling */
    [data-theme="dark"] .stApp input[type="text"],
    [data-theme="dark"] .stApp input[type="email"],
    [data-theme="dark"] .stApp input[type="number"],
    [data-theme="dark"] .stApp input[type="password"],
    [data-theme="dark"] .stApp textarea,
    [data-theme="dark"] .stApp select,
    [data-theme="dark"] .stApp .stTextInput input,
    [data-theme="dark"] .stApp .stTextArea textarea,
    [data-theme="dark"] .stApp .stSelectbox select,
    [data-theme="dark"] .stApp .stNumberInput input,
    [data-theme="dark"] .stApp .stDateInput input,
    [data-theme="dark"] .stApp .stTimeInput input {
        background-color: #0e1117 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Theme-aware background color override */
    [data-theme="dark"] .stApp * {
        --background-color: #0e1117 !important;
    }
    
    
    /* Theme-aware dropdown/select dark theme support */
    [data-theme="dark"] .stApp .stSelectbox > div > div > div[data-baseweb="select"],
    [data-theme="dark"] .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div,
    [data-theme="dark"] .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div > div,
    [data-theme="dark"] .stApp .stSelectbox select,
    [data-theme="dark"] .stApp .stSelectbox > div > div > select,
    [data-theme="dark"] .stApp select,
    [data-theme="dark"] .stApp .stMultiSelect > div > div > div[data-baseweb="select"],
    [data-theme="dark"] .stApp .stMultiSelect > div > div > div[data-baseweb="select"] > div,
    [data-theme="dark"] .stApp .stMultiSelect > div > div > div[data-baseweb="select"] > div > div {
        background-color: #0e1117 !important;
        background: #0e1117 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Theme-aware dropdown option styling */
    [data-theme="dark"] .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div > div[role="listbox"],
    [data-theme="dark"] .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div > div[role="listbox"] > div,
    [data-theme="dark"] .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div > div[role="listbox"] > div > div {
        background-color: #0e1117 !important;
        background: #0e1117 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Theme-aware multi-select dropdown styling */
    [data-theme="dark"] .stApp .stMultiSelect > div > div > div[data-baseweb="select"] > div > div[role="listbox"],
    [data-theme="dark"] .stApp .stMultiSelect > div > div > div[data-baseweb="select"] > div > div[role="listbox"] > div,
    [data-theme="dark"] .stApp .stMultiSelect > div > div > div[data-baseweb="select"] > div > div[role="listbox"] > div > div {
        background-color: #0e1117 !important;
        background: #0e1117 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Theme-aware dropdown arrow and container styling */
    [data-theme="dark"] .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div > div[data-baseweb="select-arrow"],
    [data-theme="dark"] .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div > div[data-baseweb="select-arrow"] > svg {
        color: #ffffff !important;
    }
    
    /* Theme-aware dropdown elements */
    [data-theme="dark"] .stApp [data-baseweb="select"],
    [data-theme="dark"] .stApp [data-baseweb="select"] > div,
    [data-theme="dark"] .stApp [data-baseweb="select"] > div > div,
    [data-theme="dark"] .stApp [data-baseweb="select"] > div > div > div {
        background-color: #0e1117 !important;
        background: #0e1117 !important;
        color: #ffffff !important;
    }
    
    /* Dark theme variables */
    [data-theme="dark"] {
        --background-color: #0e1117;
        --text-color: #ffffff;
        --border-color: #4a5568;
    }
    
    [data-theme="light"] {
        --background-color: #ffffff;
        --text-color: #262730;
        --border-color: #cccccc;
    }
    
    /* Fallback for systems without theme detection */
    @media (prefers-color-scheme: dark) {
        .stApp .stTextInput > div > div > input,
        .stApp .stTextArea > div > div > textarea,
        .stApp .stSelectbox > div > div > select,
        .stApp .stMultiSelect > div > div > div,
        .stApp .stNumberInput > div > div > input,
        .stApp .stDateInput > div > div > input,
        .stApp .stTimeInput > div > div > input,
        .stApp .stFileUploader > div > div > input,
        .stApp input[type="text"],
        .stApp input[type="email"],
        .stApp input[type="number"],
        .stApp textarea,
        .stApp select,
        .stApp div[data-testid="stTextInput"] input,
        .stApp div[data-testid="stTextArea"] textarea,
        .stApp div[data-testid="stSelectbox"] select,
        .stApp div[data-testid="stNumberInput"] input {
            background-color: #0e1117 !important;
            color: #ffffff !important;
            border: 1px solid #4a5568 !important;
        }
        
        .stApp .stSelectbox > div > div > div[data-baseweb="select"],
        .stApp .stMultiSelect > div > div > div[data-baseweb="select"],
        .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div,
        .stApp .stMultiSelect > div > div > div[data-baseweb="select"] > div,
        .stApp .stSelectbox > div > div > div[data-baseweb="select"] > div > div,
        .stApp .stMultiSelect > div > div > div[data-baseweb="select"] > div > div,
        .stApp .stSelectbox select,
        .stApp .stSelectbox > div > div > select,
        .stApp select,
        .stApp [data-baseweb="select"],
        .stApp [data-baseweb="select"] > div,
        .stApp [data-baseweb="select"] > div > div,
        .stApp [data-baseweb="select"] > div > div > div {
            background-color: #0e1117 !important;
            background: #0e1117 !important;
            color: #ffffff !important;
            border: 1px solid #4a5568 !important;
        }
    }
    
    /* Theme-aware placeholder text styling */
    [data-theme="dark"] .stApp .stTextInput > div > div > input::placeholder,
    [data-theme="dark"] .stApp .stTextArea > div > div > textarea::placeholder,
    [data-theme="dark"] .stApp input::placeholder,
    [data-theme="dark"] .stApp textarea::placeholder {
        color: #9ca3af !important;
    }
</style>
""", unsafe_allow_html=True)

# Check if user is already authenticated
if is_authenticated():
    # Display user info
    user_info = get_user_info()
    if user_info:
        st.write("**User Information:**")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Name:** {user_info.get('name', 'N/A')}")
            st.write(f"**Email:** {user_info.get('email', 'N/A')}")
        with col2:
            st.write(f"**Picture:** {user_info.get('picture', 'N/A')}")
            st.write(f"**Domain:** {user_info.get('hd', 'N/A')}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button('📊 Go to Forms'):
            # Set navigation flag in session state
            st.session_state.navigate_to_forms = True
            st.rerun()
    
    with col2:
        if st.button('🚪 Logout'):
            clear_authentication()
            st.rerun()
    
    st.markdown("---")
    st.info("You are currently logged in. You can now access the forms page.")

else:
    # Check for OAuth callback
    query_params = st.experimental_get_query_params()
    code = query_params.get('code', [None])[0] if 'code' in query_params else None
    state = query_params.get('state', [None])[0] if 'state' in query_params else None
    
    if code:
        # Handle OAuth callback
        st.info("🔄 Processing Google authentication...")
        
        # Use service to authenticate user with state
        result, error = auth_service.authenticate_user(code, state)
        
        if result:
            # Set authentication in session state
            set_authentication(result['user_info'], result['oauth_response'])
            st.success(f"✅ Welcome, {result['user_info'].get('name', result['user_info'].get('email', ''))}!")
            st.rerun()
        else:
            st.error("Please reauthenticate")
    
    # Sign in text
    st.markdown('<p style="text-align: center; color: #666; margin-bottom: 2rem;">Sign in with your Google account</p>', unsafe_allow_html=True)
    
    # Check if Google OAuth is properly configured
    if not auth_service.is_configured():
        st.markdown('<div class="config-info">', unsafe_allow_html=True)
        st.warning("⚠️ **Google OAuth not configured!**")
        st.write("To enable Google authentication, please:")
        st.write("1. Update the `config.py` file with your Google OAuth credentials")
        st.write("2. Set up a Google Cloud Project and enable OAuth 2.0")
        st.write("3. Configure the redirect URI in your Google Console")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Check for state parameter in URL (for request ID)
        query_params = st.experimental_get_query_params()
        state_param = query_params.get('state', [None])[0] if 'state' in query_params else None
        
        # Generate OAuth URL with state parameter
        if state_param:
            oauth_url = auth_service.generate_oauth_url(state=state_param)
        else:
            oauth_url = auth_service.generate_oauth_url()
        
        # Google Login Button
        if st.button("Sign in with Google", key="google_login", use_container_width=True):
            st.markdown(f'<meta http-equiv="refresh" content="0;url={oauth_url}">', unsafe_allow_html=True)
            st.info("🔄 Redirecting to Google...")
