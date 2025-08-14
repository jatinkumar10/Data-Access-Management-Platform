import streamlit as st
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import random
import gspread
from config import *

WORKSHEET_NAME = 'user_responses'
def get_current_url():
    """Get the current URL dynamically"""
    try:
        # Try to get the current port from Streamlit's config
        import streamlit as st
        port = st.get_option("server.port")
        if port:
            return f"http://localhost:{port}"
    except:
        pass
    
    # Fallback to default
    return DEFAULT_URL

@st.cache_resource
def get_authenticated_client():
    """Get authenticated gspread client with cached credentials"""
    try:
        creds = None
        
        # Load existing credentials
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
        
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None

def generate_request_id():
    """Generate unique request ID with timestamp and random number"""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    random_num = random.randint(REQUEST_RANDOM_MIN, REQUEST_RANDOM_MAX)
    return f"{REQUEST_PREFIX}_{timestamp}_{random_num}"

def has_pending_request(user_id):
    """Check if user has a pending request"""
    try:
        gc = get_authenticated_client()
        if not gc:
            return False
            
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        all_data = worksheet.get_all_values()
        
        for row in all_data[1:]:  # Skip header
            if row and row[0] == user_id:
                return len(row) < 6 or (len(row) >= 6 and row[5] not in [APPROVED_STATUS, REJECTED_STATUS])
        return False
    except Exception:
        return False

def save_request(data):
    """Save new request to Google Sheets"""
    try:
        gc = get_authenticated_client()
        if not gc:
            return False
            
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        worksheet.append_row(data)
        return True
    except Exception as e:
        st.error(f"Error saving request: {e}")
        return False

def update_request_status(request_id, approver_type, new_status):
    """Update request status in Google Sheets"""
    try:
        gc = get_authenticated_client()
        if not gc:
            return False
            
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        all_data = worksheet.get_all_values()
        
        if not all_data:
            return False
        
        # For user creation, status is in column F (index 5)
        # The data structure is: [Request_id, User, Manager, BU, Entity, Approval_status]
        status_col = 5  # Column F (6th column, 0-indexed = 5)
        request_id_col = 0  # Column A (1st column, 0-indexed = 0)
        
        # Find request row and update status
        for idx, row in enumerate(all_data[1:], start=2):  # Skip header, 1-indexed
            if row and len(row) > request_id_col and row[request_id_col] == request_id:
                worksheet.update_cell(idx, status_col + 1, new_status)
                return True
                
        return False
    except Exception as e:
        st.error(f"Error updating status: {e}")
        return False

