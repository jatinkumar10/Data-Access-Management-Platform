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

@st.cache_resource(ttl=CACHE_TTL)  # Cache for 5 minutes
def get_sheets_service():
    """Initialize and return Google Sheets service with cached credentials"""
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

@st.cache_data(ttl=CACHE_TTL)  # Cache for 5 minutes
def fetch_all_sheet_data():
    """Fetch all required data from Google Sheets in one optimized call"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Fetch all sheets in one batch request
        ranges = ['snf_user', 'rm approvers', 'data approvers', 'table_list']
        result = sheet.values().batchGet(
            spreadsheetId=SPREADSHEET_ID,
            ranges=ranges
        ).execute()
        
        value_ranges = result.get('valueRanges', [])
        
        # Process user data
        users = []
        if len(value_ranges) > 0 and value_ranges[0].get('values'):
            values = value_ranges[0]['values']
            if len(values) > 1:
                header = values[0]
                try:
                    entity_col = header.index('ENTITY')
                    email_col = header.index('EMAIL')
                    role_col = header.index('DEFAULT_ROLE')
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
                except ValueError:
                    pass
        
        # Process RM approvers data
        rm_approvers = []
        if len(value_ranges) > 1 and value_ranges[1].get('values'):
            values = value_ranges[1]['values']
            if len(values) > 1:
                header = values[0]
                try:
                    user_email_col = header.index('User_Email')
                    approver_col = header.index('Approver')
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
                except ValueError:
                    pass
        
        # Process data approvers data
        data_approvers = []
        if len(value_ranges) > 2 and value_ranges[2].get('values'):
            values = value_ranges[2]['values']
            if len(values) > 1:
                header = values[0]
                try:
                    database_col = header.index('Database')
                    approver_col = header.index('Approver')
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
                except ValueError:
                    pass
        
        # Process table data
        table_data = []
        if len(value_ranges) > 3 and value_ranges[3].get('values'):
            values = value_ranges[3]['values']
            if len(values) > 1:
                header = values[0]
                try:
                    object_source_col = header.index('OBJECT_SOURCE')
                    database_col = header.index('DATABASE_NAME')
                    schema_col = header.index('SCHEMA_NAME')
                    table_col = header.index('TABLE_NAME')
                    for row in values[1:]:
                        if len(row) > max(object_source_col, database_col, schema_col, table_col):
                            object_source = row[object_source_col] if object_source_col < len(row) else ''
                            database = row[database_col] if database_col < len(row) else ''
                            schema = row[schema_col] if schema_col < len(row) else ''
                            table = row[table_col] if table_col < len(row) else ''
                            # Only add if all fields are not blank
                            if (object_source and object_source.strip() and 
                                database and database.strip() and 
                                schema and schema.strip() and 
                                table and table.strip()):
                                table_data.append({
                                    'object_source': object_source,
                                    'database': database,
                                    'schema': schema,
                                    'table': table
                                })
                except ValueError:
                    pass
        
        return users, rm_approvers, data_approvers, table_data
        
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return [], [], [], []

def generate_request_id():
    """Generate a unique request ID"""
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    random_num = random.randint(REQUEST_RANDOM_MIN, REQUEST_RANDOM_MAX)
    return f"{REQUEST_PREFIX}_{date_str}_{time_str}_{random_num}"

def append_to_sheet(data):
    """Append data to the responses sheet"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Add approval status columns
        data_with_status = data + [PENDING_STATUS, PENDING_STATUS]
        
        # Force text format for request ID to prevent truncation
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='responses',
            valueInputOption="USER_ENTERED",  # Changed from RAW to USER_ENTERED
            body={"values": [data_with_status]}
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error appending to sheet: {e}")
        return False

