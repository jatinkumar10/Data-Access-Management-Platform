import streamlit as st
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import random
from config import *

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

@st.cache_resource(ttl=CACHE_TTL)
def get_sheets_service():
    """Initialize Google Sheets service with cached credentials"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server()
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('sheets', 'v4', credentials=creds)

@st.cache_data(ttl=CACHE_TTL)
def fetch_sheet_data():
    """Fetch all required data from Google Sheets"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Get all tabs first
        result = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
        tab_names = [sheet['properties']['title'] for sheet in result.get('sheets', [])]
        
        # Find the correct tab for column data
        column_tab = next((name for name in ['masked_columns', 'unhashing_columns', 'columns'] 
                          if name in tab_names), None)
        
        if not column_tab:
            st.error("Column data tab not found")
            return [], [], [], [], []
        
        # Fetch all data in one batch
        ranges = ['snf_user', 'rm approvers', 'data approvers', column_tab]
        result = sheet.values().batchGet(spreadsheetId=SPREADSHEET_ID, ranges=ranges).execute()
        value_ranges = result.get('valueRanges', [])
        
        # Process data
        users = process_user_data(value_ranges[0] if len(value_ranges) > 0 else None)
        rm_approvers = process_rm_approvers(value_ranges[1] if len(value_ranges) > 1 else None)
        data_approvers = process_data_approvers(value_ranges[2] if len(value_ranges) > 2 else None)
        table_data, column_data = process_column_data(value_ranges[3] if len(value_ranges) > 3 else None)
        
        return users, rm_approvers, data_approvers, table_data, column_data
        
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return [], [], [], [], []

def process_user_data(value_range):
    """Process user data from sheet"""
    if not value_range or not value_range.get('values'):
        return []
    
    values = value_range['values']
    if len(values) < 2:
        return []
    
    header = values[0]
    try:
        entity_col = header.index('ENTITY')
        email_col = header.index('EMAIL')
        role_col = header.index('DEFAULT_ROLE')
        
        users = []
        for row in values[1:]:
            if len(row) > max(entity_col, email_col, role_col):
                entity = row[entity_col] if entity_col < len(row) else ''
                email = row[email_col] if email_col < len(row) else ''
                role = row[role_col] if role_col < len(row) else ''
                # Only add if email is not blank
                if email and email.strip():
                    users.append({
                        'entity': entity,
                        'email': email,
                        'role': role
                    })
        return users
    except ValueError:
        return []

def process_rm_approvers(value_range):
    """Process RM approvers data from sheet"""
    if not value_range or not value_range.get('values'):
        return []
    
    values = value_range['values']
    if len(values) < 2:
        return []
    
    header = values[0]
    try:
        user_email_col = header.index('User_Email')
        approver_col = header.index('Approver')
        
        rm_approvers = []
        for row in values[1:]:
            if len(row) > max(user_email_col, approver_col):
                user_email = row[user_email_col] if user_email_col < len(row) else ''
                approver = row[approver_col] if approver_col < len(row) else ''
                # Only add if both user_email and approver are not blank
                if user_email and user_email.strip() and approver and approver.strip():
                    rm_approvers.append({
                        'user_email': user_email,
                        'approver': approver
                    })
        return rm_approvers
    except ValueError:
        return []

def process_data_approvers(value_range):
    """Process data approvers from sheet"""
    if not value_range or not value_range.get('values'):
        return []
    
    values = value_range['values']
    if len(values) < 2:
        return []
    
    header = values[0]
    try:
        database_col = header.index('Database')
        approver_col = header.index('Approver')
        
        data_approvers = []
        for row in values[1:]:
            if len(row) > max(database_col, approver_col):
                database = row[database_col] if database_col < len(row) else ''
                approver = row[approver_col] if approver_col < len(row) else ''
                # Only add if both database and approver are not blank
                if database and database.strip() and approver and approver.strip():
                    data_approvers.append({
                        'database': database,
                        'approver': approver
                    })
        return data_approvers
    except ValueError:
        return []

