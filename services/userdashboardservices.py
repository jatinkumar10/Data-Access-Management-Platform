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



class UserDashboardServices:
    """
    Service to handle user dashboard operations and fetch user requests from Google Sheets.
    """
    
    def __init__(self):
        self.spreadsheet_id = SPREADSHEET_ID
        self.token_service = get_token_service()
        self.google_sheets_api_base = "https://sheets.googleapis.com/v4/spreadsheets"
    
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
    
    def get_user_requests(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Get all requests for a specific user from both responses and user_responses worksheets.
        
        Args:
            user_email (str): The user's email address
            
        Returns:
            List[Dict[str, Any]]: List of user requests with all details
        """
        try:
            all_requests = []
            
            # Fetch from responses worksheet (Table and Column requests) - Updated for L1-L5 system
            responses_data = self.read_sheet_data("responses!A:AF")  # Extended range for L1-L5 columns
            
            if responses_data and len(responses_data) > 1:  # Has header + data
                headers = responses_data[0]
                
                # Find column indices for L1-L5 system
                email_idx = headers.index("EMAIL") if "EMAIL" in headers else 3
                request_type_idx = headers.index("REQUEST_TYPE") if "REQUEST_TYPE" in headers else 0
                request_id_idx = headers.index("REQUEST_ID") if "REQUEST_ID" in headers else 1
                created_at_idx = headers.index("CREATED_AT") if "CREATED_AT" in headers else 21
                
                # L1-L5 approver and status columns
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
                
                # Process each row
                for row in responses_data[1:]:  # Skip header
                    if len(row) > email_idx:
                        row_email = row[email_idx].strip()
                        
                        # Check if this request belongs to the user
                        if row_email.lower() == user_email.lower():
                            # Build L1-L5 approval status
                            approval_chain = self._build_approval_chain_status(row, [
                                ("L1", l1_approver_idx, l1_status_idx),
                                ("L2", l2_approver_idx, l2_status_idx),
                                ("L3", l3_approver_idx, l3_status_idx),
                                ("L4", l4_approver_idx, l4_status_idx),
                                ("L5", l5_approver_idx, l5_status_idx)
                            ])
                            
                            # Build individual L1-L5 status columns
                            l1_status = self._get_individual_approver_status(row, l1_approver_idx, l1_status_idx)
                            l2_status = self._get_individual_approver_status(row, l2_approver_idx, l2_status_idx)
                            l3_status = self._get_individual_approver_status(row, l3_approver_idx, l3_status_idx)
                            l4_status = self._get_individual_approver_status(row, l4_approver_idx, l4_status_idx)
                            l5_status = self._get_individual_approver_status(row, l5_approver_idx, l5_status_idx)
                            
                            request = {
                                "Request ID": row[request_id_idx] if len(row) > request_id_idx else "",
                                "Request Type": row[request_type_idx] if len(row) > request_type_idx else "",
                                "L1 Status": l1_status,
                                "L2 Status": l2_status,
                                "L3 Status": l3_status,
                                "L4 Status": l4_status,
                                "L5 Status": l5_status,
                                "Overall Status": self._get_l1_l5_overall_status(row, [
                                    l1_status_idx, l2_status_idx, l3_status_idx, l4_status_idx, l5_status_idx
                                ]),
                                "Created At": row[created_at_idx] if len(row) > created_at_idx else "",
                                "Source": "responses"
                            }
                            all_requests.append(request)
            
            # Fetch from user_responses worksheet (User Creation requests)
            user_responses_data = self.read_sheet_data("user_responses!A:Z")
            
            if user_responses_data and len(user_responses_data) > 1:  # Has header + data
                headers = user_responses_data[0]
                
                # Find column indices
                email_idx = headers.index("User") if "User" in headers else 1  # Default to column B
                request_id_idx = headers.index("Request_id") if "Request_id" in headers else 0
                rm_approver_idx = headers.index("RM_APPROVER") if "RM_APPROVER" in headers else 2
                approval_status_idx = headers.index("Approval_status") if "Approval_status" in headers else 6
                created_at_idx = headers.index("CREATED_AT") if "CREATED_AT" in headers else 5
                
                # Process each row
                for row in user_responses_data[1:]:  # Skip header
                    if len(row) > email_idx:
                        row_email = row[email_idx].strip()
                        
                        # Check if this request belongs to the user
                        if row_email.lower() == user_email.lower():
                            status = row[approval_status_idx] if len(row) > approval_status_idx else "Pending"
                            rm_approver = row[rm_approver_idx] if len(row) > rm_approver_idx else ""
                            
                            # Convert User Creation to L1-L5 format
                            l1_status = self._format_status_with_approver(status, rm_approver) if rm_approver else "None"
                            l2_status = "None"
                            l3_status = "None"
                            l4_status = "None"
                            l5_status = "None"
                            
                            request = {
                                "Request ID": row[request_id_idx] if len(row) > request_id_idx else "",
                                "Request Type": "User Creation",
                                "L1 Status": l1_status,
                                "L2 Status": l2_status,
                                "L3 Status": l3_status,
                                "L4 Status": l4_status,
                                "L5 Status": l5_status,
                                "Overall Status": self._format_status(status),
                                "Created At": row[created_at_idx] if len(row) > created_at_idx else "",
                                "Source": "user_responses"
                            }
                            all_requests.append(request)
            
            # Fetch from gsheet_unmasking_responses worksheet (GSheet Unmasking requests)
            gsheet_responses_data = self.read_sheet_data("gsheet_unmasking_responses!A:AB")
            
            if gsheet_responses_data and len(gsheet_responses_data) > 1:  # Has header + data
                headers = gsheet_responses_data[0]
                
                # Find column indices for GSheet requests
                email_idx = headers.index("EMAIL") if "EMAIL" in headers else 2
                request_id_idx = headers.index("REQUEST_ID") if "REQUEST_ID" in headers else 0
                created_at_idx = headers.index("CREATED_AT") if "CREATED_AT" in headers else 16
                
                # L1-L5 approver and status columns for GSheet
                l1_approver_idx = headers.index("L1_APPROVER") if "L1_APPROVER" in headers else 12
                l2_approver_idx = headers.index("L2_APPROVER") if "L2_APPROVER" in headers else 13
                l3_approver_idx = headers.index("L3_APPROVER") if "L3_APPROVER" in headers else 14
                l4_approver_idx = headers.index("L4_APPROVER") if "L4_APPROVER" in headers else 15
                l5_approver_idx = headers.index("L5_APPROVER") if "L5_APPROVER" in headers else 16
                
                l1_status_idx = headers.index("L1_APPROVER_STATUS") if "L1_APPROVER_STATUS" in headers else 17
                l2_status_idx = headers.index("L2_APPROVER_STATUS") if "L2_APPROVER_STATUS" in headers else 18
                l3_status_idx = headers.index("L3_APPROVER_STATUS") if "L3_APPROVER_STATUS" in headers else 19
                l4_status_idx = headers.index("L4_APPROVER_STATUS") if "L4_APPROVER_STATUS" in headers else 20
                l5_status_idx = headers.index("L5_APPROVER_STATUS") if "L5_APPROVER_STATUS" in headers else 21
                
                # Process each row
                for row in gsheet_responses_data[1:]:  # Skip header
                    if len(row) > email_idx:
                        row_email = row[email_idx].strip()
                        
                        # Check if this request belongs to the user
                        if row_email.lower() == user_email.lower():
                            # Build individual L1-L5 status columns for GSheet requests
                            l1_status = self._get_individual_approver_status(row, l1_approver_idx, l1_status_idx)
                            l2_status = self._get_individual_approver_status(row, l2_approver_idx, l2_status_idx)
                            l3_status = self._get_individual_approver_status(row, l3_approver_idx, l3_status_idx)
                            l4_status = self._get_individual_approver_status(row, l4_approver_idx, l4_status_idx)
                            l5_status = self._get_individual_approver_status(row, l5_approver_idx, l5_status_idx)
                            
                            request = {
                                "Request ID": row[request_id_idx] if len(row) > request_id_idx else "",
                                "Request Type": "GSheet Unmasking",
                                "L1 Status": l1_status,
                                "L2 Status": l2_status,
                                "L3 Status": l3_status,
                                "L4 Status": l4_status,
                                "L5 Status": l5_status,
                                "Overall Status": self._get_l1_l5_overall_status(row, [
                                    l1_status_idx, l2_status_idx, l3_status_idx, l4_status_idx, l5_status_idx
                                ]),
                                "Created At": row[created_at_idx] if len(row) > created_at_idx else "",
                                "Source": "gsheet_unmasking_responses"
                            }
                            all_requests.append(request)
            
            # Sort by Created At (latest first)
            all_requests.sort(key=lambda x: x.get("Created At", ""), reverse=True)
            
            return all_requests
            
        except Exception as e:
            print(f"Error fetching user requests: {str(e)}")
            return []
    
    def _format_status(self, status: str) -> str:
        """
        Format status with appropriate emoji.
        
        Args:
            status (str): Raw status from sheet
            
        Returns:
            str: Formatted status with emoji
        """
        status_lower = status.lower()
        if "approved" in status_lower:
            return "✅ Approved"
        elif "rejected" in status_lower or "denied" in status_lower:
            return "❌ Rejected"
        elif "pending" in status_lower:
            return "⏳ Pending"
        else:
            return f"⏳ {status}"
    
    def _format_status_with_approver(self, status: str, approver: str) -> str:
        """
        Format status with approver name and appropriate emoji.
        
        Args:
            status (str): Raw status from sheet
            approver (str): Approver email/name
            
        Returns:
            str: Formatted status with emoji and approver
        """
        status_lower = status.lower()
        if "approved" in status_lower:
            return f"✅ ({approver})"
        elif "rejected" in status_lower or "denied" in status_lower:
            return f"❌ ({approver})"
        elif "pending" in status_lower:
            return f"⏳ ({approver})"
        else:
            return f"⏳ ({approver})"
    
    def _build_approval_chain_status(self, row: List[str], level_mappings: List[tuple]) -> str:
        """
        Build approval chain status for L1-L5 system.
        
        Args:
            row (List[str]): Row data from sheet
            level_mappings (List[tuple]): List of (level, approver_idx, status_idx) tuples
            
        Returns:
            str: Formatted approval chain status
        """
        chain_parts = []
        for level, approver_idx, status_idx in level_mappings:
            if len(row) > approver_idx and len(row) > status_idx:
                approver = row[approver_idx] if row[approver_idx] else ""
                status = row[status_idx] if row[status_idx] else "Pending"
                
                if approver:  # Only show levels that have approvers assigned
                    approver_name = approver.split('@')[0] if '@' in approver else approver
                    if status.lower() == "approved":
                        chain_parts.append(f"{level}: ✅ {approver_name}")
                    elif "reject" in status.lower():
                        chain_parts.append(f"{level}: ❌ {approver_name}")
                    else:
                        chain_parts.append(f"{level}: ⏳ {approver_name}")
        
        return " | ".join(chain_parts) if chain_parts else "No approvers assigned"
    
    def _get_individual_approver_status(self, row: List[str], approver_idx: int, status_idx: int) -> str:
        """
        Get individual approver status with approver name and status.
        
        Args:
            row (List[str]): Row data from sheet
            approver_idx (int): Index of approver column
            status_idx (int): Index of status column
            
        Returns:
            str: Formatted approver status
        """
        if len(row) > approver_idx and len(row) > status_idx:
            approver = row[approver_idx] if row[approver_idx] else ""
            status = row[status_idx] if row[status_idx] else "Pending"
            
            if approver:  # Only show if approver is assigned
                approver_name = approver.split('@')[0] if '@' in approver else approver
                if status.lower() == "approved":
                    return f"✅ {approver_name}"
                elif "reject" in status.lower():
                    return f"❌ {approver_name}"
                else:
                    return f"⏳ {approver_name}"
            else:
                return "None"
        else:
            return "None"
    
    def _get_l1_l5_overall_status(self, row: List[str], status_indices: List[int]) -> str:
        """
        Determine overall status based on L1-L5 approval statuses.
        
        Args:
            row (List[str]): Row data from sheet
            status_indices (List[int]): List of status column indices for L1-L5
            
        Returns:
            str: Overall status
        """
        statuses = []
        for idx in status_indices:
            if len(row) > idx and row[idx]:
                statuses.append(row[idx].lower())
        
        # If any is rejected, overall is rejected
        if any("reject" in status for status in statuses):
            return "❌ Rejected"
        
        # Count approvals and pending
        approved_count = sum(1 for status in statuses if "approved" in status)
        pending_count = sum(1 for status in statuses if "pending" in status or not status.strip())
        
        if approved_count > 0 and pending_count == 0:
            return "✅ Approved"
        else:
            return "⏳ Pending"

    def _get_overall_status(self, rm_status: str, data_status: str) -> str:
        """
        Determine overall status based on RM and Data approver statuses (legacy).
        
        Args:
            rm_status (str): RM approver status
            data_status (str): Data approver status
            
        Returns:
            str: Overall status
        """
        rm_lower = rm_status.lower()
        data_lower = data_status.lower()
        
        # If either is rejected, overall is rejected
        if "rejected" in rm_lower or "denied" in rm_lower or "rejected" in data_lower or "denied" in data_lower:
            return "❌ Rejected"
        
        # If both are approved, overall is approved
        if "approved" in rm_lower and "approved" in data_lower:
            return "✅ Approved"
        
        # Otherwise, pending
        return "⏳ Pending"
    
    def get_request_summary(self, user_email: str) -> Dict[str, int]:
        """
        Get summary statistics for user requests.
        
        Args:
            user_email (str): The user's email address
            
        Returns:
            Dict[str, int]: Summary with total, pending, approved, rejected counts
        """
        try:
            requests = self.get_user_requests(user_email)
            
            total = len(requests)
            pending = sum(1 for req in requests if "⏳" in req.get("Overall Status", ""))
            approved = sum(1 for req in requests if "✅" in req.get("Overall Status", ""))
            rejected = sum(1 for req in requests if "❌" in req.get("Overall Status", ""))
            
            return {
                "total": total,
                "pending": pending,
                "approved": approved,
                "rejected": rejected
            }
            
        except Exception as e:
            print(f"Error getting request summary: {str(e)}")
            return {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0
            }

# Global user dashboard services instance
user_dashboard_services = UserDashboardServices()

def get_user_dashboard_services() -> UserDashboardServices:
    """
    Get the global user dashboard services instance.
    
    Returns:
        UserDashboardServices: The global user dashboard services instance
    """
    return user_dashboard_services

def get_user_requests(user_email: str) -> List[Dict[str, Any]]:
    """
    Convenience function to get user requests.
    
    Args:
        user_email (str): The user's email address
        
    Returns:
        List[Dict[str, Any]]: List of user requests
    """
    return user_dashboard_services.get_user_requests(user_email)

def get_request_summary(user_email: str) -> Dict[str, int]:
    """
    Convenience function to get request summary.
    
    Args:
        user_email (str): The user's email address
        
    Returns:
        Dict[str, int]: Summary statistics
    """
    return user_dashboard_services.get_request_summary(user_email)
