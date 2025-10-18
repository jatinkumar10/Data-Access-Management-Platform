import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import requests

# Add parent directory to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import SPREADSHEET_ID
from services.google_sheets_service import GoogleSheetsService
from services.emailhandler import EmailHandler

class SequentialApprovalService:
    """
    Service to handle sequential approval workflow for requests.
    Manages L1 to L5 approver chain and approval state tracking.
    """
    
    def __init__(self):
        self.spreadsheet_id = SPREADSHEET_ID
        self.sheets_service = GoogleSheetsService()
        self.email_handler = EmailHandler()
        self.approver_levels = ['L1', 'L2', 'L3', 'L4', 'L5']
    
    def get_approvers_for_request(self, request_data: dict) -> Dict[str, Optional[str]]:
        """
        Get the L1-L5 approvers for a specific request from the RM_Approvers sheet.
        
        Args:
            request_data (dict): Request data containing entity and business unit
            
        Returns:
            Dict[str, Optional[str]]: Dictionary with L1-L5 approver emails
        """
        try:
            # Get RM Approvers sheet data
            rm_approvers_df, _ = self.sheets_service.get_sheet_data(worksheet_name="rm_approvers")
            
            if rm_approvers_df.empty:
                return {level: None for level in self.approver_levels}
                
            # Convert DataFrame to list of lists (like the original format)
            rm_approvers_data = [rm_approvers_df.columns.tolist()] + rm_approvers_df.values.tolist()
            
            if not rm_approvers_data or len(rm_approvers_data) < 2:
                return {level: None for level in self.approver_levels}
            
            # Get user email from request data
            user_email = request_data.get('user_email', request_data.get('requester_email', ''))
            
            # Find matching row based on user email
            # Structure: User_Email, L1 Approver, L2 Approver, L3 Approver, L4 Approver, L5 Approver
            matching_row = None
            
            for row in rm_approvers_data[1:]:  # Skip header
                if len(row) >= 2 and row[0].strip().lower() == user_email.lower():
                    matching_row = row
                    break
            
            if not matching_row:
                return {level: None for level in self.approver_levels}
            
            # Extract L1-L5 approvers (they are in columns 1-5 after User_Email)
            approvers = {}
            for i, level in enumerate(self.approver_levels):
                col_index = 1 + i  # L1 in column 1, L2 in column 2, etc. (after User_Email column)
                if col_index < len(matching_row):
                    # approver_email = matching_row[col_index].strip()
                    # approvers[level] = approver_email if approver_email else None
                    cell_value = matching_row[col_index]
                    # Handle None values and empty strings safely
                    if cell_value is not None:
                        approver_email = str(cell_value).strip()
                        approvers[level] = approver_email if approver_email else None
                    else:
                        approvers[level] = None
                else:
                    approvers[level] = None
            
            return approvers
            
        except Exception as e:
            print(f"Error getting approvers for request: {str(e)}")
            return {level: None for level in self.approver_levels}
    
    def get_table_request_approvers(self, request_data: dict) -> Dict[str, Optional[str]]:
        """
        Get approvers for table requests using n-3 rule where n is total approvers.
        Minimum 1 approver is always required.
        For CFSPL databases, adds sonali.bhat1@cars24.com as additional approver.
        
        Args:
            request_data (dict): Request data containing user information and database name
            
        Returns:
            Dict[str, Optional[str]]: Dictionary with required approver levels for table requests
        """
        try:
            # Get all defined approvers for this user
            all_approvers = self.get_approvers_for_request(request_data)
            
            # Count non-empty approvers
            defined_approvers = [(level, email) for level, email in all_approvers.items() if email and email.strip()]
            total_approvers = len(defined_approvers)
            
            # Calculate required approvers (n-3, minimum 1)
            required_count = max(1, total_approvers - 3)
            
            # Take first 'required_count' approvers
            table_approvers = {}
            for i, (level, email) in enumerate(defined_approvers[:required_count]):
                table_approvers[level] = email
            
            # Check if database name contains 'CFSPL' and add additional approver
            database_name = request_data.get('database', '').upper()
            if 'CFSPL' in database_name:
                # Find the next available level to add the CFSPL approver
                used_levels = set(table_approvers.keys())
                available_levels = [level for level in ['L1', 'L2', 'L3', 'L4', 'L5'] if level not in used_levels]
                
                if available_levels:
                    next_level = available_levels[0]
                    table_approvers[next_level] = 'sonali.bhat@cars24.com'
                    print(f"CFSPL database detected ({database_name}): Added sonali.bhat1@cars24.com as {next_level}")
                else:
                    # If all levels are used, replace the last one with CFSPL approver
                    print(f"CFSPL database detected ({database_name}): All levels used, cannot add additional approver")
            
            print(f"Table request approvers: Total={total_approvers}, Required={required_count}, Selected={list(table_approvers.keys())}, Database={database_name}")
            return table_approvers
            
        except Exception as e:
            print(f"Error getting table request approvers: {str(e)}")
            # Fallback to L1 only
            all_approvers = self.get_approvers_for_request(request_data)
            return {'L1': all_approvers.get('L1')} if all_approvers.get('L1') else {}


    def get_approval_status_from_responses(self, request_id: str) -> Dict[str, str]:
        """
        Get the current approval status for each level from both responses and gsheet_unmasking_responses sheets.
        
        Args:
            request_id (str): The request ID to check
            
        Returns:
            Dict[str, str]: Status for each approver level (Approved/Pending/Reject)
        """
        try:
            from services.formservices import FormServices
            form_services = FormServices()
            
            # First try responses sheet
            data = form_services.read_sheet_data("responses!A:Z")
            request_row = None
            sheet_type = None
            
            if data and len(data) >= 2:
                for row in data[1:]:  # Skip header
                    if len(row) >= 2 and row[1].strip() == request_id:  # REQUEST_ID is in column B
                        request_row = row
                        sheet_type = 'responses'
                        break
            
            # If not found in responses, try gsheet_unmasking_responses sheet
            if not request_row:
                gsheet_data = form_services.read_sheet_data("gsheet_unmasking_responses!A:AB")
                if gsheet_data and len(gsheet_data) >= 2:
                    for row in gsheet_data[1:]:  # Skip header
                        if len(row) >= 1 and row[0].strip() == request_id:  # REQUEST_ID is in column A
                            request_row = row
                            sheet_type = 'gsheet_unmasking_responses'
                            break
            
            if not request_row:
                return {level: 'Pending' for level in self.approver_levels}
            
            # Extract L1-L5 status based on sheet type
            approval_status = {}
            
            if sheet_type == 'responses':
                # Regular responses sheet: L1-L5 status at positions 22-26 (columns W, X, Y, Z, AA)
                status_columns = {'L1': 22, 'L2': 23, 'L3': 24, 'L4': 25, 'L5': 26}
            else:  # gsheet_unmasking_responses
                # GSheet responses sheet: L1-L5 status at positions 18-22 (columns S, T, U, V, W)
                status_columns = {'L1': 18, 'L2': 19, 'L3': 20, 'L4': 21, 'L5': 22}
            
            for level, col_index in status_columns.items():
                if col_index < len(request_row):
                    status = request_row[col_index].strip()
                    approval_status[level] = status if status in ['Approved', 'Rejected'] else 'Pending'
                else:
                    approval_status[level] = 'Pending'
            
            return approval_status
            
        except Exception as e:
            print(f"Error getting approval status from responses: {str(e)}")
            return {level: 'Pending' for level in self.approver_levels}
    
    def get_next_pending_approver(self, approval_status: Dict[str, str], approvers: Dict[str, Optional[str]]) -> Optional[str]:
        """
        Get the next pending approver in the sequence.
        Skips approvers who have already approved at any other level.
        Returns None if the request has been rejected at any level.
        
        Args:
            approval_status (Dict[str, str]): Current approval status for each level
            approvers (Dict[str, Optional[str]]): Approver emails for each level
            
        Returns:
            Optional[str]: The level of the next pending approver (L1, L2, etc.) or None if all approved/rejected
        """
        # Check if request has been rejected at any level - if so, no next approver
        is_rejected = any(status and status.lower() in ['rejected', 'reject'] for status in approval_status.values())
        if is_rejected:
            return None
        
        # Get list of emails who have already approved at any level
        approved_emails = set()
        for level in self.approver_levels:
            if approval_status.get(level) == 'Approved' and approvers.get(level):
                approved_emails.add(approvers[level].lower())
        
        # Find the next pending approver who hasn't approved at any other level
        for level in self.approver_levels:
            if (approval_status.get(level) == 'Pending' and 
                approvers.get(level) and 
                approvers[level].lower() not in approved_emails):
                return level
        return None
    
    def get_approved_approvers(self, approval_status: Dict[str, str], approvers: Dict[str, Optional[str]]) -> List[str]:
        """
        Get list of approver levels who have already approved.
        
        Args:
            approval_status (Dict[str, str]): Current approval status for each level
            approvers (Dict[str, Optional[str]]): Approver emails for each level
            
        Returns:
            List[str]: List of approver levels (L1, L2, etc.) who have approved
        """
        approved_levels = []
        for level in self.approver_levels:
            if approval_status.get(level) == 'Approved' and approvers.get(level):
                approved_levels.append(level)
        return approved_levels
    
    def send_initial_approval_request(self, request_data: dict) -> Dict[str, Any]:
        """
        Send the initial approval request to L1 approver.
        
        Args:
            request_data (dict): Request data
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Get approvers for this request
            approvers = self.get_approvers_for_request(request_data)
            
            # Find L1 approver
            l1_approver = approvers.get('L1')
            if not l1_approver:
                return {
                    'success': False,
                    'message': 'No L1 approver found for this request',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Send initial approval notification
            email_request_data = request_data.copy()
            email_request_data['current_approver_email'] = l1_approver
            
            email_result = self.email_handler.send_sequential_approval_notification(
                email_request_data, 'L1', []
            )
            
            if email_result.get('success'):
                return {
                    'success': True,
                    'message': f'Initial approval request sent to L1 approver: {l1_approver}',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'l1_approver': l1_approver
                }
            else:
                return {
                    'success': False,
                    'message': f'Failed to send email to L1 approver: {email_result.get("message", "Unknown error")}',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send initial approval request: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def handle_approval_decision(self, request_id: str, approver_email: str, decision: str, rejection_reason: str = None) -> Dict[str, Any]:
        """
        Handle an approval decision from an approver.
        Updates the sheet, sends notifications, and triggers next approver if needed.
        
        Args:
            request_id (str): The request ID
            approver_email (str): The approver's email
            decision (str): 'Approved' or 'Reject'
            rejection_reason (str): Optional reason for rejection
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        print(f"DEBUG: handle_approval_decision called - Request: {request_id}, Approver: {approver_email}, Decision: {decision}")
        try:
            # Get request data from both responses and gsheet_unmasking_responses sheets
            from services.formservices import FormServices
            form_services = FormServices()
            
            # First try responses sheet
            data = form_services.read_sheet_data("responses!A:Z")
            request_row = None
            sheet_type = None
            
            if data and len(data) >= 2:
                for row in data[1:]:
                    if len(row) >= 2 and row[1].strip() == request_id:  # REQUEST_ID is in column B
                        request_row = row
                        sheet_type = 'responses'
                        break
            
            # If not found in responses, try gsheet_unmasking_responses sheet
            if not request_row:
                gsheet_data = form_services.read_sheet_data("gsheet_unmasking_responses!A:AB")
                if gsheet_data and len(gsheet_data) >= 2:
                    for row in gsheet_data[1:]:
                        if len(row) >= 1 and row[0].strip() == request_id:  # REQUEST_ID is in column A
                            request_row = row
                            sheet_type = 'gsheet_unmasking_responses'
                            break
            
            if not request_row:
                return {
                    'success': False,
                    'message': 'Request not found in any worksheet',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Convert row to dict for easier access based on sheet type
            if sheet_type == 'responses':
                # Columns: REQUEST_TYPE, REQUEST_ID, USER_NAME, EMAIL, ENTITY, DEFAULT_ROLE, DATABASE, SCHEMA, TABLE_OPTIONS, TABLE_NAME, COLUMN_NAME, GRANTEE, REQUESTING_FOR, VALIDITY_DAYS, REASON_CATEGORY, REASON_FOR_REQUEST, L1_APPROVER, L2_APPROVER, L3_APPROVER, L4_APPROVER, L5_APPROVER, CREATED_AT, ...
                request_type = request_row[0] if len(request_row) > 0 else ''
                is_table_column_request = request_type in ['Table request', 'Column request']
                
                request_data = {
                    'request_id': request_id,
                    'request_type': request_type,
                    'user_name': request_row[2] if len(request_row) > 2 else '',
                    'user_email': request_row[3] if len(request_row) > 3 else '',
                    'entity': request_row[4] if len(request_row) > 4 else '',
                    'database': request_row[6] if len(request_row) > 6 else '',
                    'schema': request_row[7] if len(request_row) > 7 else '',
                    'table_name': request_row[9] if len(request_row) > 9 else '',
                    'column_name': request_row[10] if len(request_row) > 10 else '',
                    'reason': request_row[15] if len(request_row) > 15 else '',
                    'objective': request_row[15] if len(request_row) > 15 and is_table_column_request else '',  # Map REASON_FOR_REQUEST as objective for table/column requests
                    'validity_days': request_row[13] if len(request_row) > 13 else '',
                    'requester_email': request_row[3] if len(request_row) > 3 else ''
                }
            else:  # gsheet_unmasking_responses
                # Columns: REQUEST_ID, USER_NAME, EMAIL, ENTITY, DEFAULT_ROLE, SPREADSHEET_ID, NAMED_RANGE, WHO HAS ACCESS TO THIS SHEET, END_USER_DESCRIPTION, USE_CASE, VALIDITY_DAYS, REMARKS, L1_APPROVER, L2_APPROVER, L3_APPROVER, L4_APPROVER, L5_APPROVER, CREATED_AT, ...
                request_data = {
                    'request_id': request_id,
                    'request_type': 'GSheet Unmasking',
                    'user_name': request_row[1] if len(request_row) > 1 else '',
                    'user_email': request_row[2] if len(request_row) > 2 else '',
                    'entity': request_row[3] if len(request_row) > 3 else '',
                    'database': 'Google Sheets',
                    'schema': request_row[5] if len(request_row) > 5 else '',  # SPREADSHEET_ID
                    'table_name': request_row[6] if len(request_row) > 6 else '',  # NAMED_RANGE
                    'column_name': request_row[7] if len(request_row) > 7 else '',  # WHO HAS ACCESS
                    'reason': request_row[11] if len(request_row) > 11 else '',  # REMARKS
                    'validity_days': request_row[10] if len(request_row) > 10 else '',
                    'requester_email': request_row[2] if len(request_row) > 2 else '',
                    # Add GSheet-specific fields for email template
                    'spreadsheet_id': request_row[5] if len(request_row) > 5 else '',  # SPREADSHEET_ID
                    'named_range': request_row[6] if len(request_row) > 6 else '',  # NAMED_RANGE
                    'who_has_access': request_row[7] if len(request_row) > 7 else '',  # WHO HAS ACCESS
                    'end_user_description': request_row[8] if len(request_row) > 8 else '',  # END_USER_DESCRIPTION
                    'use_case': request_row[9] if len(request_row) > 9 else '',  # USE_CASE
                    'remarks': request_row[11] if len(request_row) > 11 else '',  # REMARKS/OBJECTIVE
                    'validity_days': request_row[10] if len(request_row) > 10 else ''  # VALIDITY_DAYS
                }
            
            # Get approvers for this request
            # approvers = self.get_approvers_for_request(request_data)

            # For GSheet requests, approver columns are different (12-16) vs responses sheet (16-20)
            if sheet_type == 'gsheet_unmasking_responses':
                # GSheet columns: L1_APPROVER(12), L2_APPROVER(13), L3_APPROVER(14), L4_APPROVER(15), L5_APPROVER(16)
                approvers = {
                    'L1': request_row[12].strip() if len(request_row) > 12 and request_row[12].strip() else '',
                    'L2': request_row[13].strip() if len(request_row) > 13 and request_row[13].strip() else '',
                    'L3': request_row[14].strip() if len(request_row) > 14 and request_row[14].strip() else '',
                    'L4': request_row[15].strip() if len(request_row) > 15 and request_row[15].strip() else '',
                    'L5': request_row[16].strip() if len(request_row) > 16 and request_row[16].strip() else ''
                }
            else:
                # Regular responses sheet: L1_APPROVER(16), L2_APPROVER(17), L3_APPROVER(18), L4_APPROVER(19), L5_APPROVER(20)
                approvers = {
                    'L1': request_row[16].strip() if len(request_row) > 16 and request_row[16].strip() else '',
                    'L2': request_row[17].strip() if len(request_row) > 17 and request_row[17].strip() else '',
                    'L3': request_row[18].strip() if len(request_row) > 18 and request_row[18].strip() else '',
                    'L4': request_row[19].strip() if len(request_row) > 19 and request_row[19].strip() else '',
                    'L5': request_row[20].strip() if len(request_row) > 20 and request_row[20].strip() else ''
                }
            
            print(f"DEBUG: Using stored approvers from response sheet: {approvers}")
            
            # Find ALL levels where this approver is assigned
            approver_levels = []
            for level, email in approvers.items():
                if email and email.lower() == approver_email.lower():
                    approver_levels.append(level)
            
            if not approver_levels:
                return {
                    'success': False,
                    'message': 'Approver not found in approval chain',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            print(f"DEBUG: Found approver {approver_email} at levels: {approver_levels}")
            
            # Update approval status in the responses sheet for ALL levels this approver is assigned to
            all_updates_successful = True
            for level in approver_levels:
                sheet_update_success = self.update_approver_level_status(
                    request_id, level, decision
                )
                if not sheet_update_success:
                    all_updates_successful = False
                    print(f"❌ Failed to update approval status for level {level}")
                else:
                    print(f"✅ Updated approval status for level {level}: {decision}")
            
            if not all_updates_successful:
                return {
                    'success': False,
                    'message': 'Failed to update approval status in sheet for some levels',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            if decision == 'Approved':
                # Send confirmation to requester for the lowest level approved
                lowest_level = min(approver_levels, key=lambda x: int(x[1]))  # L1, L2, etc. -> sort by number
                self.email_handler.send_requester_approval_confirmation(
                    request_data, approver_email, lowest_level
                )
                
                # Get updated approval status
                approval_status = self.get_approval_status_from_responses(request_id)
                for level in approver_levels:
                    approval_status[level] = 'Approved'  # Update all current levels
                
                # Check if there's a next approver
                print(f"DEBUG: Checking for next approver after {approver_levels} approval. Current approval status: {approval_status}")
                next_approver_level = self.get_next_pending_approver(approval_status, approvers)
                
                if next_approver_level:
                    # Send notification to next approver
                    next_approver_email = approvers[next_approver_level]
                    previous_approvers = self.get_approved_approvers(approval_status, approvers)
                    email_request_data = request_data.copy()
                    email_request_data['current_approver_email'] = next_approver_email
                    result = self.email_handler.send_sequential_approval_notification(
                        email_request_data,
                        next_approver_level,
                        previous_approvers
                    )
                    if result.get('success'):
                        print(f"Next approver is {next_approver_level} ({next_approver_email}). Mail sent.")
                    else:
                        print(f"Next approver is {next_approver_level} ({next_approver_email}). Mail failed: {result.get('message')}")
                    return {
                        'success': True,
                        'message': f'Approval processed and forwarded to {next_approver_level}',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'next_approver': next_approver_level
                    }
                else:
                    return {
                        'success': True,
                        'message': 'All approvals completed',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'completed'
                    }
            
            elif decision == 'Reject':
                # Update the sheet with rejection status (store 'Rejected' in sheet)
                update_success = True
                for level in approver_levels:
                    if not self.update_approver_level_status(request_id, level, 'Rejected'):
                        update_success = False
                        print(f"Warning: Failed to update {level} status to Rejected")
                
                if not update_success:
                    print("Warning: Some approval levels failed to update to Rejected status")
                    return {
                        'success': False,
                        'message': 'Failed to update rejection status in sheet',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                
                # Send rejection notification to requester for the lowest level rejected (consistent with approval logic)
                lowest_level = min(approver_levels, key=lambda x: int(x[1]))  # L1, L2, etc. -> sort by number
                print(f"DEBUG: Sending rejection notification for request {request_id} by {approver_email} at level {lowest_level}")
                rejection_result = self.email_handler.send_requester_rejection_notification(
                    request_data, approver_email, lowest_level, rejection_reason
                )
                print(f"DEBUG: Rejection email result: {rejection_result}")
                
                return {
                    'success': True,
                    'message': f'Request rejected by levels {", ".join(approver_levels)}',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'rejected'
                }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to handle approval decision: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def update_approver_level_status(self, request_id: str, approver_level: str, decision: str) -> bool:
        """
        Update the specific approver level status (L1-L5) in the responses sheet.
        
        Args:
            request_id (str): The request ID to update
            approver_level (str): The approver level (L1, L2, L3, L4, L5)
            decision (str): 'Approved' or 'Reject'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from services.formservices import FormServices
            form_services = FormServices()
            
            # Try responses sheet first
            data = form_services.read_sheet_data("responses!A:Z")
            row_index = None
            sheet_name = None
            
            if data and len(data) >= 2:
                for i, row in enumerate(data[1:], start=2):  # Start from row 2 (skip header)
                    if len(row) >= 2 and row[1].strip() == request_id:  # REQUEST_ID is in column B
                        row_index = i
                        sheet_name = "responses"
                        break
            
            # If not found in responses, try gsheet_unmasking_responses sheet
            if row_index is None:
                gsheet_data = form_services.read_sheet_data("gsheet_unmasking_responses!A:AB")
                if gsheet_data and len(gsheet_data) >= 2:
                    for i, row in enumerate(gsheet_data[1:], start=2):  # Start from row 2 (skip header)
                        if len(row) >= 1 and row[0].strip() == request_id:  # REQUEST_ID is in column A
                            row_index = i
                            sheet_name = "gsheet_unmasking_responses"
                            break
            
            if row_index is None:
                print(f"❌ Request ID {request_id} not found in any worksheet")
                return False
            
            # Map approver level to column based on sheet type
            if sheet_name == "responses":
                level_column_mapping = {
                    'L1': 'W',  # Column W for L1 status (position 22)
                    'L2': 'X',  # Column X for L2 status (position 23)  
                    'L3': 'Y',  # Column Y for L3 status (position 24)
                    'L4': 'Z',  # Column Z for L4 status (position 25)
                    'L5': 'AA'  # Column AA for L5 status (position 26)
                }
            else:  # gsheet_unmasking_responses
                level_column_mapping = {
                    'L1': 'S',  # Column S for L1 status (position 18)
                    'L2': 'T',  # Column T for L2 status (position 19)  
                    'L3': 'U',  # Column U for L3 status (position 20)
                    'L4': 'V',  # Column V for L4 status (position 21)
                    'L5': 'W'   # Column W for L5 status (position 22)
                }
            
            if approver_level not in level_column_mapping:
                print(f"❌ Invalid approver level: {approver_level}")
                return False
                
            status_column = level_column_mapping[approver_level]
            
            # Update the specific level status
            connection = form_services.get_sheet_connection()
            range_name = f"{sheet_name}!{status_column}{row_index}"
            url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/{range_name}?valueInputOption=RAW"
            
            body = {
                "values": [[decision]]
            }
            
            response = requests.put(url, headers=connection['headers'], json=body)
            response.raise_for_status()
            
            # Update timestamp column for both Approved and Rejected decisions
            if decision in ['Approved', 'Rejected']:
                # Map to timestamp columns based on sheet type
                if sheet_name == "responses":
                    timestamp_column_mapping = {
                        'L1': 'AB', # Column AB for L1 timestamp (position 27)
                        'L2': 'AC', # Column AC for L2 timestamp (position 28)
                        'L3': 'AD', # Column AD for L3 timestamp (position 29)
                        'L4': 'AE', # Column AE for L4 timestamp (position 30) 
                        'L5': 'AF'  # Column AF for L5 timestamp (position 31)
                    }
                else:  # gsheet_unmasking_responses
                    timestamp_column_mapping = {
                        'L1': 'X',  # Column X for L1 timestamp (position 23)
                        'L2': 'Y',  # Column Y for L2 timestamp (position 24)
                        'L3': 'Z',  # Column Z for L3 timestamp (position 25)
                        'L4': 'AA', # Column AA for L4 timestamp (position 26)
                        'L5': 'AB'  # Column AB for L5 timestamp (position 27)
                    }
                
                if approver_level in timestamp_column_mapping:
                    ts_column = timestamp_column_mapping[approver_level]
                    ts_range = f"{sheet_name}!{ts_column}{row_index}"
                    ts_url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/{ts_range}?valueInputOption=RAW"
                    
                    ts_body = {
                        "values": [[datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]
                    }
                    
                    ts_response = requests.put(ts_url, headers=connection['headers'], json=ts_body)
                    ts_response.raise_for_status()
            
            print(f"✅ Updated {approver_level} status to {decision} for request {request_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating approver level status: {str(e)}")
            return False
    
    def get_requests_for_approver(self, approver_email: str) -> List[dict]:
        """
        Get all requests that an approver can currently approve.
        Only shows requests where this approver is the next in line.
        
        Args:
            approver_email (str): Email of the approver
            
        Returns:
            List[dict]: List of requests this approver can act on
        """
        try:
            from services.formservices import FormServices
            form_services = FormServices()
            
            # Get all requests from responses sheet
            data = form_services.read_sheet_data("responses!A:Z")
            
            if not data or len(data) < 2:
                return []
            
            approver_requests = []
            
            for row in data[1:]:  # Skip header
                if len(row) < 2:
                    continue
                    
                request_id = row[1].strip()
                if not request_id:
                    continue
                
                # Convert row to request data based on new column structure
                request_data = {
                    'request_id': request_id,
                    'user_name': row[2] if len(row) > 2 else '',
                    'user_email': row[3] if len(row) > 3 else '',
                    'entity': row[4] if len(row) > 4 else '',
                    'requester_email': row[3] if len(row) > 3 else ''
                }
                
                # Get approvers for this request
                # approvers = self.get_approvers_for_request(request_data)

                 # Get approvers from the stored response sheet data (NOT recalculated)
                # L1_APPROVER: index 16, L2_APPROVER: index 17, L3_APPROVER: index 18, L4_APPROVER: index 19, L5_APPROVER: index 20
                approvers = {
                    'L1': row[16].strip() if len(row) > 16 and row[16].strip() else '',
                    'L2': row[17].strip() if len(row) > 17 and row[17].strip() else '',
                    'L3': row[18].strip() if len(row) > 18 and row[18].strip() else '',
                    'L4': row[19].strip() if len(row) > 19 and row[19].strip() else '',
                    'L5': row[20].strip() if len(row) > 20 and row[20].strip() else ''
                }
                
                # Get current approval status
                approval_status = self.get_approval_status_from_responses(request_id)
                
                # Check if this approver is the next pending approver
                next_approver_level = self.get_next_pending_approver(approval_status, approvers)
                
                if next_approver_level and approvers.get(next_approver_level) == approver_email:
                    # Add additional request details
                    request_data.update({
                        'current_approver_level': next_approver_level,
                        'approval_status': approval_status,
                        'approvers': approvers
                    })
                    approver_requests.append(request_data)
            
            return approver_requests
            
        except Exception as e:
            print(f"Error getting requests for approver: {str(e)}")
            return []