def process_column_data(value_range):
    """Process column data and extract both table and column info"""
    if not value_range or not value_range.get('values'):
        return [], []
    
    values = value_range['values']
    if len(values) < 2:
        return [], []
    
    header = values[0]
    try:
        object_source_col = header.index('OBJECT SOURCE')
        database_col = header.index('DATABASE_NAME')
        schema_col = header.index('SCHEMA_NAME')
        table_col = header.index('TABLE_NAME')
        column_col = header.index('COLUMN_NAME')
        policy_col = header.index('POLICY_NAME')
        
        table_data = []
        column_data = []
        unique_tables = set()
        
        for row in values[1:]:
            if len(row) <= max(object_source_col, database_col, schema_col, table_col, column_col, policy_col):
                continue
            
            object_source = row[object_source_col] if object_source_col < len(row) else ''
            database = row[database_col] if database_col < len(row) else ''
            schema = row[schema_col] if schema_col < len(row) else ''
            table = row[table_col] if table_col < len(row) else ''
            column = row[column_col] if column_col < len(row) else ''
            policy = row[policy_col] if policy_col < len(row) else ''
            
            # Only process if all required fields are not blank
            if (object_source and object_source.strip() and 
                database and database.strip() and 
                schema and schema.strip() and 
                table and table.strip()):
                
                # Extract table info (unique combinations)
                table_key = (object_source, database, schema, table)
                if table_key not in unique_tables:
                    unique_tables.add(table_key)
                    table_data.append({
                        'object_source': object_source,
                        'database': database,
                        'schema': schema,
                        'table': table
                    })
                
                # Extract column info (only if column is not blank)
                if column and column.strip():
                    column_data.append({
                        'entity': object_source,
                        'database': database,
                        'schema': schema,
                        'table': table,
                        'column': column,
                        'policy': policy
                    })
        
        return table_data, column_data
        
    except ValueError:
        return [], []

def generate_request_id():
    """Generate unique request ID"""
    now = datetime.datetime.now()
    return f"{REQUEST_PREFIX}_{now.strftime('%Y%m%d_%H%M%S')}_{random.randint(REQUEST_RANDOM_MIN, REQUEST_RANDOM_MAX)}"

def save_request(data):
    """Save request to Google Sheets"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Add approval status columns
        data_with_status = data + [PENDING_STATUS, PENDING_STATUS]
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='responses',
            valueInputOption="RAW",
            body={"values": [data_with_status]}
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error saving request: {e}")
        return False

def send_approval_emails(request_id, user_name, entity, database, schema, table, columns, rm_approver, data_approver, user_email):
    """Send approval emails to RM and Data approvers"""
    subject = "Approval Needed: Column Access Request"
    
    def create_email_content(approver_type, approver_email):
        """Create email content with correct approval links for each approver type"""
        approver_title = "RM Approver" if approver_type == 'rm' else "Data Approver"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2c3e50;">Column Access Request - {approver_title} Approval Required</h2>
            <p>The user <strong>{user_name}</strong> has submitted a column access request:</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #007bff;">Request Details:</h3>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li><strong>Request ID:</strong> {request_id}</li>
                    <li><strong>Entity:</strong> {entity}</li>
                    <li><strong>Database:</strong> {database}</li>
                    <li><strong>Schema:</strong> {schema}</li>
                    <li><strong>Table:</strong> {table}</li>
                    <li><strong>Columns:</strong> {columns}</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href='{get_current_url()}?approve_id={request_id}&type={approver_type}&action=approve&approver={approver_email}' 
                   style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block; font-weight: bold;">
                   ✅ APPROVE
                </a>
                <a href='{get_current_url()}?approve_id={request_id}&type={approver_type}&action=reject&approver={approver_email}' 
                   style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block; font-weight: bold;">
                   ❌ REJECT
                </a>
            </div>
        </body>
        </html>
        """
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            
            # Send to both approvers with different email content
            for approver_email, approver_type in [(rm_approver, 'rm'), (data_approver, 'data')]:
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = EMAIL_SENDER
                message["To"] = approver_email
                message["Cc"] = user_email  # Add user to CC
                message.attach(MIMEText(create_email_content(approver_type, approver_email), "html"))
                server.sendmail(EMAIL_SENDER, [approver_email, user_email], message.as_string())
        
        return True, None
    except Exception as e:
        return False, str(e)

