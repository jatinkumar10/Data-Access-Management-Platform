import streamlit as st
import pandas as pd
from datetime import datetime
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
def get_user_approver_roles(user_email):
    """Check if user is an RM, Data approver, or Manager"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        roles = {'rm': False, 'data': False, 'manager': False}
        
        # Check RM approvers from rm approvers sheet
        try:
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='rm approvers'
            ).execute()
            
            values = result.get('values', [])
            if values and len(values) >= 2:
                header = values[0]
                try:
                    # Find approver column
                    approver_col = header.index('Approver') if 'Approver' in header else -1
                    
                    # Check if user is an RM approver
                    for row in values[1:]:
                        if approver_col >= 0 and len(row) > approver_col:
                            approver_email = row[approver_col].strip().lower()
                            if approver_email == user_email.lower():
                                roles['rm'] = True
                                break
                except ValueError:
                    pass
        except Exception:
            pass
        
        # Check Data approvers from data approvers sheet
        try:
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='data approvers'
            ).execute()
            
            values = result.get('values', [])
            if values and len(values) >= 2:
                header = values[0]
                try:
                    # Find database and approver columns
                    database_col = header.index('Database') if 'Database' in header else -1
                    approver_col = header.index('Approver') if 'Approver' in header else -1
                    
                    # Check if user is a Data approver (for any database)
                    for row in values[1:]:
                        if approver_col >= 0 and len(row) > approver_col:
                            approver_email = row[approver_col].strip().lower()
                            if approver_email == user_email.lower():
                                roles['data'] = True
                                break
                except ValueError:
                    pass
        except Exception:
            pass
        
        # Check Managers from user_manager sheet
        try:
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='user_manager'
            ).execute()
            
            values = result.get('values', [])
            if values and len(values) >= 2:
                header = values[0]
                try:
                    # Find manager email column
                    manager_email_col = header.index('Manager_email_id') if 'Manager_email_id' in header else -1
                    
                    # Check if user is a manager
                    for row in values[1:]:
                        if manager_email_col >= 0 and len(row) > manager_email_col:
                            manager_email = row[manager_email_col].strip().lower()
                            if manager_email == user_email.lower():
                                roles['manager'] = True
                                break
                except ValueError:
                    pass
        except Exception:
            pass
        
        return roles
    except Exception as e:
        st.error(f"Error checking approver roles: {e}")
        return {'rm': False, 'data': False, 'manager': False}

@st.cache_data(ttl=CACHE_TTL)
def get_pending_approvals_for_user(user_email, approver_roles):
    """Get requests pending approval for specific user"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        pending_requests = []
        
        # Fetch from responses sheet (Table and Column requests)
        if approver_roles['rm'] or approver_roles['data']:
            try:
                result = sheet.values().get(
                    spreadsheetId=SPREADSHEET_ID,
                    range='responses'
                ).execute()
                
                values = result.get('values', [])
                if values and len(values) >= 2:
                    header = values[0]
                    
                    try:
                        request_id_col = header.index('REQUEST_ID')
                        user_col = header.index('EMAIL')
                        request_type_col = header.index('REQUEST_TYPE')
                        entity_col = header.index('ENTITY')
                        rm_status_col = header.index('RM_APPROVER_STATUS')
                        data_status_col = header.index('DATA_APPROVER_STATUS') if 'DATA_APPROVER_STATUS' in header else None
                        
                        # Columns for assigned approvers
                        rm_approver_col = header.index('RM_APPROVER') if 'RM_APPROVER' in header else -1
                        data_approver_col = header.index('DATA_APPROVER') if 'DATA_APPROVER' in header else -1
                        
                        # Try alternative column names for approvers
                        if rm_approver_col == -1:
                            rm_approver_col = header.index('RM_Approver') if 'RM_Approver' in header else -1
                        if data_approver_col == -1:
                            data_approver_col = header.index('Data_Approver') if 'Data_Approver' in header else -1
                        
                        # Additional columns for detailed information
                        database_col = header.index('DATABASE') if 'DATABASE' in header else -1
                        schema_col = header.index('SCHEMA') if 'SCHEMA' in header else -1
                        table_col = header.index('TABLE') if 'TABLE' in header else -1
                        column_col = header.index('COLUMN_NAMES') if 'COLUMN_NAMES' in header else -1
                        
                        # Try alternative column names
                        if database_col == -1:
                            database_col = header.index('Database') if 'Database' in header else -1
                        if schema_col == -1:
                            schema_col = header.index('Schema') if 'Schema' in header else -1
                        if table_col == -1:
                            table_col = header.index('Table') if 'Table' in header else -1
                        if column_col == -1:
                            column_col = header.index('Column') if 'Column' in header else -1
                        
                        for row in values[1:]:
                            if len(row) > max(request_id_col, user_col, request_type_col, entity_col):
                                rm_status = row[rm_status_col] if rm_status_col < len(row) else 'Pending'
                                data_status = row[data_status_col] if data_status_col and data_status_col < len(row) else 'Pending'
                                
                                # Get assigned approvers for this request
                                rm_approver = row[rm_approver_col] if rm_approver_col >= 0 and len(row) > rm_approver_col else ""
                                data_approver = row[data_approver_col] if data_approver_col >= 0 and len(row) > data_approver_col else ""
                                
                                # Get additional details
                                database = row[database_col] if database_col >= 0 and len(row) > database_col else ""
                                schema = row[schema_col] if schema_col >= 0 and len(row) > schema_col else ""
                                table = row[table_col] if table_col >= 0 and len(row) > table_col else ""
                                column = row[column_col] if column_col >= 0 and len(row) > column_col else ""
                                
                                # Check if this request needs approval from this specific user
                                # Only show RM requests if current user is the assigned RM approver
                                if (approver_roles['rm'] and rm_status == 'Pending' and 
                                    rm_approver.strip().lower() == user_email.lower()):
                                    request_data = {
                                        'request_id': row[request_id_col],
                                        'request_type': row[request_type_col],
                                        'user': row[user_col],
                                        'entity': row[entity_col],
                                        'approver_type': 'rm',
                                        'status': rm_status,
                                        'business_unit': row[3] if len(row) > 3 else '',
                                        'submitted_date': row[0] if len(row) > 0 else '',
                                        'comments': row[-1] if len(row) > 0 else '',
                                        'database': database,
                                        'schema': schema,
                                        'table': table,
                                        'column': column
                                    }
                                    pending_requests.append(request_data)
                                
                                # Only show Data requests if current user is the assigned Data approver
                                if (approver_roles['data'] and data_status == 'Pending' and 
                                    data_approver.strip().lower() == user_email.lower()):
                                    request_data = {
                                        'request_id': row[request_id_col],
                                        'request_type': row[request_type_col],
                                        'user': row[user_col],
                                        'entity': row[entity_col],
                                        'approver_type': 'data',
                                        'status': data_status,
                                        'business_unit': row[3] if len(row) > 3 else '',
                                        'submitted_date': row[0] if len(row) > 0 else '',
                                        'comments': row[-1] if len(row) > 0 else '',
                                        'database': database,
                                        'schema': schema,
                                        'table': table,
                                        'column': column
                                    }
                                    pending_requests.append(request_data)
                    except ValueError as e:
                        st.warning(f"Required columns not found in responses sheet: {e}")
            except Exception as e:
                st.warning(f"Could not fetch from responses sheet: {e}")
        
        # Fetch from user_responses sheet (User Creation requests)
        if approver_roles['manager']:
            try:
                result = sheet.values().get(
                    spreadsheetId=SPREADSHEET_ID,
                    range='user_responses'
                ).execute()
                
                values = result.get('values', [])
                if values and len(values) >= 2:
                    header = values[0]
                    
                    try:
                        request_id_col = header.index('Request_id')
                        user_col = header.index('User')
                        entity_col = header.index('Entity')
                        approval_status_col = header.index('Approval_status')
                        bu_col = header.index('BU')
                        
                        # Additional columns for user creation requests
                        manager_email_col = header.index('Manager_Email') if 'Manager_Email' in header else -1
                        
                        # Try alternative column names for manager email
                        if manager_email_col == -1:
                            manager_email_col = header.index('Manager_email') if 'Manager_email' in header else -1
                        if manager_email_col == -1:
                            manager_email_col = header.index('Manager') if 'Manager' in header else -1
                        if manager_email_col == -1:
                            manager_email_col = header.index('Manager_email_id') if 'Manager_email_id' in header else -1
                        
                        role_col = header.index('Role') if 'Role' in header else -1
                        
                        for row in values[1:]:
                            if len(row) > max(request_id_col, user_col, entity_col, approval_status_col):
                                if row[approval_status_col] == 'Pending':
                                    # Get additional details for user creation
                                    manager_email = row[manager_email_col] if manager_email_col >= 0 and len(row) > manager_email_col else ""
                                    role = row[role_col] if role_col >= 0 and len(row) > role_col else ""
                                    
                                    # Only show manager requests if current user is the assigned manager
                                    if manager_email.strip().lower() == user_email.lower():
                                        request_data = {
                                            'request_id': row[request_id_col],
                                            'request_type': 'User Creation',
                                            'user': row[user_col],
                                            'entity': row[entity_col],
                                            'approver_type': 'manager',
                                            'status': row[approval_status_col],
                                            'business_unit': row[bu_col] if bu_col < len(row) else '',
                                            'submitted_date': row[0] if len(row) > 0 else '',
                                            'comments': row[-1] if len(row) > 0 else '',
                                            'database': "",
                                            'schema': "",
                                            'table': "",
                                            'column': "",
                                            'manager_email': manager_email,
                                            'role': role
                                        }
                                        pending_requests.append(request_data)
                    except ValueError as e:
                        st.warning(f"Required columns not found in user_responses sheet: {e}")
            except Exception as e:
                st.warning(f"Could not fetch from user_responses sheet: {e}")
        
        # Sort by request ID (latest first)
        pending_requests.sort(key=lambda x: x['request_id'], reverse=True)
        
        return pending_requests
    except Exception as e:
        st.error(f"Error fetching pending approvals: {e}")
        return []

