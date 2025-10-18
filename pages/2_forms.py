import streamlit as st
import sys
import os

# Add components directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'components'))

# Add parent directory to path to import services
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Add services directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

# Add context directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'context'))

from google_login import (
    get_google_auth_service,
    initialize_session_state,
    clear_authentication,
    set_authentication,
    is_authenticated,
    get_current_user,
    get_user_info,
    get_oauth_state
)

from context.filecontext import (
    get_request_details,
    is_user_authorized_for_request,
    update_user_creation_approval_form,
    update_table_column_approval_form,
    update_multi_approver_status_form,
    send_user_creation_approval_email,
    send_table_column_approval_email,
    send_multi_approver_notification_email
)

from horizontal_selector import horizontal_selector_three_items
from user_context import get_user_context, update_user_context_from_session

# Check for redirect requests
if hasattr(st.session_state, 'redirect_to_main') and st.session_state.redirect_to_main:
    st.session_state.redirect_to_main = False
    # Use JavaScript to navigate to main page
    st.markdown('<script>window.location.href = "/";</script>', unsafe_allow_html=True)
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Form Components",
    page_icon="🎯",
    layout="centered"
)

# CSS to set max-width to 800px and hide sidebar
st.markdown("""
<style>
    /* Set max-width to 1200px */
    .main .block-container {
        max-width: 1200px;
    }
    
    /* Reduce default spacing between elements */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Reduce spacing between form elements */
    .stForm > div {
        margin-bottom: 0.5rem !important;
    }
    
    /* Reduce spacing between text elements */
    .stMarkdown {
        margin-bottom: 0.25rem !important;
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
    
    /* Hide sidebar completely */
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

# Get Google Auth service
auth_service = get_google_auth_service()

# Check for OAuth callback at the very top
query_params = st.experimental_get_query_params()
code = query_params.get('code', [None])[0] if 'code' in query_params else None

if code:
    # Handle OAuth callback silently
    state = query_params.get('state', [None])[0] if 'state' in query_params else None
    result, error = auth_service.authenticate_user(code, state)
    
    if result:
        # Set authentication in session state
        set_authentication(result['user_info'], result['oauth_response'])
        
        # Update user context with the new user information
        user_context = get_user_context()
        user_context.set_user_info(result['user_info'], result['oauth_response'])
        
        # Redirect to clean page
        st.rerun()



# Check authentication status
if is_authenticated():
    # Update user context from session state
    update_user_context_from_session()
    
    # Check for OAuth state (request ID) and show approval interface if present
    oauth_state = get_oauth_state()
    
    # Check if user came through email URL (has request ID in state)
    if oauth_state and oauth_state.strip():  # Show approval interface if state is present and not empty
        # Store the request ID for use in approval buttons
        request_id = oauth_state
        
        # Get current user email for authorization check
        current_user_email = get_current_user()
        
        if not current_user_email:
            st.error("❌ **Authentication Error**")
            st.info("Unable to determine current user. Please log in again.")
            st.stop()
        
        # Check authorization for this request
        authorization_result = is_user_authorized_for_request(oauth_state, current_user_email)
        
        if not authorization_result['authorized']:
            # User is not authorized - show clear message
            st.error("❌ **Access Denied**")
            st.warning(authorization_result['message'])
            st.info("🔗 **Note:** This approval link is not valid for your account or the request has already been processed.")
            st.info("💡 **Tip:** If you need to access the portal, please use the main application URL.")
            
            # Clear the OAuth state
            st.session_state.oauth_state = None
            
            # Add a button to go to main portal
            if st.button("🏠 Go to Main Portal", key="go_to_main", use_container_width=True):
                st.session_state.redirect_to_main = True
                st.rerun()
            
            st.stop()
        
        # User is authorized - show approval interface
        request_details = authorization_result['request_details']
        approver_type = authorization_result['approver_type']
        approver_types = authorization_result.get('approver_types', [approver_type])
        
        st.markdown('<h1 style="text-align: center; color: #1f77b4; margin-bottom: 0.5rem; font-size: 1.8rem; font-weight: bold;">Request Approval</h1>', unsafe_allow_html=True)
        
        # Display request information
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 2px solid #667eea; border-radius: 10px; padding: 10px; margin: 5px 0;">
            <div style="font-size: 1.3rem; font-weight: bold; color: #2c3e50; text-align: center; margin-bottom: 5px;">Request ID: {oauth_state}</div>
        </div>
        """, unsafe_allow_html=True)
        

        
        # Display request details based on type
        st.info(f"📋 **Request Details**")
        st.write(f"**Request ID:** {oauth_state}")
        st.write(f"**Request Type:** {request_details.get('request_type', 'N/A')}")
        st.write(f"**Status:** {request_details.get('approval_status', 'Pending')}")
        # Format the submitted date properly
        created_at = request_details.get('created_at', 'N/A')
        if created_at and created_at != 'N/A':
            try:
                # Try to parse and format the date
                from datetime import datetime
                if isinstance(created_at, str):
                    # Handle different possible date formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y']:
                        try:
                            dt = datetime.strptime(created_at, fmt)
                            formatted_date = dt.strftime('%B %d, %Y at %I:%M %p')
                            break
                        except ValueError:
                            continue
                    else:
                        formatted_date = created_at  # Use original if parsing fails
                else:
                    formatted_date = str(created_at)
            except Exception:
                formatted_date = str(created_at)
        else:
            formatted_date = 'N/A'
        
        st.write(f"**Submitted:** {formatted_date}")
        st.write(f"**Entity:** {request_details.get('entity', 'N/A')}")
        st.write(f"**Business Unit:** {request_details.get('business_unit', 'N/A')}")
        
        # Show additional details based on request type
        if request_details['sheet_type'] == 'user_responses':
            st.write(f"**User Email:** {request_details.get('user_email', 'N/A')}")
        elif request_details['sheet_type'] == 'gsheet_unmasking_responses':
            # GSheet Unmasking request details
            st.write(f"**Spreadsheet ID:** {request_details.get('spreadsheet_id', 'N/A')}")
            st.write(f"**Named Range:** {request_details.get('named_range', 'N/A')}")
            st.write(f"**Who Has Access:** {request_details.get('who_has_access', 'N/A')}")
            st.write(f"**End User Description:** {request_details.get('end_user_description', 'N/A')}")
            st.write(f"**Use Case:** {request_details.get('use_case', 'N/A')}")
            st.write(f"**Objective:** {request_details.get('objective', 'N/A')}")
            st.write(f"**Validity:** {request_details.get('validity', 'N/A')} days")
            st.write(f"**User Email:** {request_details.get('user_email', 'N/A')}")
            
            # Show L1-L5 approval status with approver names for GSheet requests
            l1_approver = request_details.get('l1_approver', 'N/A')
            l2_approver = request_details.get('l2_approver', 'N/A')
            l3_approver = request_details.get('l3_approver', 'N/A')
            l4_approver = request_details.get('l4_approver', 'N/A')
            l5_approver = request_details.get('l5_approver', 'N/A')
            
            st.write(f"**L1 Approver ({l1_approver}):** {request_details.get('l1_approver_status', 'Pending')}")
            st.write(f"**L2 Approver ({l2_approver}):** {request_details.get('l2_approver_status', 'Pending')}")
            st.write(f"**L3 Approver ({l3_approver}):** {request_details.get('l3_approver_status', 'Pending')}")
            st.write(f"**L4 Approver ({l4_approver}):** {request_details.get('l4_approver_status', 'Pending')}")
            st.write(f"**L5 Approver ({l5_approver}):** {request_details.get('l5_approver_status', 'Pending')}")
        elif request_details['sheet_type'] == 'responses':
            st.write(f"**Database:** {request_details.get('database', 'N/A')}")
            st.write(f"**Schema:** {request_details.get('schema', 'N/A')}")
            st.write(f"**Table:** {request_details.get('table', 'N/A')}")
            if request_details.get('column'):
                st.write(f"**Column:** {request_details.get('column', 'N/A')}")
            
            # Show reason fields based on request type
            request_type = request_details.get('request_type', '')
            if request_type == 'Column request':
                # For column unhashing requests, show both reason category and objective
                st.write(f"**Reason Category:** {request_details.get('reason_category', 'N/A')}")
                st.write(f"**Objective:** {request_details.get('objective', request_details.get('reason', 'N/A'))}")
            else:
                # For table requests, show objective instead of reason
                st.write(f"**Objective:** {request_details.get('objective', request_details.get('reason', 'N/A'))}")
            
            st.write(f"**Validity:** {request_details.get('validity', 'N/A')} days")
            st.write(f"**User Email:** {request_details.get('user_email', 'N/A')}")
            
            # Show L1-L5 approval status with approver names for table/column requests
            # l1_approver = request_details.get('l1_approver', 'N/A')
            # l2_approver = request_details.get('l2_approver', 'N/A')
            # l3_approver = request_details.get('l3_approver', 'N/A')
            # l4_approver = request_details.get('l4_approver', 'N/A')
            # l5_approver = request_details.get('l5_approver', 'N/A')
            
            # st.write(f"**L1 Approver ({l1_approver}):** {request_details.get('l1_approver_status', 'Pending')}")
            # st.write(f"**L2 Approver ({l2_approver}):** {request_details.get('l2_approver_status', 'Pending')}")
            # st.write(f"**L3 Approver ({l3_approver}):** {request_details.get('l3_approver_status', 'Pending')}")
            # st.write(f"**L4 Approver ({l4_approver}):** {request_details.get('l4_approver_status', 'Pending')}")
            # st.write(f"**L5 Approver ({l5_approver}):** {request_details.get('l5_approver_status', 'Pending')}")


            approver_levels = [
                ('L1', request_details.get('l1_approver', ''), request_details.get('l1_approver_status', 'Pending')),
                ('L2', request_details.get('l2_approver', ''), request_details.get('l2_approver_status', 'Pending')),
                ('L3', request_details.get('l3_approver', ''), request_details.get('l3_approver_status', 'Pending')),
                ('L4', request_details.get('l4_approver', ''), request_details.get('l4_approver_status', 'Pending')),
                ('L5', request_details.get('l5_approver', ''), request_details.get('l5_approver_status', 'Pending'))
            ]
            
            # Display only levels with actual approvers (non-empty email addresses)
            for level, approver_email, status in approver_levels:
                if approver_email and approver_email.strip() and approver_email.lower() not in ['n/a', 'none', '']:
                    st.write(f"**{level} Approver ({approver_email}):** {status}")
        # Approval buttons
        st.markdown('<div style="text-align: center; margin: 8px 0;">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("✅ Approve", key="approve_btn", use_container_width=True, type="primary"):
                # Get current user email
                current_user_email = get_current_user()
                
                if not current_user_email:
                    st.error("❌ **Authentication Error**")
                    st.info("Unable to determine current user. Please log in again.")
                    st.stop()
                
                # Update approval status based on request type and approver type
                success = False
                
                if request_details['sheet_type'] == 'user_responses':
                    # User creation request - update Approval_status and Approval_ts
                    success = update_user_creation_approval_form(oauth_state, current_user_email, "Approved")
                elif request_details['sheet_type'] == 'gsheet_unmasking_responses':
                    # GSheet unmasking request - use sequential approval system
                    from context.filecontext import update_gsheet_unmasking_approval
                    success = update_gsheet_unmasking_approval(oauth_state, current_user_email, "Approved")
                elif request_details['sheet_type'] == 'responses':
                    # Table/Column request - update based on approver type
                    if len(approver_types) > 1:
                        # Multi-approver: update both RM and Data approver status
                        success = update_multi_approver_status_form(oauth_state, current_user_email, "Approved")
                    else:
                        # Single approver: update only the relevant status
                        success = update_table_column_approval_form(oauth_state, current_user_email, approver_type, "Approved")
                
                if success:
                    # Clear the OAuth state first
                    st.session_state.oauth_state = None
                    
                    # Show simple success message
                    st.success(f"✅ **Request Approved Successfully!**")
                    
                    # Add a button to go back to forms
                    if st.button("🔙 Back to Forms", key="back_after_approve", use_container_width=True):
                        st.rerun()
                    
                    st.stop()
                else:
                    st.error("❌ Failed to update approval status. Please try again.")
        
        with col2:
            if st.button("❌ Reject", key="reject_btn", use_container_width=True, type="secondary"):
                # Get current user email
                current_user_email = get_current_user()
                
                if not current_user_email:
                    st.error("❌ **Authentication Error**")
                    st.info("Unable to determine current user. Please log in again.")
                    st.stop()
                
                # Update rejection status based on request type and approver type
                success = False
                
                if request_details['sheet_type'] == 'user_responses':
                    # User creation request - update Approval_status and Approval_ts
                    success = update_user_creation_approval_form(oauth_state, current_user_email, "Rejected")
                elif request_details['sheet_type'] == 'gsheet_unmasking_responses':
                    # GSheet unmasking request - use sequential approval system
                    from context.filecontext import update_gsheet_unmasking_approval
                    success = update_gsheet_unmasking_approval(oauth_state, current_user_email, "Rejected")
                elif request_details['sheet_type'] == 'responses':
                    # Table/Column request - update based on approver type
                    if len(approver_types) > 1:
                        # Multi-approver: update both RM and Data approver status
                        success = update_multi_approver_status_form(oauth_state, current_user_email, "Rejected")
                    else:
                        # Single approver: update only the relevant status
                        success = update_table_column_approval_form(oauth_state, current_user_email, approver_type, "Rejected")
                
                if success:
                    # Clear the OAuth state first
                    st.session_state.oauth_state = None
                    
                    # Show simple rejection message
                    st.error(f"❌ **Request Rejected Successfully!**")
                    
                    # Add a button to go back to forms
                    if st.button("🔙 Back to Forms", key="back_after_reject", use_container_width=True):
                        st.rerun()
                    
                    st.stop()
                else:
                    st.error("❌ Failed to update rejection status. Please try again.")
        
        with col3:
            if st.button("🔙 Back to Forms", key="back_btn", use_container_width=True):
                # Clear the OAuth state and rerun to go back to forms
                st.session_state.oauth_state = None
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    else:
        # No OAuth state found - show normal forms interface
        
        # Three-Item Horizontal Selector with Context-Driven Rendering
        selected_nav = horizontal_selector_three_items(
            title="",
            key="nav_selector"
        )
    
        

else:
    # User is not authenticated - redirect to base URL
    st.warning("🔐 **Authentication Required**")
    st.info("You need to sign in with Google to use the form components. Redirecting to home page...")
    
    # Redirect to main app
    st.session_state.redirect_to_main = True
    st.rerun()