def send_approval_email(request_id, user_name, entity, database, schema, table, selected_names, rm_approver, data_approver, user_email):
    """Send approval emails"""
    subject = "Approval Needed: Table Access Request"
    
    # RM Approver email content
    rm_email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2c3e50;">Table Access Request - RM Approval Required</h2>
        <p>Dear RM Approver,</p>
        <p>The user <strong>{user_name}</strong> has submitted a table access request that requires your approval:</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #007bff;">Request Details:</h3>
            <ul style="list-style-type: none; padding-left: 0;">
                <li><strong>Request ID:</strong> {request_id}</li>
                <li><strong>Entity:</strong> {entity}</li>
                <li><strong>Database:</strong> {database}</li>
                <li><strong>Schema:</strong> {schema}</li>
                <li><strong>Table Option:</strong> {table}</li>
                <li><strong>Tables:</strong> {selected_names}</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href='{get_current_url()}?approve_id={request_id}&type=rm&action=approve&approver={rm_approver}' 
               style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block; font-weight: bold;">
               ✅ APPROVE REQUEST
            </a>
            <a href='{get_current_url()}?approve_id={request_id}&type=rm&action=reject&approver={rm_approver}' 
               style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block; font-weight: bold;">
               ❌ REJECT REQUEST
            </a>
        </div>
        
        <p style="font-size: 12px; color: #666; margin-top: 30px;">
            <em>Note: Clicking on either button will take you to the approval page where the action will be processed automatically.</em>
        </p>
    </body>
    </html>
    """
    
    # Data Approver email content
    data_email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2c3e50;">Table Access Request - Data Approval Required</h2>
        <p>Dear Data Approver,</p>
        <p>The user <strong>{user_name}</strong> has submitted a table access request that requires your approval:</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #17a2b8; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #17a2b8;">Request Details:</h3>
            <ul style="list-style-type: none; padding-left: 0;">
                <li><strong>Request ID:</strong> {request_id}</li>
                <li><strong>Entity:</strong> {entity}</li>
                <li><strong>Database:</strong> {database}</li>
                <li><strong>Schema:</strong> {schema}</li>
                <li><strong>Table Option:</strong> {table}</li>
                <li><strong>Tables:</strong> {selected_names}</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href='{get_current_url()}?approve_id={request_id}&type=data&action=approve&approver={data_approver}' 
               style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block; font-weight: bold;">
               ✅ APPROVE REQUEST
            </a>
            <a href='{get_current_url()}?approve_id={request_id}&type=data&action=reject&approver={data_approver}' 
               style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 0 10px; display: inline-block; font-weight: bold;">
               ❌ REJECT REQUEST
            </a>
        </div>
        
        <p style="font-size: 12px; color: #666; margin-top: 30px;">
            <em>Note: Clicking on either button will take you to the approval page where the action will be processed automatically.</em>
        </p>
    </body>
    </html>
    """
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            
            # Send to RM approver with RM-specific links
            rm_message = MIMEMultipart("alternative")
            rm_message["Subject"] = subject
            rm_message["From"] = EMAIL_SENDER
            rm_message["To"] = rm_approver
            rm_message["Cc"] = user_email  # Add user to CC
            rm_message.attach(MIMEText(rm_email_body, "html"))
            server.sendmail(EMAIL_SENDER, [rm_approver, user_email], rm_message.as_string())
            
            # Send to Data approver with Data-specific links
            data_message = MIMEMultipart("alternative")
            data_message["Subject"] = subject
            data_message["From"] = EMAIL_SENDER
            data_message["To"] = data_approver
            data_message["Cc"] = user_email  # Add user to CC
            data_message.attach(MIMEText(data_email_body, "html"))
            server.sendmail(EMAIL_SENDER, [data_approver, user_email], data_message.as_string())
        
        return True, None
    except Exception as e:
        return False, str(e)