def approve_request_in_sheet(request_id, approver_type, user_email):
    """Approve a request and update Google Sheets"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Determine which sheet and column to update
        if approver_type == 'rm':
            sheet_range = 'responses'
            status_column = 'RM_APPROVER_STATUS'
        elif approver_type == 'data':
            sheet_range = 'responses'
            status_column = 'DATA_APPROVER_STATUS'
        elif approver_type == 'manager':
            sheet_range = 'user_responses'
            status_column = 'Approval_status'
        
        # Find the row with matching REQUEST_ID
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_range
        ).execute()
        
        values = result.get('values', [])
        header = values[0]
        
        # Find column indices
        request_id_col = header.index('REQUEST_ID') if 'REQUEST_ID' in header else header.index('Request_id')
        status_col = header.index(status_column)
        
        # Find row to update
        row_to_update = None
        for idx, row in enumerate(values[1:], start=2):
            if len(row) > request_id_col and row[request_id_col] == request_id:
                row_to_update = idx
                break
        
        if row_to_update:
            # Update the status to "Approved"
            # Convert column index to letter (A=0, B=1, ..., Z=25, AA=26, etc.)
            def col_to_letter(col_idx):
                result = ""
                while col_idx >= 0:
                    col_idx, remainder = divmod(col_idx, 26)
                    result = chr(65 + remainder) + result
                    col_idx -= 1
                return result
            
            col_letter = col_to_letter(status_col)
            update_range = f"{sheet_range}!{col_letter}{row_to_update}"
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=update_range,
                valueInputOption="RAW",
                body={"values": [["Approved"]]}
            ).execute()
            
            return True, "Request approved successfully"
        else:
            return False, "Request ID not found"
            
    except Exception as e:
        return False, f"Error approving request: {e}"

def reject_request_in_sheet(request_id, approver_type, user_email):
    """Reject a request and update Google Sheets"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Determine which sheet and column to update
        if approver_type == 'rm':
            sheet_range = 'responses'
            status_column = 'RM_APPROVER_STATUS'
        elif approver_type == 'data':
            sheet_range = 'responses'
            status_column = 'DATA_APPROVER_STATUS'
        elif approver_type == 'manager':
            sheet_range = 'user_responses'
            status_column = 'Approval_status'
        
        # Find the row with matching REQUEST_ID
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_range
        ).execute()
        
        values = result.get('values', [])
        header = values[0]
        
        # Find column indices
        request_id_col = header.index('REQUEST_ID') if 'REQUEST_ID' in header else header.index('Request_id')
        status_col = header.index(status_column)
        
        # Find row to update
        row_to_update = None
        for idx, row in enumerate(values[1:], start=2):
            if len(row) > request_id_col and row[request_id_col] == request_id:
                row_to_update = idx
                break
        
        if row_to_update:
            # Update the status to "Rejected"
            # Convert column index to letter (A=0, B=1, ..., Z=25, AA=26, etc.)
            def col_to_letter(col_idx):
                result = ""
                while col_idx >= 0:
                    col_idx, remainder = divmod(col_idx, 26)
                    result = chr(65 + remainder) + result
                    col_idx -= 1
                return result
            
            col_letter = col_to_letter(status_col)
            update_range = f"{sheet_range}!{col_letter}{row_to_update}"
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=update_range,
                valueInputOption="RAW",
                body={"values": [["Rejected"]]}
            ).execute()
            

            
            return True, "Request rejected successfully"
        else:
            return False, "Request ID not found"
            
    except Exception as e:
        return False, f"Error rejecting request: {e}"

