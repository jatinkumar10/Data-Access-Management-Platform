import requests
import sys
import os
from typing import Dict, Any, List
from datetime import datetime
import streamlit as st
from functools import wraps
import time

# Add parent directory to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import SPREADSHEET_ID
from token_service import get_token_service

# Add emails directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emails'))
from emailtemplates import (
    create_approval_notification_email,
    create_table_access_approval_notification_email,
    create_column_unhashing_approval_notification_email,
    create_multi_approver_notification_email
)
from emailhandler import send_email

def cache_data_for_2_minutes(func):
    """
    Decorator to cache function results for 2 minutes.
    Uses Streamlit's session state to store cached data.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Create a unique cache key based on function name and arguments
        cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
        
        # Check if we have cached data and if it's still valid (less than 2 minutes old)
        if cache_key in st.session_state:
            cached_data = st.session_state[cache_key]
            if isinstance(cached_data, dict) and 'timestamp' in cached_data:
                # Check if cache is still valid (2 minutes = 120 seconds)
                if time.time() - cached_data['timestamp'] < 120:
                    return cached_data['data']
        
        # If no cache or cache expired, call the function and cache the result
        result = func(*args, **kwargs)
        st.session_state[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }
        return result
    
    return wrapper

class ApprovalDashboardServices:
    """
    Service to handle approval dashboard operations and fetch approver roles and requests from Google Sheets.
    """
    
    def __init__(self):
        self.spreadsheet_id = SPREADSHEET_ID
        self.token_service = get_token_service()
        self.google_sheets_api_base = "https://sheets.googleapis.com/v4/spreadsheets"
    
    def clear_cache(self):
        """
        Clear all cached data to force fresh data retrieval.
        This should be called after any approval/rejection action.
        """
        # Clear the cache for get_pending_requests_for_approver
        cache_keys_to_clear = []
        for key in self.__dict__.keys():
            if hasattr(self, key) and hasattr(getattr(self, key), '__wrapped__'):
                # This is a cached function, clear its cache
                if hasattr(getattr(self, key), 'cache_clear'):
                    getattr(self, key).cache_clear()
        
        # Also clear any session state cache if available
        try:
            import streamlit as st
            for key in list(st.session_state.keys()):
                if any(cache_key in key for cache_key in [
                    'get_pending_requests_for_approver',
                    'ApprovalDashboardServices',
                    'responses_data',
                    'snf_user_data',
                    'get_distinct_databases'
                ]):
                    del st.session_state[key]
        except:
            pass  # Streamlit not available in this context
    
    def get_sheet_connection(self) -> Dict[str, Any]:
        """
        Get connection details for the Google Sheet.
        
        Returns:
            Dict[str, Any]: Connection details including spreadsheet_id, base_url, and access_token
            
        Raises:
            Exception: If connection fails or authentication issues
        """
        try:
            # Get a valid access token
            access_token = self.token_service.get_valid_access_token()
            
            # Return connection details
            return {
                "spreadsheet_id": self.spreadsheet_id,
                "base_url": self.google_sheets_api_base,
                "access_token": access_token,
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to establish Google Sheet connection: {str(e)}")
    
    def read_sheet_data(self, range_name: str) -> list:
        """
        Read data from a specific range in the Google Sheet.
        
        Args:
            range_name (str): The range to read (e.g., "responses!A:V")
            
        Returns:
            list: The sheet data as a 2D list
            
        Raises:
            Exception: If reading fails
        """
        try:
            connection = self.get_sheet_connection()
            
            # Build the API URL
            url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/{range_name}"
            
            # Make the request
            response = requests.get(url, headers=connection['headers'])
            response.raise_for_status()
            
            # Parse and return the response
            data = response.json()
            return data.get("values", [])
            
        except Exception as e:
            raise Exception(f"Failed to read sheet data: {str(e)}")
    
    def get_user_roles(self, user_email: str) -> List[str]:
        """
        Get the roles assigned to a user based on the L1-L5 sequential approval system.
        
        Args:
            user_email (str): The user's email address
            
        Returns:
            List[str]: List of roles assigned to the user
        """
        try:
            roles = []
            
            # Check RM Approvers sheet for L1-L5 approver assignments
            # Structure: User_Email, L1 Approver, L2 Approver, L3 Approver, L4 Approver, L5 Approver
            rm_approvers_data = self.read_sheet_data("rm_approvers!A:F")
            if rm_approvers_data and len(rm_approvers_data) > 1:
                headers = rm_approvers_data[0]
                
                # Check if user appears in ANY L1-L5 approver column
                for row in rm_approvers_data[1:]:
                    if len(row) >= 6:  # Need at least User_Email + L1-L5 columns
                        # Check L1-L5 approver columns (columns 1-5)
                        for i, level in enumerate(['L1', 'L2', 'L3', 'L4', 'L5']):
                            approver_col_idx = 1 + i  # L1 in column 1, L2 in column 2, etc.
                            if len(row) > approver_col_idx:
                                approver_email = row[approver_col_idx].strip()
                                if approver_email.lower() == user_email.lower():
                                    roles.append(f"{level} Approver")
            
            # Check User Manager sheet
            user_manager_data = self.read_sheet_data("user_manager!A:B")
            if user_manager_data and len(user_manager_data) > 1:
                headers = user_manager_data[0]
                manager_idx = headers.index("Manager_email") if "Manager_email" in headers else 1
                
                for row in user_manager_data[1:]:
                    if len(row) > manager_idx:
                        manager_email = row[manager_idx].strip()
                        if manager_email.lower() == user_email.lower():
                            roles.append("User Manager")  # User managers can approve user creation requests
                            break
            
            return list(set(roles))  # Remove duplicates
            
        except Exception as e:
            print(f"Error fetching user roles: {str(e)}")
            return []
    
    def is_approver(self, user_email: str) -> bool:
        """
        Check if a user is an approver.
        
        Args:
            user_email (str): The user's email address
            
        Returns:
            bool: True if user is an approver, False otherwise
        """
        roles = self.get_user_roles(user_email)
        return len(roles) > 0
    
    def get_pending_requests_for_approver(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Get pending requests that need approval from the specific approver using L1-L5 sequential approval system.
        Optimized version: Load all data once and process in memory to avoid API calls in loops.
        
        Args:
            user_email (str): The approver's email address
            
        Returns:
            List[Dict[str, Any]]: List of pending requests for approval
        """
        try:
            pending_requests = []
            
            # OPTIMIZATION: Load all required data once at the start
            
            # Load all data sources once
            responses_data = self.read_sheet_data("responses!A:AF")
            gsheet_responses_data = self.read_sheet_data("gsheet_unmasking_responses!A:AB")
            snf_user_data = self.read_sheet_data("snf_user!A:D")
            
            # Create BU lookup dictionary (BU is in column D)
            user_bu_lookup = {}
            if snf_user_data and len(snf_user_data) > 1:
                headers = snf_user_data[0]
                # Try different possible email column names
                email_idx = 0  # Default to first column
                if "email" in headers: 
                    email_idx = headers.index("email")
                elif "Email" in headers: 
                    email_idx = headers.index("Email")
                elif "EMAIL" in headers: 
                    email_idx = headers.index("EMAIL")
                
                # BU is in column D (index 3) as you specified
                bu_idx = 3
                if "BU" in headers: 
                    bu_idx = headers.index("BU")
                elif "bu" in headers:
                    bu_idx = headers.index("bu")
                for row in snf_user_data[1:]:
                    if len(row) > max(email_idx, bu_idx):
                        user_email_var = row[email_idx].strip().lower() if row[email_idx] else ""
                        bu_value = row[bu_idx].strip() if len(row) > bu_idx and row[bu_idx] else ""
                        
                        if user_email_var:  # Only add if email exists
                            user_bu_lookup[user_email_var] = bu_value
            
            # Process responses data efficiently - no API calls in loop!
            if responses_data and len(responses_data) > 1:
                headers = responses_data[0]
                
                # Find column indices for L1-L5 system
                request_id_idx = headers.index("REQUEST_ID") if "REQUEST_ID" in headers else 1
                request_type_idx = headers.index("REQUEST_TYPE") if "REQUEST_TYPE" in headers else 0
                email_idx = headers.index("EMAIL") if "EMAIL" in headers else 3
                entity_idx = headers.index("ENTITY") if "ENTITY" in headers else 2
                created_at_idx = headers.index("CREATED_AT") if "CREATED_AT" in headers else 18
                database_idx = headers.index("DATABASE") if "DATABASE" in headers else 4
                schema_idx = headers.index("SCHEMA") if "SCHEMA" in headers else 5
                table_name_idx = headers.index("TABLE_NAME") if "TABLE_NAME" in headers else 6
                column_name_idx = headers.index("COLUMN_NAME") if "COLUMN_NAME" in headers else 7
                reason_idx = headers.index("REASON_FOR_REQUEST") if "REASON_FOR_REQUEST" in headers else 8
                validity_idx = headers.index("VALIDITY_DAYS") if "VALIDITY_DAYS" in headers else 9
                reason_category_idx = headers.index("REASON_CATEGORY") if "REASON_CATEGORY" in headers else 10
                requesting_for_idx = headers.index("REQUESTING_FOR") if "REQUESTING_FOR" in headers else 11
                
                # L1-L5 approver and status column indices
                l1_approver_idx = headers.index("L1_APPROVER") if "L1_APPROVER" in headers else 16
                l2_approver_idx = headers.index("L2_APPROVER") if "L2_APPROVER" in headers else 17
                l3_approver_idx = headers.index("L3_APPROVER") if "L3_APPROVER" in headers else 18
                l4_approver_idx = headers.index("L4_APPROVER") if "L4_APPROVER" in headers else 19
                l5_approver_idx = headers.index("L5_APPROVER") if "L5_APPROVER" in headers else 20
                
                l1_status_idx = headers.index("L1_APPROVER_STATUS") if "L1_APPROVER_STATUS" in headers else 22
                l2_status_idx = headers.index("L2_APPROVER_STATUS") if "L2_APPROVER_STATUS" in headers else 23
                l3_status_idx = headers.index("L3_APPROVER_STATUS") if "L3_APPROVER_STATUS" in headers else 24
                l4_status_idx = headers.index("L4_APPROVER_STATUS") if "L4_APPROVER_STATUS" in headers else 25
                l5_status_idx = headers.index("L5_APPROVER_STATUS") if "L5_APPROVER_STATUS" in headers else 26
                
                # Initialize sequential service once
                from sequential_approval_service_fixed import SequentialApprovalService
                sequential_service = SequentialApprovalService()
                
                # Process all rows efficiently - NO API calls in loop!
                for row in responses_data[1:]:
                    if len(row) > max(request_id_idx, request_type_idx, email_idx, entity_idx, created_at_idx):
                        
                        request_id = row[request_id_idx] if len(row) > request_id_idx else ""
                        requester_email = row[email_idx] if len(row) > email_idx else ""
                        
                        if not request_id or not requester_email:
                            continue
                        
                        # Get approvers directly from the current row (they are in the responses sheet!)
                        approvers = {}
                        if len(row) > l1_approver_idx and row[l1_approver_idx].strip(): 
                            approvers['L1'] = row[l1_approver_idx].strip()
                        if len(row) > l2_approver_idx and row[l2_approver_idx].strip(): 
                            approvers['L2'] = row[l2_approver_idx].strip()
                        if len(row) > l3_approver_idx and row[l3_approver_idx].strip(): 
                            approvers['L3'] = row[l3_approver_idx].strip()
                        if len(row) > l4_approver_idx and row[l4_approver_idx].strip(): 
                            approvers['L4'] = row[l4_approver_idx].strip()
                        if len(row) > l5_approver_idx and row[l5_approver_idx].strip(): 
                            approvers['L5'] = row[l5_approver_idx].strip()
                        
                        if not approvers:
                            continue
                        
                        # Extract approval status from current row (no API call!)
                        approval_status = {}
                        if len(row) > l1_status_idx: approval_status['L1'] = row[l1_status_idx].strip()
                        if len(row) > l2_status_idx: approval_status['L2'] = row[l2_status_idx].strip()
                        if len(row) > l3_status_idx: approval_status['L3'] = row[l3_status_idx].strip()
                        if len(row) > l4_status_idx: approval_status['L4'] = row[l4_status_idx].strip()
                        if len(row) > l5_status_idx: approval_status['L5'] = row[l5_status_idx].strip()
                        
                        # Check if this user is the NEXT pending approver
                        next_approver_level = sequential_service.get_next_pending_approver(approval_status, approvers)
                        
                        # Check if request has been rejected at any level - if so, don't show to any subsequent approvers
                        is_rejected = any(status and status.lower() in ['rejected', 'reject'] for status in approval_status.values())
                        
                        if next_approver_level and approvers.get(next_approver_level) == user_email and not is_rejected:
                            # Get BU from lookup (no API call!)
                            bu = user_bu_lookup.get(requester_email.lower(), "")
                            
                            # Determine if this is a table/column request to show "Objective" instead of "Reason"
                            request_type = row[request_type_idx] if len(row) > request_type_idx else ""
                            is_table_column_request = request_type in ['Table request', 'Column request']
                            
                            # Create approval status summary for previous approvers
                            approval_status_summary = []
                            next_approver_index = int(next_approver_level[1]) if next_approver_level else 6  # L1=1, L2=2, etc.
                            
                            for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
                                level_index = int(level[1])  # L1=1, L2=2, etc.
                                
                                # Only show levels that are lower than the next approver level
                                if level_index < next_approver_index and level in approvers:
                                    status = approval_status.get(level, 'Pending')
                                    if status and status.lower() in ['approved', 'rejected']:
                                        approval_status_summary.append(f"{level} {status.upper()}")
                            
                            # Add current approver level as "PENDING" (only if not rejected)
                            if next_approver_level and not is_rejected:
                                approval_status_summary.append(f"{next_approver_level} PENDING")
                            
                            request = {
                                "Request ID": request_id,
                                "Request Type": request_type,
                                "Requestor": requester_email,
                                "Entity": row[entity_idx] if len(row) > entity_idx else "",
                                "BU": bu,
                                "Database": row[database_idx] if len(row) > database_idx else "",
                                "Schema": row[schema_idx] if len(row) > schema_idx else "",
                                "Table": row[table_name_idx] if len(row) > table_name_idx else "",
                                "Column": row[column_name_idx] if len(row) > column_name_idx else "",
                                "Reason Category": row[reason_category_idx] if len(row) > reason_category_idx else "",
                                # Map REASON_FOR_REQUEST as "Objective" for table/column requests, "Reason" for others
                                "Objective" if is_table_column_request else "Reason": row[reason_idx] if len(row) > reason_idx else "",
                                "Validity": row[validity_idx] if len(row) > validity_idx else "",
                                "Requesting For": row[requesting_for_idx] if len(row) > requesting_for_idx else "",
                                "Approval Type": next_approver_level,  # Shows L1, L2, etc.
                                "Approval Status": " | ".join(approval_status_summary) if approval_status_summary else "No approvals yet",
                                "Is Multi Approver": False,  # L1-L5 system doesn't use multi-approver concept
                                "Created At": row[created_at_idx] if len(row) > created_at_idx else "",
                                "Source": "responses"
                            }
                            pending_requests.append(request)
            
            # Fetch from user_responses worksheet (User Creation requests)
            user_responses_data = self.read_sheet_data("user_responses!A:Z")
            
            if user_responses_data and len(user_responses_data) > 1:
                headers = user_responses_data[0]
                
                # Find column indices
                request_id_idx = headers.index("Request_id") if "Request_id" in headers else 0
                user_idx = headers.index("User") if "User" in headers else 1
                entity_idx = headers.index("Entity") if "Entity" in headers else 3
                bu_idx = headers.index("BU") if "BU" in headers else 4
                rm_approver_idx = headers.index("RM_APPROVER") if "RM_APPROVER" in headers else 2
                approval_status_idx = headers.index("Approval_status") if "Approval_status" in headers else 6
                created_at_idx = headers.index("CREATED_AT") if "CREATED_AT" in headers else 5
                reason_idx = headers.index("Reason_for_request") if "Reason_for_request" in headers else 7
                
                for row in user_responses_data[1:]:
                    if len(row) > max(request_id_idx, user_idx, entity_idx, rm_approver_idx, approval_status_idx, created_at_idx):
                        
                        # Check if this request needs approval from this user (User Creation still uses RM approver)
                        rm_approver = row[rm_approver_idx] if len(row) > rm_approver_idx else ""
                        approval_status = row[approval_status_idx] if len(row) > approval_status_idx else "Pending"
                        
                        if rm_approver.lower() == user_email.lower() and approval_status.lower() == "pending":
                            request = {
                                "Request ID": row[request_id_idx] if len(row) > request_id_idx else "",
                                "Request Type": "User Creation",
                                "Requestor": row[user_idx] if len(row) > user_idx else "",
                                "Entity": row[entity_idx] if len(row) > entity_idx else "",
                                "BU": row[bu_idx] if len(row) > bu_idx else "",
                                "Database": "N/A",
                                "Schema": "N/A",
                                "Table": "N/A",
                                "Column": "N/A",
                                "Reason": row[reason_idx] if len(row) > reason_idx else "",
                                "Validity": "N/A",
                                "Approval Type": "RM",
                                "Created At": row[created_at_idx] if len(row) > created_at_idx else "",
                                "Source": "user_responses"
                            }
                            pending_requests.append(request)
            
            # Process GSheet unmasking requests
            if gsheet_responses_data and len(gsheet_responses_data) > 1:
                gsheet_headers = gsheet_responses_data[0]
                
                # Find column indices for GSheet requests
                gsheet_request_id_idx = gsheet_headers.index("REQUEST_ID") if "REQUEST_ID" in gsheet_headers else 0
                gsheet_user_email_idx = gsheet_headers.index("EMAIL") if "EMAIL" in gsheet_headers else 2
                gsheet_user_name_idx = gsheet_headers.index("USER_NAME") if "USER_NAME" in gsheet_headers else 1
                gsheet_entity_idx = gsheet_headers.index("ENTITY") if "ENTITY" in gsheet_headers else 3
                gsheet_spreadsheet_id_idx = gsheet_headers.index("SPREADSHEET_ID") if "SPREADSHEET_ID" in gsheet_headers else 5
                gsheet_named_range_idx = gsheet_headers.index("NAMED_RANGE") if "NAMED_RANGE" in gsheet_headers else 6
                gsheet_who_has_access_idx = gsheet_headers.index("WHO HAS ACCESS TO THIS SHEET") if "WHO HAS ACCESS TO THIS SHEET" in gsheet_headers else 7
                gsheet_end_user_desc_idx = gsheet_headers.index("END_USER_DESCRIPTION") if "END_USER_DESCRIPTION" in gsheet_headers else 8
                gsheet_use_case_idx = gsheet_headers.index("USE_CASE") if "USE_CASE" in gsheet_headers else 9
                gsheet_validity_idx = gsheet_headers.index("VALIDITY_DAYS") if "VALIDITY_DAYS" in gsheet_headers else 10
                gsheet_remarks_idx = gsheet_headers.index("REMARKS") if "REMARKS" in gsheet_headers else 11
                gsheet_created_at_idx = gsheet_headers.index("CREATED_AT") if "CREATED_AT" in gsheet_headers else 16
                
                # L1-L5 approver and status column indices for GSheet
                gsheet_l1_approver_idx = gsheet_headers.index("L1_APPROVER") if "L1_APPROVER" in gsheet_headers else 12
                gsheet_l2_approver_idx = gsheet_headers.index("L2_APPROVER") if "L2_APPROVER" in gsheet_headers else 13
                gsheet_l3_approver_idx = gsheet_headers.index("L3_APPROVER") if "L3_APPROVER" in gsheet_headers else 14
                gsheet_l4_approver_idx = gsheet_headers.index("L4_APPROVER") if "L4_APPROVER" in gsheet_headers else 15
                gsheet_l5_approver_idx = gsheet_headers.index("L5_APPROVER") if "L5_APPROVER" in gsheet_headers else 16
                
                gsheet_l1_status_idx = gsheet_headers.index("L1_APPROVER_STATUS") if "L1_APPROVER_STATUS" in gsheet_headers else 17
                gsheet_l2_status_idx = gsheet_headers.index("L2_APPROVER_STATUS") if "L2_APPROVER_STATUS" in gsheet_headers else 18
                gsheet_l3_status_idx = gsheet_headers.index("L3_APPROVER_STATUS") if "L3_APPROVER_STATUS" in gsheet_headers else 19
                gsheet_l4_status_idx = gsheet_headers.index("L4_APPROVER_STATUS") if "L4_APPROVER_STATUS" in gsheet_headers else 20
                gsheet_l5_status_idx = gsheet_headers.index("L5_APPROVER_STATUS") if "L5_APPROVER_STATUS" in gsheet_headers else 21
                
                # Process GSheet requests
                for row in gsheet_responses_data[1:]:
                    if len(row) > max(gsheet_request_id_idx, gsheet_user_email_idx, gsheet_created_at_idx):
                        
                        request_id = row[gsheet_request_id_idx] if len(row) > gsheet_request_id_idx else ""
                        requester_email = row[gsheet_user_email_idx] if len(row) > gsheet_user_email_idx else ""
                        
                        if not request_id or not requester_email:
                            continue
                        
                        # Get approvers from GSheet row
                        approvers = {}
                        if len(row) > gsheet_l1_approver_idx and row[gsheet_l1_approver_idx].strip(): 
                            approvers['L1'] = row[gsheet_l1_approver_idx].strip()
                        if len(row) > gsheet_l2_approver_idx and row[gsheet_l2_approver_idx].strip(): 
                            approvers['L2'] = row[gsheet_l2_approver_idx].strip()
                        if len(row) > gsheet_l3_approver_idx and row[gsheet_l3_approver_idx].strip(): 
                            approvers['L3'] = row[gsheet_l3_approver_idx].strip()
                        if len(row) > gsheet_l4_approver_idx and row[gsheet_l4_approver_idx].strip(): 
                            approvers['L4'] = row[gsheet_l4_approver_idx].strip()
                        if len(row) > gsheet_l5_approver_idx and row[gsheet_l5_approver_idx].strip(): 
                            approvers['L5'] = row[gsheet_l5_approver_idx].strip()
                        
                        if not approvers:
                            continue
                        
                        # Extract approval status from GSheet row
                        approval_status = {}
                        if len(row) > gsheet_l1_status_idx: approval_status['L1'] = row[gsheet_l1_status_idx].strip()
                        if len(row) > gsheet_l2_status_idx: approval_status['L2'] = row[gsheet_l2_status_idx].strip()
                        if len(row) > gsheet_l3_status_idx: approval_status['L3'] = row[gsheet_l3_status_idx].strip()
                        if len(row) > gsheet_l4_status_idx: approval_status['L4'] = row[gsheet_l4_status_idx].strip()
                        if len(row) > gsheet_l5_status_idx: approval_status['L5'] = row[gsheet_l5_status_idx].strip()
                        
                        # # Check if this approver needs to approve this request
                        # needs_approval = False
                        # approver_level = None
                        
                        # for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
                        #     if approvers.get(level, '').lower() == user_email.lower():
                        #         current_status = approval_status.get(level, 'Pending')
                        #         if current_status.lower() == 'pending':
                        #             needs_approval = True
                        #             approver_level = level
                        #             break
                        
                        # if needs_approval:

                        # Check if this user is the NEXT pending approver (same as column unhashing)
                        next_approver_level = sequential_service.get_next_pending_approver(approval_status, approvers)
                        
                        # Check if request has been rejected at any level - if so, don't show to any subsequent approvers
                        is_rejected = any(status and status.lower() in ['rejected', 'reject'] for status in approval_status.values())
                        
                        if next_approver_level and approvers.get(next_approver_level) == user_email and not is_rejected:
                            # Get BU for the requester
                            requester_bu = user_bu_lookup.get(requester_email.lower(), "")
                            
                            # Create approval status summary for previous approvers (same logic as table/column requests)
                            approval_status_summary = []
                            next_approver_index = int(next_approver_level[1]) if next_approver_level else 6  # L1=1, L2=2, etc.
                            
                            for level in ['L1', 'L2', 'L3', 'L4', 'L5']:
                                level_index = int(level[1])  # L1=1, L2=2, etc.
                                
                                # Only show levels that are lower than the next approver level
                                if level_index < next_approver_index and level in approvers:
                                    status = approval_status.get(level, 'Pending')
                                    if status and status.lower() in ['approved', 'rejected']:
                                        approval_status_summary.append(f"{level} {status.upper()}")
                            
                            # Add current approver level as "PENDING" (only if not rejected)
                            if next_approver_level and not is_rejected:
                                approval_status_summary.append(f"{next_approver_level} PENDING")
                            
                            request = {
                                "Request ID": request_id,
                                "Request Type": "GSheet Unmasking",
                                "Requestor": requester_email,  # Use email instead of name
                                "Entity": row[gsheet_entity_idx] if len(row) > gsheet_entity_idx else "",
                                "BU": requester_bu,
                                "Database": "Google Sheets",
                                "Spreadsheet ID": row[gsheet_spreadsheet_id_idx] if len(row) > gsheet_spreadsheet_id_idx else "",
                                "Named Range": row[gsheet_named_range_idx] if len(row) > gsheet_named_range_idx else "",
                                "Who Has Access": row[gsheet_who_has_access_idx] if len(row) > gsheet_who_has_access_idx else "",
                                "End User Description": row[gsheet_end_user_desc_idx] if len(row) > gsheet_end_user_desc_idx else "",
                                "Use Case": row[gsheet_use_case_idx] if len(row) > gsheet_use_case_idx else "",
                                "Objective": row[gsheet_remarks_idx] if len(row) > gsheet_remarks_idx else "",
                                "Validity": f"{row[gsheet_validity_idx] if len(row) > gsheet_validity_idx else ''} days",
                                "Approval Type": next_approver_level,
                                "Approval Status": " | ".join(approval_status_summary) if approval_status_summary else "No approvals yet",
                                "Created At": row[gsheet_created_at_idx] if len(row) > gsheet_created_at_idx else "",
                                "Source": "gsheet_unmasking_responses"
                            }
                            pending_requests.append(request)
            
            # Sort by Created At (latest first)
            pending_requests.sort(key=lambda x: x.get("Created At", ""), reverse=True)
            
            return pending_requests
            
        except Exception as e:
            print(f"Error fetching pending requests: {str(e)}")
            return []
    
    def get_bu_from_snf_user(self, user_email: str) -> str:
        """
        Get BU (Business Unit) for a user from the snf_user worksheet.
        
        Args:
            user_email (str): The user's email address
            
        Returns:
            str: The BU or empty string if not found
        """
        try:
            # Read the snf_user worksheet data
            snf_user_data = self.read_sheet_data("snf_user!A:D")
            
            if not snf_user_data or len(snf_user_data) < 2:  # Need at least header + 1 data row
                return ""
            
            # Skip header row and search for matching user email
            for row in snf_user_data[1:]:  # Skip header row
                if len(row) >= 4:  # Need at least 4 columns: Entity, Email, Role, BU
                    sheet_entity = row[0].strip()
                    sheet_email = row[1].strip()
                    sheet_role = row[2].strip()
                    sheet_bu = row[3].strip()
                    
                    if sheet_email.lower() == user_email.lower():
                        return sheet_bu
            
            # If not found, return empty string
            return ""
            
        except Exception as e:
            print(f"Error fetching BU from snf_user: {str(e)}")
            return ""
    
    def get_distinct_databases(self) -> List[str]:
        """
        Get distinct database names from responses worksheet.
        
        Returns:
            List[str]: List of distinct database names
        """
        try:
            databases = set()
            responses_data = self.read_sheet_data("responses!A:W")
            
            if responses_data and len(responses_data) > 1:
                headers = responses_data[0]
                database_idx = headers.index("DATABASE") if "DATABASE" in headers else 4
                
                for row in responses_data[1:]:
                    if len(row) > database_idx:
                        database = row[database_idx].strip()
                        if database:
                            databases.add(database)
            
            return sorted(list(databases))
            
        except Exception as e:
            print(f"Error fetching distinct databases: {str(e)}")
            return []
    
    def get_distinct_databases_from_pending_requests(self, user_email: str) -> List[str]:
        """
        Get distinct database names from pending requests for a specific approver.
        
        Args:
            user_email (str): The approver's email address
            
        Returns:
            List[str]: List of distinct database names from pending requests
        """
        try:
            # Get pending requests for the user
            pending_requests = self.get_pending_requests_for_approver(user_email)
            
            # Extract unique databases from pending requests
            databases = set()
            for request in pending_requests:
                database = request.get("Database", "")
                if database and database != "N/A":
                    databases.add(database)
            
            return sorted(list(databases))
            
        except Exception as e:
            print(f"Error fetching distinct databases from pending requests: {str(e)}")
            return []
    
    def update_user_creation_approval(self, request_id: str, approver_email: str, approval_status: str) -> bool:
        """
        Update approval status for user creation request in user_responses worksheet.
        
        Args:
            request_id (str): The request ID to update
            approver_email (str): The approver's email
            approval_status (str): The approval status ("Approved" or "Rejected")
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            connection = self.get_sheet_connection()
            
            # First, find the row number for the request
            user_responses_data = self.read_sheet_data("user_responses!A:Z")
            
            if not user_responses_data or len(user_responses_data) <= 1:
                return False
            
            headers = user_responses_data[0]
            request_id_idx = headers.index("Request_id") if "Request_id" in headers else 0
            approval_status_idx = headers.index("Approval_status") if "Approval_status" in headers else 6
            approval_ts_idx = headers.index("Approval_ts") if "Approval_ts" in headers else 7
            
            # Find the row with matching request_id
            row_number = None
            for i, row in enumerate(user_responses_data[1:], start=2):  # Start from row 2 (1-indexed)
                if len(row) > request_id_idx and row[request_id_idx] == request_id:
                    row_number = i
                    break
            
            if row_number is None:
                return False
            
            # Prepare the update data
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Update approval status
            status_range = f"user_responses!G{row_number}"
            status_body = {
                "values": [[approval_status]]
            }
            
            status_url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/{status_range}?valueInputOption=RAW"
            status_response = requests.put(status_url, headers=connection['headers'], json=status_body)
            status_response.raise_for_status()
            
            # Update approval timestamp
            ts_range = f"user_responses!H{row_number}"
            ts_body = {
                "values": [[current_timestamp]]
            }
            
            ts_url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/{ts_range}?valueInputOption=RAW"
            ts_response = requests.put(ts_url, headers=connection['headers'], json=ts_body)
            ts_response.raise_for_status()
            
            # Send email notification for user creation (user creation doesn't use sequential approval)
            email_result = self.send_user_creation_approval_email(request_id, approval_status, approver_email)
            if not email_result['success']:
                print(f"Warning: Failed to send email notification: {email_result['message']}")
            
            # Clear cache to force immediate refresh
            self.clear_cache()
            
            return True
            
        except Exception as e:
            print(f"Error updating user creation approval: {str(e)}")
            return False
    
    def update_table_column_approval(self, request_id: str, approver_email: str, approval_type: str, approval_status: str) -> bool:
        """
        Update approval status for table/column request using L1-L5 sequential approval system.
        This method now delegates to the sequential approval service instead of using the old RM/Data system.
        
        Args:
            request_id (str): The request ID to update
            approver_email (str): The approver's email
            approval_type (str): Ignored - using L1-L5 system instead
            approval_status (str): The approval status ("Approved" or "Rejected")
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        print(f"DEBUG: update_table_column_approval called in approvaldashboardservices - delegating to sequential approval system")
        print(f"DEBUG: Request: {request_id}, Approver: {approver_email}, Status: {approval_status}")
        try:
            # Delegate to the sequential approval service which handles L1-L5 approvals and emails
            from sequential_approval_service_fixed import SequentialApprovalService
            sequential_service = SequentialApprovalService()
            
            # Convert "Rejected" to "Reject" for the sequential approval service
            decision = "Reject" if approval_status == "Rejected" else approval_status
            
            result = sequential_service.handle_approval_decision(
                request_id, approver_email, decision
            )
            
            if result.get('success'):
                print(f"✅ Sequential approval updated successfully: {result.get('message', 'Unknown')}")
                # Clear cache to force immediate refresh
                self.clear_cache()
                return True
            else:
                print(f"❌ Sequential approval failed: {result.get('message', 'Unknown error')}")
                return False
            
        except Exception as e:
            print(f"❌ Error in sequential approval: {str(e)}")
            return False
    
    def bulk_approve_requests(self, requests: List[Dict[str, Any]], approver_email: str, approval_status: str) -> Dict[str, Any]:
        """
        Bulk approve/reject multiple requests.
        
        Args:
            requests (List[Dict[str, Any]]): List of requests to approve/reject
            approver_email (str): The approver's email
            approval_status (str): The approval status ("Approved" or "Rejected")
            
        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        try:
            results = {
                "total": len(requests),
                "successful": 0,
                "failed": 0,
                "errors": []
            }
            
            for request in requests:
                request_id = request.get("Request ID", "")
                request_type = request.get("Request Type", "")
                approval_type = request.get("Approval Type", "")
                
                success = False
                
                try:
                    if request_type == 'User Creation':
                        # Update user creation approval
                        success = self.update_user_creation_approval(request_id, approver_email, approval_status)
                    else:
                        # Update table/column approval (handles both single and multi-approver)
                        success = self.update_table_column_approval(request_id, approver_email, approval_type, approval_status)
                    
                    if success:
                        results["successful"] += 1
                        # Note: Sequential approval is now handled directly within update_table_column_approval
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Failed to update {request_id}")
                        
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Error updating {request_id}: {str(e)}")
            
            return results
            
        except Exception as e:
            return {
                "total": len(requests),
                "successful": 0,
                "failed": len(requests),
                "errors": [f"Bulk operation failed: {str(e)}"]
            }
    
    def send_user_creation_approval_email(self, request_id: str, approval_status: str, approver_email: str) -> Dict[str, Any]:
        """
        Send approval notification email for user creation request.
        
        Args:
            request_id (str): The request ID
            approval_status (str): The approval status ("Approved" or "Rejected")
            approver_email (str): The approver's email
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Get request details from user_responses sheet
            user_responses_data = self.read_sheet_data("user_responses!A:Z")
            
            if not user_responses_data or len(user_responses_data) <= 1:
                return {
                    'success': False,
                    'message': 'Failed to fetch request details',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'No data found in user_responses sheet'
                }
            
            headers = user_responses_data[0]
            request_id_idx = headers.index("Request_id") if "Request_id" in headers else 0
            user_idx = headers.index("User") if "User" in headers else 1
            entity_idx = headers.index("Entity") if "Entity" in headers else 3
            bu_idx = headers.index("BU") if "BU" in headers else 4
            reason_idx = headers.index("Reason_for_request") if "Reason_for_request" in headers else 7
            
            # Find the request
            request_data = None
            for row in user_responses_data[1:]:
                if len(row) > request_id_idx and row[request_id_idx] == request_id:
                    request_data = {
                        'request_id': row[request_id_idx] if len(row) > request_id_idx else '',
                        'user_email': row[user_idx] if len(row) > user_idx else '',
                        'user_name': row[user_idx].split('@')[0] if len(row) > user_idx and '@' in row[user_idx] else row[user_idx] if len(row) > user_idx else '',
                        'entity': row[entity_idx] if len(row) > entity_idx else '',
                        'business_unit': row[bu_idx] if len(row) > bu_idx else '',
                        'reason': row[reason_idx] if len(row) > reason_idx else ''
                    }
                    break
            
            if not request_data:
                return {
                    'success': False,
                    'message': 'Request not found',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': f'Request ID {request_id} not found'
                }
            
            # Create email content
            email_content = create_approval_notification_email(request_data, approval_status, approver_email)
            
            # Send email to user
            result = send_email(
                to_email=request_data['user_email'],
                subject=f"User Creation Request {approval_status} - {request_id}",
                content=email_content
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send approval notification: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def send_table_column_approval_email(self, request_id: str, approval_type: str, approval_status: str, approver_email: str) -> Dict[str, Any]:
        """
        Send approval notification email for table/column request using sequential approval flow.
        
        Args:
            request_id (str): The request ID
            approval_type (str): The type of approval ("RM" or "Data") - deprecated, now uses L1-L5 system
            approval_status (str): The approval status ("Approved" or "Rejected")
            approver_email (str): The approver's email
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Use the sequential approval service for proper L1-L5 flow
            from sequential_approval_service_fixed import SequentialApprovalService
            sequential_service = SequentialApprovalService()
            
            # Get request details from responses sheet (using new L1-L5 columns)
            responses_data = self.read_sheet_data("responses!A:AF")  # Extended range for L1-L5 columns
            
            if not responses_data or len(responses_data) <= 1:
                return {
                    'success': False,
                    'message': 'Failed to fetch request details',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'No data found in responses sheet'
                }
            
            headers = responses_data[0]
            request_id_idx = headers.index("REQUEST_ID") if "REQUEST_ID" in headers else 1
            email_idx = headers.index("EMAIL") if "EMAIL" in headers else 3
            
            # Find the request to build request_data
            request_data = None
            for row in responses_data[1:]:
                if len(row) > request_id_idx and row[request_id_idx] == request_id:
                    request_data = {
                        'request_id': request_id,
                        'user_email': row[email_idx] if len(row) > email_idx else '',
                        'requester_email': row[email_idx] if len(row) > email_idx else '',
                        'user_name': row[email_idx].split('@')[0] if len(row) > email_idx and '@' in row[email_idx] else ''
                    }
                    break
            
            if not request_data:
                return {
                    'success': False,
                    'message': 'Request not found',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': f'Request ID {request_id} not found'
                }
            
            # Use sequential approval service to handle the approval and next approver notification
            result = sequential_service.handle_approval_decision(
                request_id, approver_email, approval_status
            )
            
            if result.get('success'):
                print(f"✅ Email notification sent for sequential approval: {request_id}")
                return {
                    'success': True,
                    'message': f'Sequential approval processed: {result.get("message", "Unknown")}',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                print(f"❌ Sequential approval failed: {result.get('message', 'Unknown error')}")
                return {
                    'success': False,
                    'message': f'Sequential approval failed: {result.get("message", "Unknown error")}',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': result.get('error', 'Unknown error')
                }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to process sequential approval: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def send_multi_approver_notification_email(self, request_id: str, approval_status: str, approver_email: str) -> Dict[str, Any]:
        """
        Send approval notification email for multi-approver scenario (same person is both RM and Data approver).
        
        Args:
            request_id (str): The request ID
            approval_status (str): The approval status ("Approved" or "Rejected")
            approver_email (str): The approver's email
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Get request details from responses sheet
            responses_data = self.read_sheet_data("responses!A:W")
            
            if not responses_data or len(responses_data) <= 1:
                return {
                    'success': False,
                    'message': 'Failed to fetch request details',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'No data found in responses sheet'
                }
            
            headers = responses_data[0]
            request_id_idx = headers.index("REQUEST_ID") if "REQUEST_ID" in headers else 1
            request_type_idx = headers.index("REQUEST_TYPE") if "REQUEST_TYPE" in headers else 0
            email_idx = headers.index("EMAIL") if "EMAIL" in headers else 3
            entity_idx = headers.index("ENTITY") if "ENTITY" in headers else 2
            database_idx = headers.index("DATABASE") if "DATABASE" in headers else 4
            schema_idx = headers.index("SCHEMA") if "SCHEMA" in headers else 5
            table_name_idx = headers.index("TABLE_NAME") if "TABLE_NAME" in headers else 6
            column_name_idx = headers.index("COLUMN_NAME") if "COLUMN_NAME" in headers else 7
            reason_idx = headers.index("REASON_FOR_REQUEST") if "REASON_FOR_REQUEST" in headers else 8
            validity_idx = headers.index("VALIDITY_DAYS") if "VALIDITY_DAYS" in headers else 9
            requesting_for_idx = headers.index("REQUESTING_FOR") if "REQUESTING_FOR" in headers else 11
            
            # Find the request
            request_data = None
            for row in responses_data[1:]:
                if len(row) > request_id_idx and row[request_id_idx] == request_id:
                    request_data = {
                        'request_id': row[request_id_idx] if len(row) > request_id_idx else '',
                        'user_email': row[email_idx] if len(row) > email_idx else '',
                        'user_name': row[email_idx].split('@')[0] if len(row) > email_idx and '@' in row[email_idx] else row[email_idx] if len(row) > email_idx else '',
                        'entity': row[entity_idx] if len(row) > entity_idx else '',
                        'database': row[database_idx] if len(row) > database_idx else '',
                        'schema': row[schema_idx] if len(row) > schema_idx else '',
                        'table': row[table_name_idx] if len(row) > table_name_idx else '',
                        'column': row[column_name_idx] if len(row) > column_name_idx else '',
                        'reason': row[reason_idx] if len(row) > reason_idx else '',
                        'validity_days': row[validity_idx] if len(row) > validity_idx else '',
                        'requesting_for_value': row[requesting_for_idx] if len(row) > requesting_for_idx else '',
                        'request_type': row[request_type_idx] if len(row) > request_type_idx else ''
                    }
                    break
            
            if not request_data:
                return {
                    'success': False,
                    'message': 'Request not found',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': f'Request ID {request_id} not found'
                }
            
            # Create email content for multi-approver
            email_content = create_multi_approver_notification_email(request_data, approval_status, approver_email)
            
            # Send email to user
            result = send_email(
                to_email=request_data['user_email'],
                subject=f"{request_data['request_type']} Request {approval_status} - {request_id}",
                content=email_content
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send approval notification: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }

# Global approval dashboard services instance
approval_dashboard_services = ApprovalDashboardServices()

def get_approval_dashboard_services() -> ApprovalDashboardServices:
    """
    Get the global approval dashboard services instance.
    
    Returns:
        ApprovalDashboardServices: The global approval dashboard services instance
    """
    return approval_dashboard_services

def get_user_roles(user_email: str) -> List[str]:
    """
    Convenience function to get user roles.
    
    Args:
        user_email (str): The user's email address
        
    Returns:
        List[str]: List of user roles
    """
    return approval_dashboard_services.get_user_roles(user_email)

def is_approver(user_email: str) -> bool:
    """
    Convenience function to check if user is an approver.
    
    Args:
        user_email (str): The user's email address
        
    Returns:
        bool: True if user is an approver
    """
    return approval_dashboard_services.is_approver(user_email)

def get_pending_requests_for_approver(user_email: str) -> List[Dict[str, Any]]:
    """
    Convenience function to get pending requests for approver.
    
    Args:
        user_email (str): The approver's email address
        
    Returns:
        List[Dict[str, Any]]: List of pending requests
    """
    return approval_dashboard_services.get_pending_requests_for_approver(user_email)

def get_distinct_databases() -> List[str]:
    """
    Convenience function to get distinct databases.
    
    Returns:
        List[str]: List of distinct database names
    """
    return approval_dashboard_services.get_distinct_databases()

def get_distinct_databases_from_pending_requests(user_email: str) -> List[str]:
    """
    Convenience function to get distinct databases from pending requests.
    
    Args:
        user_email (str): The approver's email address
        
    Returns:
        List[str]: List of distinct database names from pending requests
    """
    return approval_dashboard_services.get_distinct_databases_from_pending_requests(user_email)

def update_user_creation_approval(request_id: str, approver_email: str, approval_status: str) -> bool:
    """
    Convenience function to update user creation approval.
    
    Args:
        request_id (str): The request ID to update
        approver_email (str): The approver's email
        approval_status (str): The approval status ("Approved" or "Rejected")
        
    Returns:
        bool: True if update was successful
    """
    return approval_dashboard_services.update_user_creation_approval(request_id, approver_email, approval_status)

def update_table_column_approval(request_id: str, approver_email: str, approval_type: str, approval_status: str) -> bool:
    """
    Convenience function to update table/column approval.
    
    Args:
        request_id (str): The request ID to update
        approver_email (str): The approver's email
        approval_type (str): The type of approval ("RM" or "Data")
        approval_status (str): The approval status ("Approved" or "Rejected")
        
    Returns:
        bool: True if update was successful
    """
    return approval_dashboard_services.update_table_column_approval(request_id, approver_email, approval_type, approval_status)

def bulk_approve_requests(requests: List[Dict[str, Any]], approver_email: str, approval_status: str) -> Dict[str, Any]:
    """
    Convenience function to bulk approve/reject requests.
    
    Args:
        requests (List[Dict[str, Any]]): List of requests to approve/reject
        approver_email (str): The approver's email
        approval_status (str): The approval status ("Approved" or "Rejected")
        
    Returns:
        Dict[str, Any]: Results of the bulk operation
    """
    return approval_dashboard_services.bulk_approve_requests(requests, approver_email, approval_status)

def send_user_creation_approval_email_dashboard(request_id: str, approval_status: str, approver_email: str) -> Dict[str, Any]:
    """
    Convenience function to send user creation approval email.
    
    Args:
        request_id (str): The request ID
        approval_status (str): The approval status ("Approved" or "Rejected")
        approver_email (str): The approver's email
        
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    return approval_dashboard_services.send_user_creation_approval_email(request_id, approval_status, approver_email)

def send_table_column_approval_email_dashboard(request_id: str, approval_type: str, approval_status: str, approver_email: str) -> Dict[str, Any]:
    """
    Convenience function to send table/column approval email.
    
    Args:
        request_id (str): The request ID
        approval_type (str): The type of approval ("RM" or "Data")
        approval_status (str): The approval status ("Approved" or "Rejected")
        approver_email (str): The approver's email
        
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    return approval_dashboard_services.send_table_column_approval_email(request_id, approval_type, approval_status, approver_email)

def send_multi_approver_notification_email_dashboard(request_id: str, approval_status: str, approver_email: str) -> Dict[str, Any]:
    """
    Convenience function to send multi-approver notification email.
    
    Args:
        request_id (str): The request ID
        approval_status (str): The approval status ("Approved" or "Rejected")
        approver_email (str): The approver's email
        
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    return approval_dashboard_services.send_multi_approver_notification_email(request_id, approval_status, approver_email)