def send_approval_email(user_id, manager_email, entity, bu, request_id, user_email):
    """Send approval email with action buttons"""
    base_url = get_current_url()
    approve_link = f"{base_url}?approve_id={request_id}&type=user&action=approve&u={user_id}&e={entity}&b={bu}&approver={manager_email}"
    reject_link = f"{base_url}?approve_id={request_id}&type=user&action=reject&u={user_id}&e={entity}&b={bu}&approver={manager_email}"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2c3e50;">Approval Needed: Snowflake User Creation Request</h2>
        
        <p>The user ID <strong>{user_id}</strong> has submitted a request for Snowflake user creation in:</p>
        <ul>
            <li><strong>Entity:</strong> {entity}</li>
            <li><strong>BU:</strong> {bu}</li>
            <li><strong>Request ID:</strong> {request_id}</li>
        </ul>
        
        <p><strong>Please take an action:</strong></p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{approve_link}" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block; font-weight: bold;">✅ APPROVE REQUEST</a>
            <a href="{reject_link}" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block; font-weight: bold;">❌ REJECT REQUEST</a>
        </div>
        
        <p style="font-size: 12px; color: #666; margin-top: 30px;">
            <em>Note: Clicking on either button will take you to the approval page where the action will be processed automatically.</em>
        </p>
    </body>
    </html>
    """
    
    message = MIMEMultipart("alternative")
    message["Subject"] = "Approval Needed: Snowflake User Creation Request"
    message["From"] = EMAIL_SENDER
    message["To"] = manager_email
    message["Cc"] = user_email  # Add user to CC
    
    text_part = MIMEText(f"Approval needed for user {user_id}. Please use the buttons in the email.", "plain")
    html_part = MIMEText(html_body, "html")
    
    message.attach(text_part)
    message.attach(html_part)
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, [manager_email, user_email], message.as_string())
            return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

@st.cache_data(ttl=CACHE_TTL)  # Cache for 5 minutes
def load_dropdown_data():
    """Load data for dropdown menus with caching"""
    try:
        gc = get_authenticated_client()
        if not gc:
            return {}, {}
            
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        # Load entity-BU mapping
        try:
            bu_worksheet = spreadsheet.worksheet('user_bu')
            bu_data = bu_worksheet.get_all_values()[1:]  # Skip header
            entity_bu_mapping = {}
            
            for row in bu_data:
                if len(row) >= 2 and row[0] and row[1]:
                    entity, bu = row[0], row[1]
                    if entity not in entity_bu_mapping:
                        entity_bu_mapping[entity] = []
                    entity_bu_mapping[entity].append(bu)
        except:
            entity_bu_mapping = {"CSPL": ["C2B", "B2B"], "CAPL": ["C2B", "B2B"], "CFSPL": ["C2B", "B2B"]}
        
        # Load user-manager mapping
        try:
            user_worksheet = spreadsheet.worksheet('user_manager')
            user_data = user_worksheet.get_all_values()[1:]  # Skip header
            user_manager_dict = {row[0]: row[1] for row in user_data if len(row) >= 2 and row[0]}
        except:
            user_manager_dict = {}
        
        return entity_bu_mapping, user_manager_dict
        
    except Exception:
        return {}, {}

def handle_approval_action():
    """Handle approval/rejection from email links"""
    try:
        params = st.query_params
        if 'approve_id' in params and 'type' in params and 'action' in params and 'approver' in params:
            request_id = str(params['approve_id']).strip()
            approver_type = str(params['type']).strip()
            action = str(params['action']).strip()
            user_id = str(params.get('u', '')).strip()
            entity = str(params.get('e', '')).strip()
            bu = str(params.get('b', '')).strip()
            approver_email = str(params['approver']).strip()
            
            # Get the current user's email from session state
            current_user_email = st.session_state.get('user_email', '')
            
            # Check if user is logged in
            if not current_user_email:
                st.error("❌ Please login first to approve this request.")
                return True
            
            # Check if the logged-in user is the designated approver
            if current_user_email.lower() != approver_email.lower():
                st.error("❌ You are not authorized to approve this request!")
                st.info(f"Only {approver_email} can approve this request. Please login with the correct account.")
                return True
            
            # Optional: Check if the current user is trying to approve their own request
            if current_user_email.lower() == user_id.lower():
                st.error("❌ You cannot approve or reject your own request!")
                st.info("Only designated approvers can approve or reject requests.")
                return True
            
            new_status = 'Approved' if action == 'approve' else 'Rejected'
            action_text = 'approved' if action == 'approve' else 'rejected'
            action_icon = '✅' if action == 'approve' else '❌'
            action_color = 'green' if action == 'approve' else 'red'
            
            success = update_request_status(request_id, approver_type, new_status)
            
            if success:
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; max-width: 400px; margin: 0 auto; 
                            background-color: #f8f9fa; border-radius: 10px; border: 1px solid #e9ecef;">
                    <div style="font-size: 48px; margin-bottom: 15px;">{action_icon}</div>
                    <h3 style="color: {action_color}; margin: 10px 0;">Request {action_text.title()}!</h3>
                    <p style="color: #666; margin: 5px 0; font-size: 14px;">ID: {request_id}</p>
                    <p style="color: #666; margin: 5px 0; font-size: 14px;">User: {user_id}</p>
                    <p style="color: #666; margin: 5px 0; font-size: 14px;">Entity: {entity}</p>
                    <p style="color: #666; margin: 5px 0; font-size: 14px;">BU: {bu}</p>
                    <p style="color: #999; margin: 15px 0 0 0; font-size: 12px;">You can close this tab now.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"Failed to update request {request_id}")
            
            return True
        return False
    except Exception:
        return True

def main_form():
    """Main user creation form"""
    st.title("User Creation Form")
    
    # Check if user is authenticated
    if 'user_email' not in st.session_state:
        st.error("Please login first")
        return
    
    # Get user email from session
    user_email = st.session_state.user_email
    
    # Initialize session state
    if 'selected_manager_email' not in st.session_state:
        st.session_state.selected_manager_email = ""
    
    # Load dropdown data with loading indicator
    with st.spinner("Loading form data..."):
        entity_bu_mapping, user_manager_dict = load_dropdown_data()
    
    # Generate request ID
    request_id = st.text_input("Request ID", value=generate_request_id(), disabled=True, key="request_id_user_creation")
    
    # User email (read-only, auto-filled)
    st.text_input("Email ID", value=user_email, disabled=True, key="user_email_display")
    
    # Auto-populate manager email based on user email
    manager_email = user_manager_dict.get(user_email, "")
    st.text_input("Manager Email", value=manager_email, disabled=True, key="manager_email_user_creation")
    
    # Entity and BU selection
    entity_options = ["Select Entity"] + sorted(list(entity_bu_mapping.keys()))
    selected_entity = st.selectbox("Entity", options=entity_options, key="entity_dropdown")
    
    if selected_entity != "Select Entity" and selected_entity in entity_bu_mapping:
        bu_options = ["Select Business Unit"] + sorted(entity_bu_mapping[selected_entity])
        selected_bu = st.selectbox("Business Unit (BU)", options=bu_options, key="bu_dropdown")
    else:
        bu_options = ["Select Business Unit"]
        selected_bu = st.selectbox("Business Unit (BU)", options=bu_options, disabled=True, key="bu_dropdown_disabled")
    
    # Submit form
    if st.button("Submit", key="submit_user_creation"):
        # Validation
        if not user_email:
            st.error("User email not found")
            return
        
        if not manager_email:
            st.error("Manager email not found for selected user")
            return
        
        if selected_entity == "Select Entity":
            st.error("Please select an Entity")
            return
        
        if selected_bu == "Select Business Unit":
            st.error("Please select a Business Unit")
            return
        
        # Check for pending requests
        if has_pending_request(user_email):
            st.error("You already have a pending request. Please wait for it to be processed.")
            return
        
        # Prepare and save data
        form_data = [request_id, user_email, manager_email, selected_bu, selected_entity, PENDING_STATUS]
        
        if save_request(form_data):
            # Send approval email
            email_sent = send_approval_email(user_email, manager_email, selected_entity, selected_bu, request_id, user_email) # Pass user_email as user_email
            
            if email_sent:
                st.success(f"✅ **Request Submitted Successfully!**\n\n**Request ID:** {request_id}\n**User:** {user_email}\n**Manager:** {manager_email}\n**Entity:** {selected_entity}\n**Business Unit:** {selected_bu}\n\n📧 Approval email has been sent to the manager.")
            else:
                st.warning(f"⚠️ **Request Submitted Successfully!**\n\n**Request ID:** {request_id}\n**User:** {user_email}\n**Entity:** {selected_entity}\n**Business Unit:** {selected_bu}\n\n❌ Manager email not found. Cannot send approval email.")
        else:
            st.error("Failed to save user creation request. Please try again.")

def main():
    """Main application entry point"""
    # Handle approval actions first
    if handle_approval_action():
        return
    
    # Show main form if no approval action
    main_form()

if __name__ == "__main__":
    main() 