def show_complete_request_details(request_id, approver_type):
    """Show ALL columns from Google Sheet for specific request"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        # Determine which sheet to fetch from
        if approver_type in ['rm', 'data']:
            sheet_range = 'responses'
        elif approver_type == 'manager':
            sheet_range = 'user_responses'
        else:
            st.error("Invalid approver type")
            return
        
        # Fetch the complete row from the appropriate sheet
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_range
        ).execute()
        
        values = result.get('values', [])
        if not values or len(values) < 2:
            st.error("No data found")
            return
        
        header = values[0]
        
        # Find the row with matching REQUEST_ID
        request_id_col = header.index('REQUEST_ID') if 'REQUEST_ID' in header else header.index('Request_id')
        
        target_row = None
        for row in values[1:]:
            if len(row) > request_id_col and row[request_id_col] == request_id:
                target_row = row
                break
        
        if not target_row:
            st.error("Request not found")
            return
        
        # Display complete request details
        st.markdown("---")
        st.markdown("### 📋 Complete Request Details")
        st.markdown(f"**Request ID:** {request_id}")
        st.markdown(f"**Sheet:** {sheet_range}")
        
        # Create a table with all columns
        details_data = {}
        for i, col_name in enumerate(header):
            if i < len(target_row):
                details_data[col_name] = target_row[i]
            else:
                details_data[col_name] = ""
        
        # Display as a horizontal table
        st.markdown("#### All Request Information:")
        
        # Show as a dataframe for horizontal viewing
        df_details = pd.DataFrame([details_data])
        st.dataframe(df_details, use_container_width=True, hide_index=True)
        
        # Also show as a formatted table with better spacing
        st.markdown("#### Formatted View:")
        
        # Create a more compact horizontal layout
        num_cols = 3  # Show 3 columns per row
        for i in range(0, len(details_data), num_cols):
            cols = st.columns(num_cols)
            for j, col in enumerate(cols):
                if i + j < len(details_data):
                    col_name = list(details_data.keys())[i + j]
                    value = details_data[col_name]
                    with col:
                        st.markdown(f"**{col_name}:**")
                        st.text(value)
        
    except Exception as e:
        st.error(f"Error fetching complete request details: {e}")

def create_approver_dashboard():
    """Main approver dashboard function"""
    st.title("🔐 Approver Dashboard")
    
    # Check if user is authenticated
    if 'user_email' not in st.session_state:
        st.error("Please login first")
        return
    
    user_email = st.session_state.user_email
    
    # Check if user is an approver
    approver_roles = get_user_approver_roles(user_email)
    
    if not any(approver_roles.values()):
        st.error("Access Denied: You are not authorized to view this dashboard.")
        st.info("Only RM approvers, Data approvers, and Managers can access this dashboard.")
        return
    
    # Show user's roles
    roles_text = []
    if approver_roles['rm']:
        roles_text.append("RM Approver")
    if approver_roles['data']:
        roles_text.append("Data Approver")
    if approver_roles['manager']:
        roles_text.append("Manager")
    
    st.markdown(f"**Your Roles:** {', '.join(roles_text)}")
    
    # Fetch pending approvals
    with st.spinner("Loading pending approvals..."):
        pending_requests = get_pending_approvals_for_user(user_email, approver_roles)
    
    if not pending_requests:
        st.info("No pending approvals found. All requests have been processed!")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        type_filter = st.selectbox(
            "Filter by Type",
            ["All"] + list(set([req['request_type'] for req in pending_requests])),
            key="approver_type_filter"
        )
    
    with col2:
        approver_type_filter = st.selectbox(
            "Filter by Approver Type",
            ["All"] + list(set([req['approver_type'] for req in pending_requests])),
            key="approver_role_filter"
        )
    
    with col3:
        search_term = st.text_input("Search by Request ID", key="approver_search_filter")
    
    # Apply filters
    filtered_requests = pending_requests.copy()
    
    if type_filter != "All":
        filtered_requests = [req for req in filtered_requests if req['request_type'] == type_filter]
    
    if approver_type_filter != "All":
        filtered_requests = [req for req in filtered_requests if req['approver_type'] == approver_type_filter]
    
    if search_term:
        filtered_requests = [req for req in filtered_requests if search_term.lower() in req['request_id'].lower()]
    
    # Action buttons and summary
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("✅ Approve All", key="approve_all_btn", type="primary"):
            if filtered_requests:
                success_count = 0
                error_count = 0
                with st.spinner("Processing approvals..."):
                    for req in filtered_requests:
                        success, message = approve_request_in_sheet(req['request_id'], req['approver_type'], user_email)
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                
                if success_count > 0:
                    st.success(f"Successfully approved {success_count} requests!")
                if error_count > 0:
                    st.error(f"Failed to approve {error_count} requests.")
                st.rerun()
            else:
                st.warning("No requests to approve.")
    
    with col2:
        if st.button("❌ Reject All", key="reject_all_btn", type="secondary"):
            if filtered_requests:
                st.session_state["show_reject_all"] = True
            else:
                st.warning("No requests to reject.")
    
    with col3:
        # Summary statistics
        total_requests = len(filtered_requests)
        rm_requests = len([req for req in filtered_requests if req['approver_type'] == 'rm'])
        data_requests = len([req for req in filtered_requests if req['approver_type'] == 'data'])
        manager_requests = len([req for req in filtered_requests if req['approver_type'] == 'manager'])
        
        st.markdown(f"**Summary:** Total: {total_requests} | RM: {rm_requests} | Data: {data_requests} | Manager: {manager_requests}")
    
    # Reject All confirmation dialog
    if st.session_state.get("show_reject_all", False):
        st.markdown("### Reject All Requests")
        st.warning("⚠️ You are about to reject ALL filtered requests. This action cannot be undone.")
        
        rejection_reason = st.text_area("Rejection Reason (required):", 
                                       placeholder="Please provide a reason for rejecting all requests...",
                                       key="reject_all_reason")
        
        col_confirm1, col_confirm2, col_confirm3 = st.columns([1, 1, 2])
        
        with col_confirm1:
            if st.button("✅ Confirm Reject All", key="confirm_reject_all_btn", type="primary"):
                if rejection_reason.strip():
                    success_count = 0
                    error_count = 0
                    with st.spinner("Processing rejections..."):
                        for req in filtered_requests:
                            success, message = reject_request_in_sheet(req['request_id'], req['approver_type'], user_email, rejection_reason)
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                    
                    if success_count > 0:
                        st.success(f"Successfully rejected {success_count} requests!")
                    if error_count > 0:
                        st.error(f"Failed to reject {error_count} requests.")
                    st.session_state["show_reject_all"] = False
                    st.rerun()
                else:
                    st.error("Please provide a rejection reason.")
        
        with col_confirm2:
            if st.button("❌ Cancel", key="cancel_reject_all_btn"):
                st.session_state["show_reject_all"] = False
                st.rerun()
    
    st.markdown("---")
    
    # Display only actions section
    if filtered_requests:
        st.markdown("### Actions")
        
        for req in filtered_requests:
            request_id = req['request_id']
            
            # Create a container for each request with action buttons
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.markdown(f"**{request_id}** - {req['request_type']} by {req['user']}")
                    
                    # Show additional details based on request type
                    if req['request_type'] in ['Table request', 'Column request', 'Table', 'Column']:
                        details_parts = []
                        if req.get('database'):
                            details_parts.append(f"DB: {req['database']}")
                        if req.get('schema'):
                            details_parts.append(f"Schema: {req['schema']}")
                        if req.get('table'):
                            details_parts.append(f"Table: {req['table']}")
                        if req.get('column') and req['request_type'] in ['Column request', 'Column']:
                            details_parts.append(f"Column: {req['column']}")
                        
                        if details_parts:
                            st.markdown(f"<small>{' | '.join(details_parts)}</small>", unsafe_allow_html=True)
                        else:
                            # Debug: Show what data we have
                            debug_info = []
                            if req.get('database'):
                                debug_info.append(f"DB: {req['database']}")
                            if req.get('schema'):
                                debug_info.append(f"Schema: {req['schema']}")
                            if req.get('table'):
                                debug_info.append(f"Table: {req['table']}")
                            if req.get('column'):
                                debug_info.append(f"Column: {req['column']}")
                            if debug_info:
                                st.markdown(f"<small style='color: orange;'>Debug: {' | '.join(debug_info)}</small>", unsafe_allow_html=True)
                    
                    elif req['request_type'] == 'User Creation':
                        user_details = []
                        if req.get('manager_email'):
                            user_details.append(f"Manager: {req['manager_email']}")
                        if req.get('role'):
                            user_details.append(f"Role: {req['role']}")
                        
                        if user_details:
                            st.markdown(f"<small>{' | '.join(user_details)}</small>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"Entity: {req['entity']} | Type: {req['approver_type'].title()}")
                
                with col3:
                    if st.button("✅ Approve", key=f"approve_{request_id}_{req['approver_type']}"):
                        success, message = approve_request_in_sheet(request_id, req['approver_type'], user_email)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                
                with col4:
                    if st.button("❌ Reject", key=f"reject_{request_id}_{req['approver_type']}"):
                        success, message = reject_request_in_sheet(request_id, req['approver_type'], user_email)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                
                st.markdown("---")
    else:
        st.info("No requests match your current filters.")

if __name__ == "__main__":
    create_approver_dashboard() 