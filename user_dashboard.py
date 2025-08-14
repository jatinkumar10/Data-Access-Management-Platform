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
def get_user_requests(user_email):
    """Fetch all requests for the logged-in user"""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        
        all_user_requests = []
        
        # Fetch from responses sheet (Table and Column requests)
        try:
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='responses'
            ).execute()
            
            values = result.get('values', [])
            if values and len(values) >= 2:
                header = values[0]
                
                # Find column indices
                try:
                    request_id_col = header.index('REQUEST_ID')
                    user_col = header.index('EMAIL')  # Based on your sheet, it's 'EMAIL'
                    request_type_col = header.index('REQUEST_TYPE')
                    entity_col = header.index('ENTITY')
                    rm_status_col = header.index('RM_APPROVER_STATUS')  # Based on your sheet, it's 'RM_APPROVER_STATUS'
                    data_status_col = header.index('DATA_APPROVER_STATUS') if 'DATA_APPROVER_STATUS' in header else None
                except ValueError as e:
                    st.error(f"Required columns not found in responses sheet. Error: {e}")
                    st.info(f"Available columns: {header}")
                    return []
                
                # Process each row
                for row in values[1:]:
                    if len(row) > user_col and row[user_col].strip().lower() == user_email.lower():
                        request_data = {
                            'request_id': row[request_id_col] if request_id_col < len(row) else '',
                            'request_type': row[request_type_col] if request_type_col < len(row) else '',
                            'entity': row[entity_col] if entity_col < len(row) else '',
                            'rm_status': row[rm_status_col] if rm_status_col < len(row) else 'Pending',
                            'data_status': row[data_status_col] if data_status_col and data_status_col < len(row) else 'Pending',
                            'business_unit': row[3] if len(row) > 3 else '',  # Column 3 for BU/Table
                            'submitted_date': row[0] if len(row) > 0 else '',  # First column often has date
                            'comments': row[-1] if len(row) > 0 else ''  # Last column often has comments
                        }
                        all_user_requests.append(request_data)
        except Exception as e:
            st.warning(f"Could not fetch from responses sheet: {e}")
        
        # Fetch from user_responses sheet (User Creation requests)
        try:
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='user_responses'
            ).execute()
            
            values = result.get('values', [])
            if values and len(values) >= 2:
                header = values[0]
                
                # Find column indices for user_responses sheet
                try:
                    request_id_col = header.index('Request_id')
                    user_col = header.index('User')
                    entity_col = header.index('Entity')
                    approval_status_col = header.index('Approval_status')
                    bu_col = header.index('BU')
                except ValueError as e:
                    st.warning(f"Required columns not found in user_responses sheet. Error: {e}")
                    st.info(f"Available columns in user_responses: {header}")
                else:
                    # Process each row
                    for row in values[1:]:
                        if len(row) > user_col and row[user_col].strip().lower() == user_email.lower():
                            request_data = {
                                'request_id': row[request_id_col] if request_id_col < len(row) else '',
                                'request_type': 'User Creation',  # Fixed type for user creation
                                'entity': row[entity_col] if entity_col < len(row) else '',
                                'rm_status': row[approval_status_col] if approval_status_col < len(row) else 'Pending',
                                'data_status': 'N/A',  # User creation doesn't have data approval
                                'business_unit': row[bu_col] if bu_col < len(row) else '',
                                'submitted_date': row[0] if len(row) > 0 else '',
                                'comments': row[-1] if len(row) > 0 else ''
                            }
                            all_user_requests.append(request_data)
        except Exception as e:
            st.warning(f"Could not fetch from user_responses sheet: {e}")
        
        # Sort by request ID (latest first - assuming newer IDs come later)
        all_user_requests.sort(key=lambda x: x['request_id'], reverse=True)
        
        return all_user_requests
    except Exception as e:
        st.error(f"Error fetching user requests: {e}")
        return []

def get_status_icon(status):
    """Get status icon based on status"""
    if status == "Approved":
        return "✅"
    elif status == "Rejected":
        return "❌"
    else:
        return "⏳"

def get_status_color(status):
    """Get status color for styling"""
    if status == "Approved":
        return "color: green; font-weight: bold;"
    elif status == "Rejected":
        return "color: red; font-weight: bold;"
    else:
        return "color: orange; font-weight: bold;"

def calculate_overall_status(rm_status, data_status):
    """Calculate overall status based on both approvals"""
    # Handle user creation requests where data_status is "N/A"
    if data_status == "N/A":
        if rm_status == "Approved":
            return "Approved"
        elif rm_status == "Rejected":
            return "Rejected"
        else:
            return "Pending"
    
    # Handle regular requests (Table/Column) that need both approvals
    if rm_status == "Rejected" or data_status == "Rejected":
        return "Rejected"
    elif rm_status == "Approved" and data_status == "Approved":
        return "Approved"
    else:
        return "Pending"