def update_approval_status(request_id, approver_type, new_status):
    """Update approval status in Google Sheets"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='responses').execute()
        values = result.get('values', [])
        
        if not values:
            return False
        
        header = values[0]
        try:
            reqid_col = header.index('REQUEST_ID')
            rm_col = header.index('RM_APPROVER_STATUS') 
            data_col = header.index('DATA_APPROVER_STATUS')
        except ValueError:
            return False
        
        # Find row to update
        for idx, row in enumerate(values[1:], start=2):
            if len(row) > reqid_col and row[reqid_col] == request_id:
                update_col_index = rm_col if approver_type == 'rm' else data_col
                update_col_letter = chr(ord('A') + update_col_index)
                range_to_update = f"responses!{update_col_letter}{idx}"
                
                sheet.values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=range_to_update,
                    valueInputOption="RAW",
                    body={"values": [[new_status]]}
                ).execute()
                return True
        
        return False
        
    except Exception:
        return False

def handle_approval_request():
    """Handle approval from URL parameters"""
    try:
        params = st.query_params
        if 'approve_id' in params and 'type' in params and 'action' in params and 'approver' in params:
            request_id = str(params['approve_id']).strip()
            approver_type = str(params['type']).strip()
            action = str(params['action']).strip()
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
            
            new_status = 'Approved' if action == 'approve' else 'Rejected'
            action_text = 'approved' if action == 'approve' else 'rejected'
            action_icon = '✅' if action == 'approve' else '❌'
            action_color = 'green' if action == 'approve' else 'red'
            
            success = update_approval_status(request_id, approver_type, new_status)
            
            if success:
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; max-width: 400px; margin: 0 auto; 
                            background-color: #f8f9fa; border-radius: 10px; border: 1px solid #e9ecef;">
                    <div style="font-size: 48px; margin-bottom: 15px;">{action_icon}</div>
                    <h3 style="color: {action_color}; margin: 10px 0;">Request {action_text.title()}!</h3>
                    <p style="color: #666; margin: 5px 0; font-size: 14px;">ID: {request_id}</p>
                    <p style="color: #999; margin: 15px 0 0 0; font-size: 12px;">You can close this tab now.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"Failed to update request {request_id}")
            
            return True
        return False
    except Exception:
        return True

def initialize_session_state():
    """Initialize session state variables"""
    defaults = {
        'selected_email': "Select your email ID",
        'user_name': "", 'email': "", 'entity': "", 'default_role': "",
        'rm_approver': "", 'data_approver': "", 'requesting_for_option': "Self",
        'selected_object_source': "Select Object Source",
        'selected_database': "Select Database",
        'selected_schema': "Select Schema",
        'selected_table': "Select Table"
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def main():
    """Main application"""
    # st.set_page_config(page_title="Column Access Request Form", page_icon="📋")
    st.title("Column Access Request Form")
    
    # Check if user is authenticated
    if 'user_email' not in st.session_state:
        st.error("Please login first")
        return
    
    # Handle approval first
    if handle_approval_request():
        return
    
    # Get user email from session
    user_email = st.session_state.user_email
    
    # Initialize session state
    initialize_session_state()
    
    # Fetch data
    with st.spinner("Loading data..."):
        users, rm_approvers, data_approvers, table_data, column_data = fetch_sheet_data()
    
    if not users:
        st.error("Unable to load user data. Please check your connection.")
        return
    
    # Form fields
    request_id = st.text_input("Request ID", value=generate_request_id(), disabled=True, key="request_id_unhashing")
    
    # Email field (read-only, auto-filled)
    st.text_input("Email ID", value=user_email, disabled=True, key="email_display_unhashing")
    
    # Auto-populate user info based on session email
    selected_user = next((user for user in users if user['email'] == user_email), None)
    if selected_user:
        st.session_state.user_name = selected_user['email'].split('@')[0]
        st.session_state.email = selected_user['email']
        st.session_state.entity = selected_user['entity']
        st.session_state.default_role = selected_user['role']
        
        # Auto-populate RM approver
        rm_approver_entry = next((r for r in rm_approvers if r['user_email'] == user_email), None)
        st.session_state.rm_approver = rm_approver_entry['approver'] if rm_approver_entry else ""
    
    # User fields
    user_name = st.text_input("User Name", value=st.session_state.user_name, disabled=True, key="user_name_unhashing")
    entity = st.text_input("Entity", value=st.session_state.entity, disabled=True, key="entity_unhashing")
    
    # Hidden fields for response (not shown in UI)
    email = st.session_state.email
    default_role = st.session_state.default_role
    
    # Database selection
    object_source_options = ["Select Object Source", "CSPL", "CAPL", "CFSPL"]
    selected_object_source = st.selectbox("Object Source", options=object_source_options, key="object_source_dropdown_unhashing")
    
    if selected_object_source != st.session_state.selected_object_source:
        st.session_state.selected_object_source = selected_object_source
        st.session_state.selected_database = "Select Database"
        st.session_state.selected_schema = "Select Schema"
        st.session_state.selected_table = "Select Table"
    
    # Database dropdown
    database_options = ["Select Database"]
    if selected_object_source != "Select Object Source" and table_data:
        filtered_databases = set()
        for table in table_data:
            if table['object_source'] == selected_object_source:
                filtered_databases.add(table['database'])
        database_options.extend(sorted(filtered_databases))
    
    selected_database = st.selectbox("Database", options=database_options, key="database_dropdown_unhashing")
    
    if selected_database != st.session_state.selected_database:
        st.session_state.selected_database = selected_database
        st.session_state.selected_schema = "Select Schema"
        st.session_state.selected_table = "Select Table"
        
        # Auto-populate data approver
        data_approver_entry = next((d for d in data_approvers if d['database'] == selected_database), None)
        st.session_state.data_approver = data_approver_entry['approver'] if data_approver_entry else ""
    
    # Schema dropdown
    schema_options = ["Select Schema"]
    if selected_database != "Select Database" and table_data:
        filtered_schemas = set()
        for table in table_data:
            if (table['object_source'] == selected_object_source and 
                table['database'] == selected_database):
                filtered_schemas.add(table['schema'])
        schema_options.extend(sorted(filtered_schemas))
    
    selected_schema = st.selectbox("Schema", options=schema_options, key="schema_dropdown_unhashing")
    
    if selected_schema != st.session_state.selected_schema:
        st.session_state.selected_schema = selected_schema
        st.session_state.selected_table = "Select Table"
    
    # Table dropdown
    table_options = ["Select Table"]
    if selected_schema != "Select Schema" and table_data:
        filtered_tables = []
        for table in table_data:
            if (table['object_source'] == selected_object_source and 
                table['database'] == selected_database and 
                table['schema'] == selected_schema):
                filtered_tables.append(table['table'])
        table_options.extend(sorted(filtered_tables))
    
    selected_table = st.selectbox("Table", options=table_options, key="table_dropdown_unhashing")
    
    if selected_table != st.session_state.selected_table:
        st.session_state.selected_table = selected_table
    
    # Column selection
    column_select_option = st.radio("Column Selection:", ["Select Columns", "All Columns"], key="column_selection_radio_unhashing")
    
    selected_columns = []
    columns = ""
    
    if column_select_option == "Select Columns":
        column_options = []
        if selected_table != "Select Table" and column_data:
            filtered_columns = []
            for column in column_data:
                if (column['database'] == selected_database and 
                    column['schema'] == selected_schema and 
                    column['table'] == selected_table):
                    filtered_columns.append(column['column'])
            column_options = sorted(filtered_columns)
        
        selected_columns = st.multiselect("Column(s)", options=column_options, key="columns_multiselect_unhashing")
        
        if selected_columns:
            st.markdown("**Selected Columns:**")
            for col in selected_columns:
                st.code(col)
            columns = ", ".join(selected_columns)
        else:
            columns = ""
    elif column_select_option == "All Columns":
        columns = "ALL"
        st.info("All columns are selected for the chosen table.")
    
    # Requesting For
    requesting_for_option = st.radio("Requesting For:", ["Self", "Generic User", "Generic Role"], key="requesting_for_radio_unhashing")
    
    if requesting_for_option != st.session_state.requesting_for_option:
        st.session_state.requesting_for_option = requesting_for_option
    
    if st.session_state.requesting_for_option == "Self":
        requesting_for = st.text_input("Requesting For", value=st.session_state.email, disabled=True, key="requesting_for_unhashing")
    elif st.session_state.requesting_for_option == "Generic User":
        if st.session_state.entity in ["CSPL", "CAPL", "CFSPL"]:
            # Fetch generic users for the user's entity
            generic_users = []
            try:
                service = get_sheets_service()
                sheet = service.spreadsheets()
                result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='generic roles/users').execute()
                values = result.get('values', [])
                if len(values) > 1:
                    header = values[0]
                    try:
                        entity_col = header.index('entity')
                        generic_user_col = header.index('generic_users')
                        for row in values[1:]:
                            if len(row) > max(entity_col, generic_user_col) and row[entity_col] == st.session_state.entity:
                                generic_user = row[generic_user_col] if generic_user_col < len(row) else ''
                                if generic_user and generic_user.strip():
                                    generic_users.append(generic_user)
                    except ValueError:
                        pass
            except Exception:
                pass
            
            if generic_users:
                requesting_for = st.selectbox(f"Select {st.session_state.entity} Generic User", options=["Select Generic User"] + generic_users, key="generic_user_dropdown_unhashing")
                if requesting_for == "Select Generic User":
                    requesting_for = ""
            else:
                requesting_for = st.text_input(f"Generic User (No {st.session_state.entity} users found)", key="generic_user_text_unhashing")
        else:
            requesting_for = st.text_input("Generic User (Only available for CSPL, CAPL, and CFSPL entities)", key="generic_user_text_unhashing")
    elif st.session_state.requesting_for_option == "Generic Role":
        if st.session_state.entity in ["CSPL", "CAPL", "CFSPL"]:
            # Fetch generic roles for the user's entity
            generic_roles = []
            try:
                service = get_sheets_service()
                sheet = service.spreadsheets()
                result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='generic roles/users').execute()
                values = result.get('values', [])
                if len(values) > 1:
                    header = values[0]
                    try:
                        entity_col = header.index('entity')
                        generic_role_col = header.index('generic_roles')
                        for row in values[1:]:
                            if len(row) > max(entity_col, generic_role_col) and row[entity_col] == st.session_state.entity:
                                generic_role = row[generic_role_col] if generic_role_col < len(row) else ''
                                if generic_role and generic_role.strip():
                                    generic_roles.append(generic_role)
                    except ValueError:
                        pass
            except Exception:
                pass
            
            if generic_roles:
                requesting_for = st.selectbox(f"Select {st.session_state.entity} Generic Role", options=["Select Generic Role"] + generic_roles, key="generic_role_dropdown_unhashing")
                if requesting_for == "Select Generic Role":
                    requesting_for = ""
            else:
                requesting_for = st.text_input(f"Generic Role (No {st.session_state.entity} roles found)", key="generic_role_text_unhashing")
        else:
            requesting_for = st.text_input("Generic Role (Only available for CSPL, CAPL, and CFSPL entities)", key="generic_role_text_unhashing")
    
    # Other fields
    validity = st.number_input("Validity (01-30 days)", min_value=1, max_value=30, step=1, value=10, key="validity_unhashing")
    reason = st.text_area("Reason for Request", max_chars=20, key="reason_unhashing")
    rm_approver = st.text_input("RM Approver", value=st.session_state.rm_approver, disabled=True, key="rm_approver_unhashing")
    data_approver = st.text_input("Data Approver", value=st.session_state.data_approver, disabled=True, key="data_approver_unhashing")
    
    # Submit
    submitted = st.button("Submit Request", key="submit_unhashing")
    
    # Handle submission
    if submitted:
        # Determine grantee type based on requesting_for_option
        if st.session_state.requesting_for_option == "Self":
            grantee = "SELF"
        elif st.session_state.requesting_for_option == "Generic User":
            grantee = "GENERIC_USER"
        elif st.session_state.requesting_for_option == "Generic Role":
            grantee = "GENERIC_ROLE"
        else:
            grantee = "SELF"
        
        form_data = [
            "Column request", request_id, user_name, email, entity, default_role,
            selected_object_source, selected_database, selected_schema,
            "", selected_table, columns, "", grantee, requesting_for, validity, reason,
            rm_approver, data_approver
        ]
        
        if save_request(form_data):
            mail_sent, mail_error = send_approval_emails(
                request_id, user_name, entity, selected_database, selected_schema,
                selected_table, columns, rm_approver, data_approver, email
            )
            
            if mail_sent:
                st.success("Column access request submitted successfully! Approval emails sent.")
                st.success(f"Your request ID is: {request_id}")
            else:
                st.error(f"Request saved but failed to send emails: {mail_error}")
        else:
            st.error("Failed to save request. Please try again.")

if __name__ == "__main__":
    main()