def update_request_status(request_id, approver_type, new_status):
    """Update request status in Google Sheets"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='responses'
        ).execute()
        
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
        row_to_update = -1
        for idx, row in enumerate(values[1:], start=2):
            if len(row) > reqid_col and row[reqid_col] == request_id:
                row_to_update = idx
                break
        
        if row_to_update == -1:
            return False
        
        # Update status
        update_col_index = rm_col if approver_type == 'rm' else data_col
        update_col_letter = chr(ord('A') + update_col_index)
        range_to_update = f"responses!{update_col_letter}{row_to_update}"
        
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption="RAW",
            body={"values": [[new_status]]}
        ).execute()
        
        return True
        
    except Exception:
        return False

def handle_approval_from_url():
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
            
            success = update_request_status(request_id, approver_type, new_status)
            
            if success:
                st.success(f"{action_icon} Request {action_text} successfully!")
                st.info(f"Request ID: {request_id}")
                st.info(f"Status updated to: {new_status}")
                st.info(f"Approved by: {approver_email}")
            else:
                st.error("❌ Failed to update request status. Please try again.")
            
            return True
        
        return False
    except Exception as e:
        st.error(f"Error handling approval: {e}")
        return False

def main():
    """Main application"""
    # st.set_page_config(page_title="Table Access Request Form", page_icon="📋")
    st.title("Table Access Request Form")
    
    # Check if user is authenticated
    if 'user_email' not in st.session_state:
        st.error("Please login first")
        return
    
    # Handle approval first
    if handle_approval_from_url():
        return
    
    # Get user email from session
    user_email = st.session_state.user_email
    
    # Initialize session state
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'email' not in st.session_state:
        st.session_state.email = ""
    if 'entity' not in st.session_state:
        st.session_state.entity = ""
    if 'default_role' not in st.session_state:
        st.session_state.default_role = ""
    if 'rm_approver' not in st.session_state:
        st.session_state.rm_approver = ""
    if 'data_approver' not in st.session_state:
        st.session_state.data_approver = ""
    if 'requesting_for_option' not in st.session_state:
        st.session_state.requesting_for_option = "Self"
    if 'selected_object_source' not in st.session_state:
        st.session_state.selected_object_source = "Select Object Source"
    if 'selected_database' not in st.session_state:
        st.session_state.selected_database = "Select Database"
    if 'selected_schema' not in st.session_state:
        st.session_state.selected_schema = "Select Schema"

    
    # Fetch all data in one optimized call
    with st.spinner("Loading data..."):
        users, rm_approvers, data_approvers, table_data = fetch_all_sheet_data()
    
    if not users:
        st.error("Unable to load user data. Please check your connection.")
        return
    
    # Generate request ID
    request_id = st.text_input("Request ID", value=generate_request_id(), disabled=True, key="request_id_table")
    
    # Email field (read-only, auto-filled)
    st.text_input("Email ID", value=user_email, disabled=True, key="email_display")
    
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
    user_name = st.text_input("User Name", value=st.session_state.user_name, disabled=True, key="user_name_table")
    entity = st.text_input("Entity", value=st.session_state.entity, disabled=True, key="entity_table")
    
    # Hidden fields for response (not shown in UI)
    email = st.session_state.email
    default_role = st.session_state.default_role
    
    # Database selection
    
    # Object Source
    object_source_options = ["Select Object Source", "CSPL", "CAPL", "CFSPL"]
    selected_object_source = st.selectbox("Object Source", options=object_source_options, key="object_source_dropdown")
    
    if selected_object_source != st.session_state.selected_object_source:
        st.session_state.selected_object_source = selected_object_source
        st.session_state.selected_database = "Select Database"
        st.session_state.selected_schema = "Select Schema"
    
    # Database
    database_options = ["Select Database"]
    if selected_object_source != "Select Object Source" and table_data:
        filtered_databases = set()
        for table in table_data:
            if table['object_source'] == selected_object_source:
                filtered_databases.add(table['database'])
        database_options.extend(sorted(filtered_databases))
    
    selected_database = st.selectbox("Database", options=database_options, key="database_dropdown")
    
    if selected_database != st.session_state.selected_database:
        st.session_state.selected_database = selected_database
        st.session_state.selected_schema = "Select Schema"
        
        # Auto-populate data approver
        data_approver_entry = next((d for d in data_approvers if d['database'] == selected_database), None)
        st.session_state.data_approver = data_approver_entry['approver'] if data_approver_entry else ""
    
    # Schema
    schema_options = ["Select Schema"]
    if selected_database != "Select Database" and table_data:
        filtered_schemas = set()
        for table in table_data:
            if (table['object_source'] == selected_object_source and 
                table['database'] == selected_database):
                filtered_schemas.add(table['schema'])
        schema_options.extend(sorted(filtered_schemas))
    
    selected_schema = st.selectbox("Schema", options=schema_options, key="schema_dropdown")
    
    if selected_schema != st.session_state.selected_schema:
        st.session_state.selected_schema = selected_schema
    
    # Table selection
    table = st.radio("Table Selection:", ["Select Tables", "All Tables"], key="table_selection_radio")
    
    selected_names = None
    if table == "Select Tables":
        table_options = []
        if selected_schema != "Select Schema" and table_data:
            filtered_tables = []
            for table_item in table_data:
                if (table_item['object_source'] == selected_object_source and 
                    table_item['database'] == selected_database and 
                    table_item['schema'] == selected_schema):
                    filtered_tables.append(table_item['table'])
            table_options = sorted(filtered_tables)
        
        selected_tables = st.multiselect("Select Table(s):", options=table_options, key="tables_multiselect")
        
        if selected_tables:
            st.markdown("**Selected Tables:**")
            for t in selected_tables:
                st.code(t)
            selected_names = ", ".join(selected_tables)
        else:
            selected_names = ""
    elif table == "All Tables":
        selected_names = "ALL"
        st.info("All tables are selected for the chosen schema.")
    
    # Requesting For
    requesting_for_option = st.radio("Requesting For:", ["Self", "Generic User", "Generic Role"], key="requesting_for_radio")
    
    if requesting_for_option != st.session_state.requesting_for_option:
        st.session_state.requesting_for_option = requesting_for_option
    
    if st.session_state.requesting_for_option == "Self":
        requesting_for = st.text_input("Requesting For", value=st.session_state.email, disabled=True, key="requesting_for_table")
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
                requesting_for = st.selectbox(f"Select {st.session_state.entity} Generic User", options=["Select Generic User"] + generic_users, key="generic_user_dropdown")
                if requesting_for == "Select Generic User":
                    requesting_for = ""
            else:
                requesting_for = st.text_input(f"Generic User (No {st.session_state.entity} users found)", key="generic_user_text")
        else:
            requesting_for = st.text_input("Generic User (Only available for CSPL, CAPL, and CFSPL entities)", key="generic_user_text")
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
                requesting_for = st.selectbox(f"Select {st.session_state.entity} Generic Role", options=["Select Generic Role"] + generic_roles, key="generic_role_dropdown")
                if requesting_for == "Select Generic Role":
                    requesting_for = ""
            else:
                requesting_for = st.text_input(f"Generic Role (No {st.session_state.entity} roles found)", key="generic_role_text")
        else:
            requesting_for = st.text_input("Generic Role (Only available for CSPL, CAPL, and CFSPL entities)", key="generic_role_text")
    
    # Other fields
    validity = st.number_input("Validity (01-30 days)", min_value=1, max_value=30, step=1, key="validity_table")
    reason = st.text_area("Reason for Request", max_chars=20, key="reason_table")
    rm_approver = st.text_input("RM Approver", value=st.session_state.rm_approver, disabled=True, key="rm_approver_table")
    data_approver = st.text_input("Data Approver", value=st.session_state.data_approver, disabled=True, key="data_approver_table")
    
    # Submit button
    submitted = st.button("Submit Request", key="submit_table")
    
    # Validation checks
    if submitted:
        # Check if schema is selected
        if selected_schema == "Select Schema":
            st.error("Please select a Schema before submitting.")
            return
        
        # Check if tables are selected when "Select Tables" is chosen
        if table == "Select Tables" and not selected_tables:
            st.error("Please select at least one table before submitting.")
            return
        
        # Check if requesting_for is filled for Generic User/Role
        if st.session_state.requesting_for_option in ["Generic User", "Generic Role"] and not requesting_for:
            st.error("Please select a Generic User/Role before submitting.")
            return
        
        # Determine grantee type based on requesting_for_option
        if st.session_state.requesting_for_option == "Self":
            grantee = "SELF"
        elif st.session_state.requesting_for_option == "Generic User":
            grantee = "GENERIC_USER"
        elif st.session_state.requesting_for_option == "Generic Role":
            grantee = "GENERIC_ROLE"
        else:
            grantee = "SELF"
        
        # Determine shared status
        shared_status = "SHARED"  # Default value
        if st.session_state.entity != selected_object_source:
            # Case 2: Entity and object source are different
            try:
                service = get_sheets_service()
                sheet = service.spreadsheets()
                result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='table_list').execute()
                values = result.get('values', [])
                
                if len(values) > 1:
                    header = values[0]
                    try:
                        object_source_col = header.index('OBJECT_SOURCE')
                        fqn_col = header.index('FQN(DB.SCH)')
                        
                        target_fqn = f"{selected_database}.{selected_schema}"
                        
                        # Check if this DATABASE.SCHEMA combination exists in user's entity
                        found_in_entity = False
                        for row in values[1:]:
                            if len(row) > max(object_source_col, fqn_col):
                                row_entity = row[object_source_col] if object_source_col < len(row) else ''
                                row_fqn = row[fqn_col] if fqn_col < len(row) else ''
                                
                                if row_entity == st.session_state.entity and row_fqn == target_fqn:
                                    found_in_entity = True
                                    break
                        
                        shared_status = "SHARED" if found_in_entity else "NOT_SHARED"
                        
                    except ValueError:
                        shared_status = "NOT_SHARED"
            except Exception:
                shared_status = "NOT_SHARED"
        
        # Create a unique key for this form combination
        form_key = f"{selected_database}_{selected_schema}_{table}_{selected_names}"
        confirmation_key = f"confirmed_{form_key}"
        
        # Check if database.schema is not shared and show warning message once
        if shared_status == "NOT_SHARED" and not st.session_state.get(confirmation_key, False):
            target_fqn = f"{selected_database}.{selected_schema}"
            
            st.warning(f"This database.schema ({target_fqn}) is not shared. You can still proceed with your request.")
            # Mark this form combination as warned
            st.session_state[confirmation_key] = True
            return
        
        # If we reach here, either it's SHARED or user has already seen the warning
        form_data = [
            "Table request", request_id, user_name, email, entity, default_role,
            selected_object_source, selected_database, selected_schema,
            table, selected_names, "", shared_status, grantee, requesting_for, validity, reason,
            rm_approver, data_approver
        ]
        
        # Debug: Show what we're actually sending
        print("FORM DATA BEING SENT:", form_data)
        
        # Save to Google Sheets
        if append_to_sheet(form_data):
            mail_sent, mail_error = send_approval_email(
                request_id, user_name, entity, selected_database, selected_schema,
                table, selected_names, rm_approver, data_approver, email
            )
            
            if mail_sent:
                st.success("Table request submitted successfully! Approval emails sent.")
                st.success(f"Your request ID is: {request_id}")
                # Reset the specific confirmation key for this form combination
                form_key = f"{selected_database}_{selected_schema}_{table}_{selected_names}"
                confirmation_key = f"confirmed_{form_key}"
                st.session_state[confirmation_key] = False
                # Don't call st.rerun() to keep the message visible
                return
            else:
                st.error(f"Request saved but failed to send emails: {mail_error}")
        else:
            st.error("Failed to save request. Please try again.")
        return

if __name__ == "__main__":
    main()