def format_dashboard_data(requests):
    """Format requests data for dashboard display"""
    dashboard_data = []
    
    for req in requests:
        overall_status = calculate_overall_status(req['rm_status'], req['data_status'])
        
        dashboard_data.append({
            'Request ID': req['request_id'],
            'Request Type': req['request_type'],
            'Entity': req['entity'],
            'RM Status': f"{get_status_icon(req['rm_status'])} {req['rm_status']}",
            'Data Status': f"{get_status_icon(req['data_status'])} {req['data_status']}",
            'Overall Status': f"{get_status_icon(overall_status)} {overall_status}",
            # Store full data for details modal
            '_full_data': req
        })
    
    return dashboard_data

def show_request_details(request_data):
    """Show detailed request information in a modal-like format"""
    st.markdown("---")
    st.markdown("### 📋 Request Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Request ID:** {request_data['request_id']}")
        st.markdown(f"**Request Type:** {request_data['request_type']}")
        st.markdown(f"**Entity:** {request_data['entity']}")
        st.markdown(f"**Business Unit/Table:** {request_data['business_unit']}")
    
    with col2:
        st.markdown(f"**Submitted Date:** {request_data['submitted_date']}")
        st.markdown(f"**RM Status:** {get_status_icon(request_data['rm_status'])} {request_data['rm_status']}")
        st.markdown(f"**Data Status:** {get_status_icon(request_data['data_status'])} {request_data['data_status']}")
        if request_data['comments']:
            st.markdown(f"**Comments:** {request_data['comments']}")

def create_dashboard():
    """Main dashboard function"""
    st.title("📊 My Requests Dashboard")
    
    # Check if user is authenticated
    if 'user_email' not in st.session_state:
        st.error("Please login first")
        return
    
    user_email = st.session_state.user_email
    
    # Fetch user requests
    with st.spinner("Loading your requests..."):
        user_requests = get_user_requests(user_email)
    
    if not user_requests:
        st.info("No requests found. Submit your first request to see it here!")
        return
    
    # Format data for dashboard
    dashboard_data = format_dashboard_data(user_requests)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Pending", "Approved", "Rejected"],
            key="status_filter"
        )
    
    with col2:
        type_filter = st.selectbox(
            "Filter by Type",
            ["All"] + list(set([req['Request Type'] for req in dashboard_data])),
            key="type_filter"
        )
    
    with col3:
        search_term = st.text_input("Search by Request ID", key="search_filter")
    
    # Apply filters
    filtered_data = dashboard_data.copy()
    
    if status_filter != "All":
        filtered_data = [req for req in filtered_data if status_filter in req['Overall Status']]
    
    if type_filter != "All":
        filtered_data = [req for req in filtered_data if req['Request Type'] == type_filter]
    
    if search_term:
        filtered_data = [req for req in filtered_data if search_term.lower() in req['Request ID'].lower()]
    
    # Summary statistics
    total_requests = len(filtered_data)
    pending_count = len([req for req in filtered_data if "Pending" in req['Overall Status']])
    approved_count = len([req for req in filtered_data if "Approved" in req['Overall Status']])
    rejected_count = len([req for req in filtered_data if "Rejected" in req['Overall Status']])
    
    st.markdown(f"**Summary:** Total: {total_requests} | Pending: {pending_count} | Approved: {approved_count} | Rejected: {rejected_count}")
    
    st.markdown("---")
    
    # Display requests table
    if filtered_data:
        st.markdown("### Your Requests (Latest First)")
        
        # Create DataFrame for display
        display_data = []
        for req in filtered_data:
            display_data.append({
                'Request ID': req['Request ID'],
                'Request Type': req['Request Type'],
                'Entity': req['Entity'],
                'RM Status': req['RM Status'],
                'Data Status': req['Data Status'],
                'Overall Status': req['Overall Status']
            })
        
        df = pd.DataFrame(display_data)
        
        # Display with custom styling
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Request ID": st.column_config.TextColumn(
                    "Request ID",
                    help="Click to view details",
                    max_chars=20
                ),
                "RM Status": st.column_config.TextColumn(
                    "RM Status",
                    help="Risk Management approval status"
                ),
                "Data Status": st.column_config.TextColumn(
                    "Data Status",
                    help="Data team approval status"
                ),
                "Overall Status": st.column_config.TextColumn(
                    "Overall Status",
                    help="Overall request status"
                )
            }
        )
    else:
        st.info("No requests match your current filters.")

if __name__ == "__main__":
    create_dashboard() 