import requests
import sys
import os
from typing import Dict, Any
import json
from datetime import datetime, timedelta
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



class FormServices:


    def get_gsheet_unmasking_options(self, user_snowflake_account: str = None) -> dict:
        """
        Fetch spreadsheet IDs and named ranges from gsheet_unmasking!A:D.
        Optionally filter by user's Snowflake account (first column).
        Returns a dict: {spreadsheet_id: [named_ranges]}
        """
        data = self.read_sheet_data("gsheet_unmasking!A:D")
        options = {}
        for row in data[1:]:  # Skip header
            if len(row) < 2:
                continue
            snowflake_account = row[0].strip()
            spreadsheet_id = row[2].strip()
            named_range = row[3].strip() if len(row) > 2 else ""
            # Optionally filter by user account
            if user_snowflake_account and snowflake_account != user_snowflake_account:
                continue
            if spreadsheet_id not in options:
                options[spreadsheet_id] = []
            if named_range:
                options[spreadsheet_id].append(named_range)
        return options
    """
    Service to handle form operations and Google Sheets connection.
    """
    
    def __init__(self):
        self.spreadsheet_id = SPREADSHEET_ID
        self.token_service = get_token_service()
        self.google_sheets_api_base = "https://sheets.googleapis.com/v4/spreadsheets"
    
    def clear_approval_cache(self):
        """
        Clear all cached data to force fresh data retrieval.
        This should be called after any approval/rejection action.
        """
        # Clear any session state cache if available
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
            # Use token service to get a valid access token (will try to refresh if expired)
            access_token = self.token_service.get_valid_access_token()
            
            if not access_token or access_token == "None":
                raise Exception("No access token available from token service")
            
            # Return connection details
            connection = {
                "spreadsheet_id": self.spreadsheet_id,
                "base_url": self.google_sheets_api_base,
                "access_token": access_token,
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            }
            return connection
            
        except Exception as e:
            raise Exception(f"Failed to establish Google Sheet connection: {str(e)}")
    
    def read_sheet_data(self, range_name: str) -> list:
        """
        Read data from a specific range in the Google Sheet.
        
        Args:
            range_name (str): The range to read (e.g., "user_manager!A:B")
            
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
    
    def get_manager_email(self, user_email: str) -> str:
        """
        Get manager email for a given user email from the user_manager worksheet.
        
        Args:
            user_email (str): The user's email address
            
        Returns:
            str: The manager's email address or None if not found
        """
        try:
            # Read the user_manager worksheet data
            data = self.read_sheet_data("user_manager!A:B")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return None  # No data found
            
            # Skip header row and search for matching user email
            for row in data[1:]:  # Skip header row
                if len(row) >= 2:
                    sheet_user_email = row[0].strip()
                    manager_email = row[1].strip()
                    
                    if sheet_user_email.lower() == user_email.lower():
                        return manager_email
            
            # If not found, return None
            return None
            
        except Exception as e:
            return None  # Return None on error
    
    def get_entity_bu_mapping(self) -> Dict[str, list]:
        """
        Get Entity to BU mapping from the user_bu worksheet.
        
        Returns:
            Dict[str, list]: Dictionary with entity as key and list of BUs as value
        """
        try:
            # Read the user_bu worksheet data
            data = self.read_sheet_data("user_bu!A:B")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return {}
            
            entity_bu_mapping = {}
            
            # Skip header row and build mapping
            for row in data[1:]:  # Skip header row
                if len(row) >= 2:
                    entity = row[0].strip()
                    bu = row[1].strip()
                    
                    if entity and entity != "Entity" and bu and bu != "BU":
                        if entity not in entity_bu_mapping:
                            entity_bu_mapping[entity] = []
                        entity_bu_mapping[entity].append(bu)
            
            # Sort BUs for each entity
            for entity in entity_bu_mapping:
                entity_bu_mapping[entity] = sorted(list(set(entity_bu_mapping[entity])))
            
            return entity_bu_mapping
            
        except Exception as e:
            print(f"Error fetching entity/BU mapping: {str(e)}")
            return {}
    
    def get_entity_bu_options(self) -> Dict[str, list]:
        """
        Get distinct Entity and BU options from the user_bu worksheet.
        
        Returns:
            Dict[str, list]: Dictionary with 'entities' and 'business_units' lists
        """
        try:
            # Read the user_bu worksheet data
            data = self.read_sheet_data("user_bu!A:B")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return {
                    'entities': ["Select Entity"],
                    'business_units': ["Select Business Unit"]
                }
            
            entities = set()
            
            # Skip header row and collect distinct entities
            for row in data[1:]:  # Skip header row
                if len(row) >= 2:
                    entity = row[0].strip()
                    
                    if entity and entity != "Entity":
                        entities.add(entity)
            
            # Convert to sorted list
            entities_list = ["Select Entity"] + sorted(list(entities))
            
            result = {
                'entities': entities_list,
                'business_units': ["Select Business Unit"]  # Will be populated based on selected entity
            }
            
            return result
            
        except Exception as e:
            print(f"Error fetching entity/BU options: {str(e)}")
            return {
                'entities': ["Select Entity"],
                'business_units': ["Select Business Unit"]
            }
    
    def get_user_entity_role(self, user_email: str) -> Dict[str, str]:
        """
        Get user's entity and default role from the snf_user worksheet.
        
        Args:
            user_email (str): The user's email address
            
        Returns:
            Dict[str, str]: Dictionary with 'entity' and 'default_role' or empty strings if not found
        """
        try:
            # Read the snf_user worksheet data
            data = self.read_sheet_data("snf_user!A:C")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return {"entity": "", "default_role": ""}
            
            # Skip header row and search for matching user email
            for row in data[1:]:  # Skip header row
                if len(row) >= 3:
                    sheet_entity = row[0].strip()
                    sheet_email = row[1].strip()
                    sheet_role = row[2].strip()
                    
                    if sheet_email.lower() == user_email.lower():
                        return {
                            "entity": sheet_entity,
                            "default_role": sheet_role
                        }
            
            # If not found, return empty values
            return {"entity": "", "default_role": ""}
            
        except Exception as e:
            print(f"Error fetching user entity/role: {str(e)}")
            return {"entity": "", "default_role": ""}
    
    def get_database_schema_table_mapping(self) -> Dict[str, Dict[str, list]]:
        """
        Get database, schema, and table mapping from the table_list worksheet.
        
        Returns:
            Dict[str, Dict[str, list]]: Dictionary with database as key, schema as sub-key, and tables as list
        """
        try:
            # Read the table_list worksheet data
            data = self.read_sheet_data("table_list!A:C")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return {}
            
            db_schema_table_mapping = {}
            
            # Skip header row and build mapping
            for row in data[1:]:  # Skip header row
                if len(row) >= 3:
                    database = row[0].strip()
                    schema = row[1].strip()
                    table = row[2].strip()
                    
                    if database and database != "DATABASE_NAME" and schema and schema != "SCHEMA_NAME" and table and table != "TABLE_NAME":
                        if database not in db_schema_table_mapping:
                            db_schema_table_mapping[database] = {}
                        
                        if schema not in db_schema_table_mapping[database]:
                            db_schema_table_mapping[database][schema] = []
                        
                        db_schema_table_mapping[database][schema].append(table)
            
            # Sort schemas and tables for each database
            for database in db_schema_table_mapping:
                for schema in db_schema_table_mapping[database]:
                    db_schema_table_mapping[database][schema] = sorted(list(set(db_schema_table_mapping[database][schema])))
            
            return db_schema_table_mapping
            
        except Exception as e:
            print(f"Error fetching database/schema/table mapping: {str(e)}")
            return {}
    
    def get_database_options(self) -> list:
        """
        Get distinct database names from the table_list worksheet.
        
        Returns:
            list: List of distinct database names
        """
        try:
            # Read the table_list worksheet data
            data = self.read_sheet_data("table_list!A:C")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return ["Select Database"]
            
            databases = set()
            
            # Skip header row and collect distinct databases
            for row in data[1:]:  # Skip header row
                if len(row) >= 3:
                    database = row[0].strip()
                    
                    if database and database != "DATABASE_NAME":
                        databases.add(database)
            
            # Convert to sorted list
            databases_list = ["Select Database"] + sorted(list(databases))
            
            return databases_list
            
        except Exception as e:
            print(f"Error fetching database options: {str(e)}")
            return ["Select Database"]
    
    def get_generic_user_role_options(self, user_entity: str) -> Dict[str, list]:
        """
        Get generic user and role options for a specific entity from the generic_role_mapping worksheet.
        
        Args:
            user_entity (str): The user's entity
            
        Returns:
            Dict[str, list]: Dictionary with 'generic_users' and 'generic_roles' lists
        """
        try:
            # Read the generic_role_mapping worksheet data
            data = self.read_sheet_data("generic_role_mapping!A:C")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return {
                    'generic_users': ["Select Generic User"],
                    'generic_roles': ["Select Generic Role"]
                }
            
            generic_users = set()
            generic_roles = set()
            
            # Skip header row and collect options for the specific entity
            for row in data[1:]:  # Skip header row
                if len(row) >= 3:
                    sheet_entity = row[0].strip()
                    generic_user = row[1].strip()
                    generic_role = row[2].strip()
                    
                    # Only include options for the user's entity
                    if sheet_entity.lower() == user_entity.lower():
                        if generic_user and generic_user != "GENERIC_USER":
                            generic_users.add(generic_user)
                        if generic_role and generic_role != "GENERIC_ROLE":
                            generic_roles.add(generic_role)
            
            # Convert to sorted lists
            generic_users_list = ["Select Generic User"] + sorted(list(generic_users))
            generic_roles_list = ["Select Generic Role"] + sorted(list(generic_roles))
            
            return {
                'generic_users': generic_users_list,
                'generic_roles': generic_roles_list
            }
            
        except Exception as e:
            print(f"Error fetching generic user/role options: {str(e)}")
            return {
                'generic_users': ["Select Generic User"],
                'generic_roles': ["Select Generic Role"]
            }
    
    def get_rm_approver(self, user_email: str) -> str:
        """
        Get RM approver email for a given user email from the rm_approvers worksheet.
        
        Args:
            user_email (str): The user's email address
            
        Returns:
            str: The RM approver's email address or None if not found
        """
        try:
            # Read the rm_approvers worksheet data
            data = self.read_sheet_data("rm_approvers!A:B")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return None  # No data found
            
            # Skip header row and search for matching user email
            for row in data[1:]:  # Skip header row
                if len(row) >= 2:
                    sheet_user_email = row[0].strip()
                    approver_email = row[1].strip()
                    
                    if sheet_user_email.lower() == user_email.lower():
                        return approver_email
            
            # If not found, return None
            return None
            
        except Exception as e:
            print(f"Error fetching RM approver: {str(e)}")
            return None  # Return None on error
    
    def get_data_approver(self, database: str, schema: str) -> str:
        """
        Get data approver email for a given database and schema from the data_approvers worksheet.
        
        Args:
            database (str): The selected database name
            schema (str): The selected schema name
            
        Returns:
            str: The data approver's email address or empty string if not found
        """
        try:
            # Read the data_approvers worksheet data
            data = self.read_sheet_data("data_approvers!A:C")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return ""  # Return empty string when no data found
            
            # Skip header row and search for matching database and schema
            for row in data[1:]:  # Skip header row
                if len(row) >= 3:
                    sheet_database = row[0].strip()
                    sheet_schema = row[1].strip()
                    approver_email = row[2].strip()
                    
                    if sheet_database.lower() == database.lower() and sheet_schema.lower() == schema.lower():
                        return approver_email
            
            # If not found, return empty string
            return ""
            
        except Exception as e:
            print(f"Error fetching data approver: {str(e)}")
            return ""  # Return empty string on error
    
    def get_masked_columns_mapping(self, user_entity: str) -> Dict[str, Dict[str, Dict[str, list]]]:
        """
        Get database, schema, table, and column mapping from the masked_columns worksheet for a specific entity.
        
        Args:
            user_entity (str): The user's entity
            
        Returns:
            Dict[str, Dict[str, Dict[str, list]]]: Dictionary with database as key, schema as sub-key, table as sub-sub-key, and columns as list
        """
        try:
            # Read the masked_columns worksheet data (A:F based on the image)
            data = self.read_sheet_data("masked_columns!A:F")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return {}
            
            db_schema_table_column_mapping = {}
            
            # Skip header row and build mapping for the specific entity
            for row in data[1:]:  # Skip header row
                if len(row) >= 6:  # A:F columns
                    sheet_entity = row[0].strip()
                    database = row[1].strip()
                    schema = row[2].strip()
                    table = row[3].strip()
                    column = row[4].strip()
                    policy = row[5].strip()
                    
                    # Only include data for the user's entity
                    if sheet_entity.lower() == user_entity.lower():
                        if database and database != "DATABASE_NAME" and schema and schema != "SCHEMA_NAME" and table and table != "TABLE_NAME" and column and column != "COLUMN_NAME":
                            if database not in db_schema_table_column_mapping:
                                db_schema_table_column_mapping[database] = {}
                            
                            if schema not in db_schema_table_column_mapping[database]:
                                db_schema_table_column_mapping[database][schema] = {}
                            
                            if table not in db_schema_table_column_mapping[database][schema]:
                                db_schema_table_column_mapping[database][schema][table] = []
                            
                            db_schema_table_column_mapping[database][schema][table].append(column)
            
            # Sort schemas, tables, and columns for each database
            for database in db_schema_table_column_mapping:
                for schema in db_schema_table_column_mapping[database]:
                    for table in db_schema_table_column_mapping[database][schema]:
                        db_schema_table_column_mapping[database][schema][table] = sorted(list(set(db_schema_table_column_mapping[database][schema][table])))
            
            return db_schema_table_column_mapping
            
        except Exception as e:
            print(f"Error fetching masked columns mapping: {str(e)}")
            return {}
    
    def get_masked_database_options(self, user_entity: str) -> list:
        """
        Get distinct database names from the masked_columns worksheet for a specific entity.
        
        Args:
            user_entity (str): The user's entity
            
        Returns:
            list: List of distinct database names
        """
        try:
            # Read the masked_columns worksheet data (A:F based on the image)
            data = self.read_sheet_data("masked_columns!A:F")
            
            if not data or len(data) < 2:  # Need at least header + 1 data row
                return ["Select Database"]
            
            databases = set()
            
            # Skip header row and collect distinct databases for the specific entity
            for row in data[1:]:  # Skip header row
                if len(row) >= 6:  # A:F columns
                    sheet_entity = row[0].strip()
                    database = row[1].strip()
                    
                    # Only include databases for the user's entity
                    if sheet_entity.lower() == user_entity.lower():
                        if database and database != "DATABASE_NAME":
                            databases.add(database)
            
            # Convert to sorted list
            databases_list = ["Select Database"] + sorted(list(databases))
            
            return databases_list
            
        except Exception as e:
            print(f"Error fetching masked database options: {str(e)}")
            return ["Select Database"]
    
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
    
    def append_user_response(self, request_data: Dict[str, str]) -> bool:
        """
        Append user creation request response to the user_responses worksheet.
        
        Args:
            request_data (Dict[str, str]): Dictionary containing the form data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from datetime import datetime
            
            # Prepare the row data for the user_responses worksheet
            # Based on the columns: Request_id, User, RM_APPROVER, BU, Entity, CREATED_AT, Approval_status, Approval_ts
            row_data = [
                request_data.get('request_id', ''),
                request_data.get('user_email', ''),
                request_data.get('manager_email', ''),
                request_data.get('business_unit', ''),
                request_data.get('entity', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # CREATED_AT (format: 2025-08-18 13:18:28)
                'Pending',  # Approval_status
                ''  # Approval_ts (empty for pending requests)
            ]
            
            # Append the data to the user_responses worksheet
            connection = self.get_sheet_connection()
            
            # Build the API URL for appending
            url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/user_responses!A:Z:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
            
            # Prepare the request body
            body = {
                "values": [row_data]
            }
            
            # Make the request
            response = requests.post(url, headers=connection['headers'], json=body)
            response.raise_for_status()
            
            print(f"✅ User response appended successfully: {request_data.get('request_id', '')}")
            return True
            
        except Exception as e:
            print(f"❌ Error appending user response: {str(e)}")
            return False
    
    def append_table_access_response(self, request_data: Dict[str, Any]) -> bool:
        """
        Append table access request response to the responses worksheet with new L1-L5 approver structure.
        
        Args:
            request_data (Dict[str, Any]): Dictionary containing the form data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from datetime import datetime
            # Import the sequential approval service to get approvers
            sys.path.append(os.path.join(os.path.dirname(__file__)))
            from sequential_approval_service_fixed import SequentialApprovalService
            
            # Handle table names based on selection
            table_names = request_data.get('tables', [])
            if isinstance(table_names, list):
                if table_names == ["ALL"]:
                    table_name_value = "ALL"
                else:
                    # Join selected tables with comma separator
                    table_name_value = ", ".join(table_names)
            else:
                table_name_value = str(table_names)
            
            # Get L1-L5 approvers using the sequential approval service
            approval_service = SequentialApprovalService()
            # approvers = approval_service.get_approvers_for_request(request_data)
            approvers = approval_service.get_table_request_approvers(request_data)
            
            # Prepare the row data for the responses worksheet with new structure
            # New columns: REQUEST_TYPE, REQUEST_ID, USER_NAME, EMAIL, ENTITY, DEFAULT_ROLE, DATABASE, SCHEMA, TABLE_OPTIONS, TABLE_NAME, COLUMN_NAME, GRANTEE, REQUESTING_FOR, VALIDITY_DAYS, REASON_CATEGORY, REASON_FOR_REQUEST, L1_APPROVER, L2_APPROVER, L3_APPROVER, L4_APPROVER, L5_APPROVER, CREATED_AT, L1_APPROVER_STATUS, L2_APPROVER_STATUS, L3_APPROVER_STATUS, L4_APPROVER_STATUS, L5_APPROVER_STATUS, L1_APPROVER_TS, L2_APROVER_TS, L3_APPROVER_TS, L4_APROVER_TS, L5_APROVER_TS
            row_data = [
                "Table request",  # REQUEST_TYPE
                request_data.get('request_id', ''),  # REQUEST_ID
                request_data.get('user_name', ''),  # USER_NAME
                request_data.get('user_email', ''),  # EMAIL
                request_data.get('entity', ''),  # ENTITY
                request_data.get('default_role', ''),  # DEFAULT_ROLE
                request_data.get('database', ''),  # DATABASE
                request_data.get('schema', ''),  # SCHEMA
                request_data.get('table_selection', ''),  # TABLE_OPTIONS
                table_name_value,  # TABLE_NAME (comma-separated or "ALL")
                '',  # COLUMN_NAME (blank as requested)
                request_data.get('requesting_for_type', ''),  # GRANTEE
                request_data.get('requesting_for_value', ''),  # REQUESTING_FOR
                request_data.get('validity_days', ''),  # VALIDITY_DAYS
                request_data.get('reason_category', ''),  # REASON_CATEGORY
                request_data.get('reason', ''),  # REASON_FOR_REQUEST
                approvers.get('L1', ''),  # L1_APPROVER
                approvers.get('L2', ''),  # L2_APPROVER
                approvers.get('L3', ''),  # L3_APPROVER
                approvers.get('L4', ''),  # L4_APPROVER
                approvers.get('L5', ''),  # L5_APPROVER
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # CREATED_AT (format: 2025-08-18 13:18:28)
                'Pending' if approvers.get('L1', '') else '',  # L1_APPROVER_STATUS
                'Pending' if approvers.get('L2', '') else '',  # L2_APPROVER_STATUS
                'Pending' if approvers.get('L3', '') else '',  # L3_APPROVER_STATUS
                'Pending' if approvers.get('L4', '') else '',  # L4_APPROVER_STATUS
                'Pending' if approvers.get('L5', '') else '',  # L5_APPROVER_STATUS
                '',  # L1_APPROVER_TS (empty for pending requests)
                '',  # L2_APROVER_TS (empty for pending requests)
                '',  # L3_APPROVER_TS (empty for pending requests)
                '',  # L4_APROVER_TS (empty for pending requests)
                ''   # L5_APROVER_TS (empty for pending requests)
            ]
            
            # Append the data to the responses worksheet
            connection = self.get_sheet_connection()
            
            # Build the API URL for appending (extended range to accommodate new columns)
            url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/responses!A:AC:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
            
            # Prepare the request body
            body = {
                "values": [row_data]
            }
            
            # Make the request
            response = requests.post(url, headers=connection['headers'], json=body)
            response.raise_for_status()
            
            print(f"✅ Table access response appended successfully: {request_data.get('request_id', '')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error appending table access response: {str(e)}")
            return False
    
    def append_column_unhashing_response(self, request_data: Dict[str, Any]) -> bool:
        """
        Append column unhashing request response to the responses worksheet with new L1-L5 approver structure.
        
        Args:
            request_data (Dict[str, Any]): Dictionary containing the form data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from datetime import datetime
            # Import the sequential approval service to get approvers
            sys.path.append(os.path.join(os.path.dirname(__file__)))
            from sequential_approval_service_fixed import SequentialApprovalService
            
            # Handle column names based on selection
            column_names = request_data.get('columns', [])
            if isinstance(column_names, list):
                if column_names == ["ALL"]:
                    column_name_value = "ALL"
                else:
                    # Join selected columns with comma separator
                    column_name_value = ", ".join(column_names)
            else:
                column_name_value = str(column_names)
            
            # Get L1-L5 approvers using the sequential approval service
            approval_service = SequentialApprovalService()
            approvers = approval_service.get_approvers_for_request(request_data)
            
            # Prepare the row data for the responses worksheet with new structure
            # New columns: REQUEST_TYPE, REQUEST_ID, USER_NAME, EMAIL, ENTITY, DEFAULT_ROLE, DATABASE, SCHEMA, TABLE_OPTIONS, TABLE_NAME, COLUMN_NAME, GRANTEE, REQUESTING_FOR, VALIDITY_DAYS, REASON_CATEGORY, REASON_FOR_REQUEST, L1_APPROVER, L2_APPROVER, L3_APPROVER, L4_APPROVER, L5_APPROVER, CREATED_AT, L1_APPROVER_STATUS, L2_APPROVER_STATUS, L3_APPROVER_STATUS, L4_APPROVER_STATUS, L5_APPROVER_STATUS, L1_APPROVER_TS, L2_APROVER_TS, L3_APPROVER_TS, L4_APROVER_TS, L5_APROVER_TS
            row_data = [
                "Column request",  # REQUEST_TYPE
                request_data.get('request_id', ''),  # REQUEST_ID
                request_data.get('user_name', ''),  # USER_NAME
                request_data.get('user_email', ''),  # EMAIL
                request_data.get('entity', ''),  # ENTITY
                request_data.get('default_role', ''),  # DEFAULT_ROLE
                request_data.get('database', ''),  # DATABASE
                request_data.get('schema', ''),  # SCHEMA
                request_data.get('column_selection', ''),  # TABLE_OPTIONS (using column_selection for column requests)
                request_data.get('table', ''),  # TABLE_NAME
                column_name_value,  # COLUMN_NAME (comma-separated or "ALL")
                request_data.get('requesting_for_type', ''),  # GRANTEE
                request_data.get('requesting_for_value', ''),  # REQUESTING_FOR
                request_data.get('validity_days', ''),  # VALIDITY_DAYS
                request_data.get('reason_category', ''),  # REASON_CATEGORY
                request_data.get('reason', ''),  # REASON_FOR_REQUEST
                approvers.get('L1', ''),  # L1_APPROVER
                approvers.get('L2', ''),  # L2_APPROVER
                approvers.get('L3', ''),  # L3_APPROVER
                approvers.get('L4', ''),  # L4_APPROVER
                approvers.get('L5', ''),  # L5_APPROVER
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # CREATED_AT (format: 2025-08-18 13:18:28)
                'Pending' if approvers.get('L1', '') else '',  # L1_APPROVER_STATUS
                'Pending' if approvers.get('L2', '') else '',  # L2_APPROVER_STATUS
                'Pending' if approvers.get('L3', '') else '',  # L3_APPROVER_STATUS
                'Pending' if approvers.get('L4', '') else '',  # L4_APPROVER_STATUS
                'Pending' if approvers.get('L5', '') else '',  # L5_APPROVER_STATUS
                '',  # L1_APPROVER_TS (empty for pending requests)
                '',  # L2_APROVER_TS (empty for pending requests)
                '',  # L3_APPROVER_TS (empty for pending requests)
                '',  # L4_APROVER_TS (empty for pending requests)
                ''   # L5_APROVER_TS (empty for pending requests)
            ]
            
            # Append the data to the responses worksheet
            connection = self.get_sheet_connection()
            
            # Build the API URL for appending (extended range to accommodate new columns)
            url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/responses!A:AC:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
            
            # Prepare the request body
            body = {
                "values": [row_data]
            }
            
            # Make the request
            response = requests.post(url, headers=connection['headers'], json=body)
            response.raise_for_status()
            
            print(f"✅ Column unhashing response appended successfully: {request_data.get('request_id', '')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error appending column unhashing response: {str(e)}")
            return False
    
    def append_gsheet_unmasking_response(self, request_data: Dict[str, Any]) -> bool:
        """
        Append GSheet unmasking request response to the gsheet_unmasking_responses worksheet.
        
        Args:
            request_data (Dict[str, Any]): Dictionary containing the form data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from datetime import datetime
            
            # Prepare the row data for the gsheet_unmasking_responses worksheet
            # Columns: REQUEST_ID, USER_NAME, EMAIL, ENTITY, DEFAULT_ROLE, SPREADSHEET_ID, NAMED_RANGE, 
            # WHO HAS ACCESS TO THIS SHEET, END_USER_DESCRIPTION, USE_CASE, REMARKS, 
            # L1_APPROVER, L2_APPROVER, L3_APPROVER, L4_APPROVER, L5_APPROVER, CREATED_AT,
            # L1_APPROVER_STATUS, L2_APPROVER_STATUS, L3_APPROVER_STATUS, L4_APPROVER_STATUS, L5_APPROVER_STATUS,
            # L1_APPROVER_TS, L2_APROVER_TS, L3_APPROVER_TS, L4_APPROVER_TS, L5_APPROVER_TS
            row_data = [
                request_data.get('request_id', ''),  # REQUEST_ID
                request_data.get('user_name', ''),  # USER_NAME
                request_data.get('user_email', ''),  # EMAIL
                request_data.get('entity', ''),  # ENTITY
                request_data.get('default_role', ''),  # DEFAULT_ROLE
                request_data.get('spreadsheet_id', ''),  # SPREADSHEET_ID
                request_data.get('named_range', ''),  # NAMED_RANGE
                request_data.get('who_has_access', ''),  # WHO HAS ACCESS TO THIS SHEET
                request_data.get('end_user_description', ''),  # END_USER_DESCRIPTION
                request_data.get('use_case', ''),  # USE_CASE
                request_data.get('validity_days', ''),  # VALIDITY_DAYS
                request_data.get('remarks', ''),  # REMARKS
                request_data.get('l1_approver', ''),  # L1_APPROVER
                request_data.get('l2_approver', ''),  # L2_APPROVER
                request_data.get('l3_approver', ''),  # L3_APPROVER
                request_data.get('l4_approver', ''),  # L4_APPROVER
                request_data.get('l5_approver', ''),  # L5_APPROVER
                request_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),  # CREATED_AT
                'Pending',  # L1_APPROVER_STATUS
                'Pending',  # L2_APPROVER_STATUS
                'Pending',  # L3_APPROVER_STATUS
                'Pending',  # L4_APPROVER_STATUS
                'Pending',  # L5_APPROVER_STATUS
                '',  # L1_APPROVER_TS (empty for pending requests)
                '',  # L2_APROVER_TS (empty for pending requests)
                '',  # L3_APPROVER_TS (empty for pending requests)
                '',  # L4_APPROVER_TS (empty for pending requests)
                ''   # L5_APPROVER_TS (empty for pending requests)
            ]
            
            # Append the data to the gsheet_unmasking_responses worksheet
            connection = self.get_sheet_connection()
            
            # Build the API URL for appending to gsheet_unmasking_responses worksheet
            url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/gsheet_unmasking_responses!A:AB:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
            
            # Prepare the request body
            body = {
                "values": [row_data]
            }
            
            # Make the request
            response = requests.post(url, headers=connection['headers'], json=body)
            response.raise_for_status()
            
            print(f"✅ GSheet unmasking response appended successfully: {request_data.get('request_id', '')}")
            
            # Send initial approval request to L1 approver using sequential approval service
            try:
                from sequential_approval_service_fixed import SequentialApprovalService
                approval_service = SequentialApprovalService()
                initial_approval_result = approval_service.send_initial_approval_request(request_data)
                print(f"Initial approval request result: {initial_approval_result}")
            except Exception as e:
                print(f"Warning: Could not send initial approval request: {str(e)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error appending GSheet unmasking response: {str(e)}")
            return False
    
    def update_gsheet_unmasking_approval(self, request_id: str, approver_email: str, approval_status: str) -> bool:
        """
        Update GSheet unmasking request approval status using L1-L5 sequential approval system.
        This method now delegates to the sequential approval service.
        
        Args:
            request_id (str): The request ID to update
            approver_email (str): The approver's email
            approval_status (str): 'Approved' or 'Rejected'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"DEBUG: update_gsheet_unmasking_approval called - delegating to sequential approval system")
            print(f"DEBUG: Request: {request_id}, Approver: {approver_email}, Status: {approval_status}")
            
            # Delegate to the sequential approval service which handles L1-L5 approvals and emails
            from sequential_approval_service_fixed import SequentialApprovalService
            sequential_service = SequentialApprovalService()
            
            # Convert "Rejected" to "Reject" for the sequential approval service
            decision = "Reject" if approval_status == "Rejected" else approval_status
            
            result = sequential_service.handle_approval_decision(
                request_id, approver_email, decision
            )
            
            if result.get('success'):
                print(f"✅ GSheet unmasking approval updated successfully: {result.get('message', 'Unknown')}")
                # Clear cache to force immediate refresh
                self.clear_approval_cache()
                return True
            else:
                print(f"❌ GSheet unmasking approval failed: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating GSheet unmasking approval: {str(e)}")
            return False
    
    def get_request_details(self, request_id: str) -> Dict[str, Any]:
        """
        Get request details from both user_responses and responses worksheets.
        
        Args:
            request_id (str): The request ID to search for
            
        Returns:
            Dict[str, Any]: Dictionary containing request details and authorization info
        """
        try:
            # Search in user_responses worksheet first
            user_responses_data = self.read_sheet_data("user_responses!A:H")
            
            if user_responses_data and len(user_responses_data) > 1:
                for row in user_responses_data[1:]:  # Skip header
                    if len(row) >= 3:
                        sheet_request_id = row[0].strip()
                        user_email = row[1].strip()
                        rm_approver = row[2].strip()
                        
                        if sheet_request_id == request_id:
                            return {
                                'found': True,
                                'sheet_type': 'user_responses',
                                'request_id': request_id,
                                'user_email': user_email,
                                'rm_approver': rm_approver,
                                'data_approver': None,  # Not applicable for user creation requests
                                'request_type': 'User Creation',
                                'entity': row[4].strip() if len(row) > 4 else '',
                                'business_unit': row[3].strip() if len(row) > 3 else '',
                                'created_at': row[5].strip() if len(row) > 5 else '',
                                'approval_status': row[6].strip() if len(row) > 6 else 'Pending'
                            }
            
            # Search in responses worksheet
            responses_data = self.read_sheet_data("responses!A:AF")  # Read up to column AF to get all L1-L5 data
            
            if responses_data and len(responses_data) > 1:
                for row in responses_data[1:]:  # Skip header
                    if len(row) >= 20:
                        sheet_request_id = row[1].strip()  # REQUEST_ID is in column B
                        
                        if sheet_request_id == request_id:
                            return {
                                'found': True,
                                'sheet_type': 'responses',
                                'request_id': request_id,
                                'user_email': row[3].strip(),  # EMAIL is in column D

                                'request_type': row[0].strip(),  # REQUEST_TYPE is in column A
                                'entity': row[4].strip(),  # ENTITY is in column E
                                'database': row[6].strip() if len(row) > 6 else '',  # DATABASE is in column G
                                'schema': row[7].strip() if len(row) > 7 else '',  # SCHEMA is in column H
                                'table': row[9].strip() if len(row) > 9 else '',  # TABLE_NAME is in column J
                                'column': row[10].strip() if len(row) > 10 else '',  # COLUMN_NAME is in column K
                                'reason_category': row[14].strip() if len(row) > 14 else '',  # REASON_CATEGORY is in column O
                                'reason': row[15].strip() if len(row) > 15 else '',  # REASON_FOR_REQUEST is in column P
                                'objective': row[15].strip() if len(row) > 15 else '',  # Map REASON_FOR_REQUEST as objective for table/column requests
                                'validity': row[13].strip() if len(row) > 13 else '',  # VALIDITY_DAYS is in column N
                                'created_at': row[21].strip() if len(row) > 21 else '',  # CREATED_AT is at index 21

                                'business_unit': self.get_bu_from_snf_user(row[3].strip()) if len(row) > 3 else '',  # Get BU from snf_user worksheet
                                # L1-L5 Approver names and statuses
                                'l1_approver': row[16].strip() if len(row) > 16 else '',  # L1_APPROVER is at index 16
                                'l2_approver': row[17].strip() if len(row) > 17 else '',  # L2_APPROVER is at index 17
                                'l3_approver': row[18].strip() if len(row) > 18 else '',  # L3_APPROVER is at index 18
                                'l4_approver': row[19].strip() if len(row) > 19 else '',  # L4_APPROVER is at index 19
                                'l5_approver': row[20].strip() if len(row) > 20 else '',  # L5_APPROVER is at index 20
                                'l1_approver_status': row[22].strip() if len(row) > 22 else 'Pending',  # L1_APPROVER_STATUS is at index 22
                                'l2_approver_status': row[23].strip() if len(row) > 23 else 'Pending',  # L2_APPROVER_STATUS is at index 23
                                'l3_approver_status': row[24].strip() if len(row) > 24 else 'Pending',  # L3_APPROVER_STATUS is at index 24
                                'l4_approver_status': row[25].strip() if len(row) > 25 else 'Pending',  # L4_APPROVER_STATUS is at index 25
                                'l5_approver_status': row[26].strip() if len(row) > 26 else 'Pending'   # L5_APPROVER_STATUS is at index 26
                            }
            
            # Search in gsheet_unmasking_responses worksheet
            gsheet_responses_data = self.read_sheet_data("gsheet_unmasking_responses!A:AB")
            
            if gsheet_responses_data and len(gsheet_responses_data) > 1:
                for row in gsheet_responses_data[1:]:  # Skip header
                    if len(row) >= 1:
                        sheet_request_id = row[0].strip()  # REQUEST_ID is in column A
                        
                        if sheet_request_id == request_id:
                            return {
                                'found': True,
                                'sheet_type': 'gsheet_unmasking_responses',
                                'request_id': request_id,
                                'user_email': row[2].strip() if len(row) > 2 else '',  # EMAIL is in column C
                                'request_type': 'GSheet Unmasking',
                                'entity': row[3].strip() if len(row) > 3 else '',  # ENTITY is in column D
                                'database': 'Google Sheets',
                                'spreadsheet_id': row[5].strip() if len(row) > 5 else '',  # SPREADSHEET_ID is in column F
                                'named_range': row[6].strip() if len(row) > 6 else '',  # NAMED_RANGE is in column G
                                'who_has_access': row[7].strip() if len(row) > 7 else '',  # WHO HAS ACCESS TO THIS SHEET is in column H
                                'end_user_description': row[8].strip() if len(row) > 8 else '',  # END_USER_DESCRIPTION is in column I
                                'use_case': row[9].strip() if len(row) > 9 else '',  # USE_CASE is in column J
                                'objective': row[11].strip() if len(row) > 11 else '',  # REMARKS is in column L
                                'validity': row[10].strip() if len(row) > 10 else '',  # VALIDITY_DAYS is in column K
                                'created_at': row[16].strip() if len(row) > 16 else '',  # CREATED_AT is in column Q
                                
                                'business_unit': self.get_bu_from_snf_user(row[2].strip()) if len(row) > 2 else '',  # Get BU from snf_user worksheet
                                # L1-L5 Approver names and statuses
                                'l1_approver': row[12].strip() if len(row) > 12 else '',  # L1_APPROVER is in column M
                                'l2_approver': row[13].strip() if len(row) > 13 else '',  # L2_APPROVER is in column N
                                'l3_approver': row[14].strip() if len(row) > 14 else '',  # L3_APPROVER is in column O
                                'l4_approver': row[15].strip() if len(row) > 15 else '',  # L4_APPROVER is in column P
                                'l5_approver': row[16].strip() if len(row) > 16 else '',  # L5_APPROVER is in column Q
                                'l1_approver_status': row[18].strip() if len(row) > 18 else 'Pending',  # L1_APPROVER_STATUS is in column S
                                'l2_approver_status': row[19].strip() if len(row) > 19 else 'Pending',  # L2_APPROVER_STATUS is in column T
                                'l3_approver_status': row[20].strip() if len(row) > 20 else 'Pending',  # L3_APPROVER_STATUS is in column U
                                'l4_approver_status': row[21].strip() if len(row) > 21 else 'Pending',  # L4_APPROVER_STATUS is in column V
                                'l5_approver_status': row[22].strip() if len(row) > 22 else 'Pending'   # L5_APPROVER_STATUS is in column W
                            }
            
            # Request not found
            return {
                'found': False,
                'message': f'Request ID {request_id} not found in any worksheet'
            }
            
        except Exception as e:
            print(f"Error fetching request details: {str(e)}")
            return {
                'found': False,
                'message': f'Error fetching request details: {str(e)}'
            }
    
    def is_user_authorized_for_request(self, request_id: str, user_email: str) -> Dict[str, Any]:
        """
        Check if the current user is authorized to approve/reject the request using L1-L5 sequential approval system.
        
        Args:
            request_id (str): The request ID to check
            user_email (str): The current user's email
            
        Returns:
            Dict[str, Any]: Dictionary containing authorization status and details
        """
        try:
            # Get request details
            request_details = self.get_request_details(request_id)
            
            if not request_details['found']:
                return {
                    'authorized': False,
                    'message': request_details['message'],
                    'request_details': None
                }
            
            # Check authorization based on sheet type
            if request_details['sheet_type'] == 'user_responses':
                # For user creation requests, check if user is the RM approver (still uses old system)
                if user_email.lower() == request_details['rm_approver'].lower():
                    return {
                        'authorized': True,
                        'approver_type': 'RM_APPROVER',
                        'message': 'Authorized as RM Approver for User Creation Request',
                        'request_details': request_details
                    }
                else:
                    return {
                        'authorized': False,
                        'message': f'You are not authorized to approve this request. RM Approver: {request_details["rm_approver"]}',
                        'request_details': request_details
                    }
            
            elif request_details['sheet_type'] == 'gsheet_unmasking_responses':
                # For GSheet unmasking requests, use L1-L5 sequential approval system
                try:
                    from sequential_approval_service_fixed import SequentialApprovalService
                    sequential_service = SequentialApprovalService()
                    
                    # Build request data for the sequential service
                    temp_request_data = {
                        'user_email': request_details.get('user_email', ''),
                        'requester_email': request_details.get('user_email', '')
                    }
                    
                    # Get approvers for this request
                    approvers = sequential_service.get_approvers_for_request(temp_request_data)
                    
                    # Check if user is assigned as ANY L1-L5 approver
                    user_approver_levels = []
                    for level, approver_email in approvers.items():
                        if approver_email and approver_email.lower() == user_email.lower():
                            user_approver_levels.append(level)
                    
                    if user_approver_levels:
                        # Get current approval status to determine which level is currently pending
                        approval_status = {}
                        if 'l1_approver_status' in request_details: approval_status['L1'] = request_details['l1_approver_status']
                        if 'l2_approver_status' in request_details: approval_status['L2'] = request_details['l2_approver_status']
                        if 'l3_approver_status' in request_details: approval_status['L3'] = request_details['l3_approver_status']
                        if 'l4_approver_status' in request_details: approval_status['L4'] = request_details['l4_approver_status']
                        if 'l5_approver_status' in request_details: approval_status['L5'] = request_details['l5_approver_status']
                        
                        # Get the current pending level
                        next_pending_level = sequential_service.get_next_pending_approver(approval_status, approvers)
                        
                        if next_pending_level and next_pending_level in user_approver_levels:
                            message = f'Authorized as {next_pending_level} Approver for GSheet Unmasking Request (Current Pending Level)'
                        else:
                            message = f'You are {", ".join(user_approver_levels)} Approver(s) for GSheet Unmasking, but current pending level is {next_pending_level}'
                        
                        return {
                            'authorized': True,
                            'approver_type': f'L1_TO_L5_APPROVER',
                            'approver_levels': user_approver_levels,
                            'message': message,
                            'request_details': request_details
                        }
                    else:
                        return {
                            'authorized': False,
                            'message': 'You are not authorized to approve this GSheet unmasking request in the L1-L5 sequential approval chain',
                            'request_details': request_details
                        }
                        
                except Exception as e:
                    print(f"Error checking L1-L5 authorization for GSheet request: {str(e)}")
                    return {
                        'authorized': False,
                        'message': f'Error checking authorization for GSheet request: {str(e)}',
                        'request_details': request_details
                    }
            
            elif request_details['sheet_type'] == 'responses':
                # For table/column requests, use L1-L5 sequential approval system
                try:
                    from sequential_approval_service_fixed import SequentialApprovalService
                    sequential_service = SequentialApprovalService()
                    
                    # Build request data for the sequential service
                    temp_request_data = {
                        'user_email': request_details.get('user_email', ''),
                        'requester_email': request_details.get('user_email', '')
                    }
                    
                    # Get approvers for this request
                    approvers = sequential_service.get_approvers_for_request(temp_request_data)
                    
                    # Check if user is assigned as ANY L1-L5 approver
                    user_approver_levels = []
                    for level, approver_email in approvers.items():
                        if approver_email and approver_email.lower() == user_email.lower():
                            user_approver_levels.append(level)
                    
                    if user_approver_levels:
                        # Get current approval status to determine which level is currently pending
                        approval_status = {}
                        if 'l1_approver_status' in request_details: approval_status['L1'] = request_details['l1_approver_status']
                        if 'l2_approver_status' in request_details: approval_status['L2'] = request_details['l2_approver_status']
                        if 'l3_approver_status' in request_details: approval_status['L3'] = request_details['l3_approver_status']
                        if 'l4_approver_status' in request_details: approval_status['L4'] = request_details['l4_approver_status']
                        if 'l5_approver_status' in request_details: approval_status['L5'] = request_details['l5_approver_status']
                        
                        # Get the current pending level
                        next_pending_level = sequential_service.get_next_pending_approver(approval_status, approvers)
                        
                        if next_pending_level and next_pending_level in user_approver_levels:
                            message = f'Authorized as {next_pending_level} Approver (Current Pending Level)'
                        else:
                            message = f'You are {", ".join(user_approver_levels)} Approver(s), but current pending level is {next_pending_level}'
                        
                        return {
                            'authorized': True,
                            'approver_type': f'L1_TO_L5_APPROVER',
                            'approver_levels': user_approver_levels,
                            'message': message,
                            'request_details': request_details
                        }
                    else:
                        return {
                            'authorized': False,
                            'message': 'You are not authorized to approve this request in the L1-L5 sequential approval chain',
                            'request_details': request_details
                        }
                        
                except Exception as e:
                    print(f"Error checking L1-L5 authorization: {str(e)}")
                    return {
                        'authorized': False,
                        'message': f'Error checking authorization: {str(e)}',
                        'request_details': request_details
                    }
                else:
                    return {
                        'authorized': False,
                        'message': f'You are not authorized to approve this request. RM Approver: {request_details["rm_approver"]}, Data Approver: {request_details["data_approver"]}',
                        'request_details': request_details
                    }
            
            return {
                'authorized': False,
                'message': 'Unknown request type',
                'request_details': request_details
            }
            
        except Exception as e:
            print(f"Error checking authorization: {str(e)}")
            return {
                'authorized': False,
                'message': f'Error checking authorization: {str(e)}',
                'request_details': None
            }
    
    def update_user_creation_approval(self, request_id: str, approver_email: str, approval_status: str) -> bool:
        """
        Update user creation request approval status in user_responses worksheet.
        
        Args:
            request_id (str): The request ID to update
            approver_email (str): The approver's email
            approval_status (str): 'Approved' or 'Rejected'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from datetime import datetime
            
            # Read the user_responses worksheet to find the row to update
            data = self.read_sheet_data("user_responses!A:H")
            
            if not data or len(data) < 2:
                print(f"❌ No data found in user_responses worksheet")
                return False
            
            # Find the row with matching request_id
            row_index = None
            for i, row in enumerate(data[1:], start=2):  # Start from row 2 (skip header)
                if len(row) >= 1 and row[0].strip() == request_id:
                    row_index = i
                    break
            
            if row_index is None:
                print(f"❌ Request ID {request_id} not found in user_responses worksheet")
                return False
            
            # Prepare the update data
            # Columns: Request_id, User, RM_APPROVER, BU, Entity, CREATED_AT, Approval_status, Approval_ts
            update_data = [
                '',  # Request_id (unchanged)
                '',  # User (unchanged)
                '',  # RM_APPROVER (unchanged)
                '',  # BU (unchanged)
                '',  # Entity (unchanged)
                '',  # CREATED_AT (unchanged)
                approval_status,  # Approval_status
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Approval_ts
            ]
            
            # Update the specific row
            connection = self.get_sheet_connection()
            
            # Build the API URL for updating specific range
            range_name = f"user_responses!G{row_index}:H{row_index}"
            url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/{range_name}?valueInputOption=RAW"
            
            # Prepare the request body
            body = {
                "values": [[approval_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]
            }
            
            # Make the request
            response = requests.put(url, headers=connection['headers'], json=body)
            
            response.raise_for_status()
            
            print(f"✅ User creation approval updated successfully: {request_id} - {approval_status}")
            
            # Send email notification to user
            try:
                self.send_user_creation_approval_email(request_id, approval_status, approver_email)
                print(f"✅ Email notification sent for user creation approval: {request_id}")
            except Exception as email_error:
                print(f"⚠️ Email notification failed: {str(email_error)}")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error updating user creation approval: {e}")
            print(f"❌ Status Code: {e.response.status_code}")
            print(f"❌ Response: {e.response.text}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Request Error updating user creation approval: {e}")
            return False
        except Exception as e:
            print(f"❌ Error updating user creation approval: {str(e)}")
            return False
    
    def update_table_column_approval(self, request_id: str, approver_email: str, approval_type: str, approval_status: str) -> bool:
        """
        Update table/column request approval status using L1-L5 sequential approval system.
        
        Args:
            request_id (str): The request ID to update
            approver_email (str): The approver's email
            approval_type (str): Ignored - using L1-L5 system instead
            approval_status (str): 'Approved' or 'Rejected'
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from datetime import datetime
            
            # Read the responses worksheet to find the row and get approver info
            data = self.read_sheet_data("responses!A:AF")  # Read up to column AF to get all L1-L5 data
            
            if not data or len(data) < 2:
                print(f"❌ No data found in responses worksheet")
                return False
            
            # Find the row with matching request_id
            row_index = None
            request_row = None
            for i, row in enumerate(data[1:], start=2):  # Start from row 2 (skip header)
                if len(row) >= 2 and row[1].strip() == request_id:  # REQUEST_ID is in column B
                    row_index = i
                    request_row = row
                    break
            
            if row_index is None or request_row is None:
                print(f"❌ Request ID {request_id} not found in responses worksheet")
                return False
            
            # Determine which L-level(s) this approver belongs to by checking L1_APPROVER through L5_APPROVER columns
            # L1_APPROVER is column Q (17), L2_APPROVER is column R (18), etc.
            approver_levels = []
            level_mapping = {
                'L1': {'approver_col': 16, 'status_col': 'W', 'ts_col': 'AB'},  # L1_APPROVER (Q), L1_APPROVER_STATUS (W), L1_APPROVER_TS (AB)
                'L2': {'approver_col': 17, 'status_col': 'X', 'ts_col': 'AC'},  # L2_APPROVER (R), L2_APPROVER_STATUS (X), L2_APROVER_TS (AC)
                'L3': {'approver_col': 18, 'status_col': 'Y', 'ts_col': 'AD'},  # L3_APPROVER (S), L3_APPROVER_STATUS (Y), L3_APPROVER_TS (AD)
                'L4': {'approver_col': 19, 'status_col': 'Z', 'ts_col': 'AE'},  # L4_APPROVER (T), L4_APPROVER_STATUS (Z), L4_APROVER_TS (AE)
                'L5': {'approver_col': 20, 'status_col': 'AA', 'ts_col': 'AF'}  # L5_APPROVER (U), L5_APPROVER_STATUS (AA), L5_APROVER_TS (AF)
            }
            
            # Check each level to see if this approver email matches
            for level, mapping in level_mapping.items():
                approver_col_index = mapping['approver_col']
                if len(request_row) > approver_col_index and request_row[approver_col_index]:
                    if request_row[approver_col_index].strip().lower() == approver_email.lower():
                        approver_levels.append(level)
            
            if not approver_levels:
                print(f"❌ Approver email {approver_email} not found in any L1-L5 approver columns for request {request_id}")
                return False
            
            print(f"✅ Found approver {approver_email} as level(s): {approver_levels}")
            
            # Update status and timestamp for each level this approver belongs to
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Update the specific columns individually
            connection = self.get_sheet_connection()
            
            for level in approver_levels:
                mapping = level_mapping[level]
                
                # Update status column
                status_range = f"responses!{mapping['status_col']}{row_index}"
                status_body = {"values": [[approval_status]]}
                status_url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/{status_range}?valueInputOption=RAW"
                
                response_status = requests.put(status_url, headers=connection['headers'], json=status_body)
                response_status.raise_for_status()
                
                # Update timestamp column (only if approved)
                if approval_status.lower() == 'approved':
                    ts_range = f"responses!{mapping['ts_col']}{row_index}"
                    ts_body = {"values": [[current_timestamp]]}
                    ts_url = f"{connection['base_url']}/{connection['spreadsheet_id']}/values/{ts_range}?valueInputOption=RAW"
                    
                    response_ts = requests.put(ts_url, headers=connection['headers'], json=ts_body)
                    response_ts.raise_for_status()
                
                print(f"✅ Updated {level} status to {approval_status} for request {request_id}")
            
            print(f"✅ Sequential approval updated successfully: {request_id} - {approval_status} for levels: {approver_levels}")
            
            # Trigger sequential approval flow to find next approver and send email
            try:
                from sequential_approval_service_fixed import SequentialApprovalService
                sequential_service = SequentialApprovalService()
                
                # Build request data for sequential service
                request_data = {
                    'request_id': request_id,
                    'user_email': '',  # Will be filled by sequential service from sheet
                    'requester_email': ''  # Will be filled by sequential service from sheet
                }
                
                sequential_result = sequential_service.handle_approval_decision(
                    request_id, approver_email, approval_status
                )
                
                if sequential_result.get('success'):
                    print(f"✅ Email notification sent for sequential approval: {request_id}")
                    print(f"Sequential flow result: {sequential_result.get('message', 'Unknown')}")
                else:
                    print(f"⚠️ Sequential approval failed: {sequential_result.get('message', 'Unknown error')}")
                    
            except Exception as seq_error:
                print(f"⚠️ Sequential approval processing failed: {str(seq_error)}")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error updating table/column approval: {e}")
            print(f"❌ Status Code: {e.response.status_code}")
            print(f"❌ Response: {e.response.text}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Request Error updating table/column approval: {e}")
            return False
        except Exception as e:
            print(f"❌ Error updating table/column approval: {str(e)}")
            return False
    
    def update_multi_approver_status(self, request_id: str, approver_email: str, approval_status: str) -> bool:
        """
        Update multi-approver status using L1-L5 sequential approval system.
        This function now delegates to the single approver function since we're using L1-L5 levels.
        Args:
            request_id (str): The request ID to update
            approver_email (str): The approver's email
            approval_status (str): 'Approved' or 'Rejected'
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Since we're using L1-L5 sequential approval, multi-approver just means
        # the same person appears in multiple L-level columns, which is already
        # handled by the update_table_column_approval function
        print(f"🔄 Multi-approver request - delegating to sequential approval system")
        return self.update_table_column_approval(request_id, approver_email, "SEQUENTIAL", approval_status)
    
    def send_user_creation_approval_email(self, request_id: str, approval_status: str, approver_email: str) -> bool:
        """
        Send approval notification email for user creation requests.
        
        Args:
            request_id (str): The request ID
            approval_status (str): 'Approved' or 'Rejected'
            approver_email (str): The approver's email
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get request details from user_responses worksheet
            data = self.read_sheet_data("user_responses!A:H")
            
            if not data or len(data) < 2:
                return False
            
            # Find the request details
            request_data = {}
            for row in data[1:]:  # Skip header
                if len(row) >= 1 and row[0].strip() == request_id:
                    request_data = {
                        'request_id': request_id,
                        'user_email': row[1].strip() if len(row) > 1 else '',
                        'user_name': row[1].strip().split('@')[0] if len(row) > 1 and '@' in row[1] else '',
                        'entity': row[4].strip() if len(row) > 4 else '',
                        'business_unit': row[3].strip() if len(row) > 3 else '',
                        'approval_status': approval_status,
                        'approver_email': approver_email
                    }
                    break
            
            if not request_data.get('user_email'):
                return False
            
            # Create email content
            email_content = create_approval_notification_email(request_data, approval_status, approver_email)
            
            # Send email
            result = send_email(
                to_email=request_data['user_email'],
                subject=f"User Creation Request {approval_status} - {request_id}",
                content=email_content
            )
            
            return result.get('success', False)
            
        except Exception as e:
            print(f"Error sending user creation approval email: {str(e)}")
            return False
    
    def send_table_column_approval_email(self, request_id: str, approval_type: str, approval_status: str, approver_email: str) -> bool:
        """
        Send approval notification email for table/column requests (single approver).
        
        Args:
            request_id (str): The request ID
            approval_type (str): 'RM_APPROVER' or 'DATA_APPROVER'
            approval_status (str): 'Approved' or 'Rejected'
            approver_email (str): The approver's email
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get request details from responses worksheet
            data = self.read_sheet_data("responses!A:V")
            
            if not data or len(data) < 2:
                return False
            
            # Find the request details
            request_data = {}
            for row in data[1:]:  # Skip header
                if len(row) >= 2 and row[1].strip() == request_id:
                    request_data = {
                        'request_id': request_id,
                        'user_email': row[3].strip() if len(row) > 3 else '',  # EMAIL column
                        'user_name': row[2].strip() if len(row) > 2 else '',  # USER_NAME column
                        'entity': row[4].strip() if len(row) > 4 else '',  # ENTITY column
                        'database': row[6].strip() if len(row) > 6 else '',  # DATABASE column
                        'schema': row[7].strip() if len(row) > 7 else '',  # SCHEMA column
                        'table': row[9].strip() if len(row) > 9 else '',  # TABLE_NAME column
                        'column': row[10].strip() if len(row) > 10 else '',  # COLUMN_NAME column
                        'reason': row[14].strip() if len(row) > 14 else '',  # REASON_FOR_REQUEST column
                        'validity_days': row[13].strip() if len(row) > 13 else '',  # VALIDITY_DAYS column
                        'request_type': row[0].strip() if len(row) > 0 else '',  # REQUEST_TYPE column
                        'approval_type': approval_type,
                        'approval_status': approval_status,
                        'approver_email': approver_email
                    }
                    break
            
            if not request_data.get('user_email'):
                return False
            
            # Create email content based on request type
            if request_data['request_type'] == 'Table request':
                email_content = create_table_access_approval_notification_email(request_data, approval_type, approval_status, approver_email)
                subject = f"Table Access Request {approval_status} by {approval_type} - {request_id}"
            else:  # Column request
                email_content = create_column_unhashing_approval_notification_email(request_data, approval_type, approval_status, approver_email)
                subject = f"Column Unhashing Request {approval_status} by {approval_type} - {request_id}"
            
            # Send email
            result = send_email(
                to_email=request_data['user_email'],
                subject=subject,
                content=email_content
            )
            
            return result.get('success', False)
            
        except Exception as e:
            print(f"Error sending table/column approval email: {str(e)}")
            return False
    
    def send_multi_approver_notification_email(self, request_id: str, approval_status: str, approver_email: str) -> bool:
        """
        Send approval notification email for multi-approver scenarios (same person is both RM and Data approver).
        
        Args:
            request_id (str): The request ID
            approval_status (str): 'Approved' or 'Rejected'
            approver_email (str): The approver's email
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get request details from responses worksheet
            data = self.read_sheet_data("responses!A:V")
            
            if not data or len(data) < 2:
                return False
            
            # Find the request details
            request_data = {}
            for row in data[1:]:  # Skip header
                if len(row) >= 2 and row[1].strip() == request_id:
                    request_data = {
                        'request_id': request_id,
                        'user_email': row[3].strip() if len(row) > 3 else '',  # EMAIL column
                        'user_name': row[2].strip() if len(row) > 2 else '',  # USER_NAME column
                        'entity': row[4].strip() if len(row) > 4 else '',  # ENTITY column
                        'database': row[6].strip() if len(row) > 6 else '',  # DATABASE column
                        'schema': row[7].strip() if len(row) > 7 else '',  # SCHEMA column
                        'table': row[9].strip() if len(row) > 9 else '',  # TABLE_NAME column
                        'column': row[10].strip() if len(row) > 10 else '',  # COLUMN_NAME column
                        'reason': row[14].strip() if len(row) > 14 else '',  # REASON_FOR_REQUEST column
                        'validity_days': row[13].strip() if len(row) > 13 else '',  # VALIDITY_DAYS column
                        'request_type': row[0].strip() if len(row) > 0 else '',  # REQUEST_TYPE column
                        'approval_status': approval_status,
                        'approver_email': approver_email
                    }
                    break
            
            if not request_data.get('user_email'):
                return False
            
            # Create email content based on request type
            if request_data['request_type'] == 'Table request':
                email_content = create_multi_approver_notification_email(request_data, approval_status, approver_email)
                subject = f"Table Access Request {approval_status} (Multi-Approver) - {request_id}"
            else:  # Column request
                email_content = create_multi_approver_notification_email(request_data, approval_status, approver_email)
                subject = f"Column Unhashing Request {approval_status} (Multi-Approver) - {request_id}"
            
            # Send email
            result = send_email(
                to_email=request_data['user_email'],
                subject=subject,
                content=email_content
            )
            
            return result.get('success', False)
            
        except Exception as e:
            print(f"Error sending multi-approver notification email: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test the connection to the Google Sheet.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            connection = self.get_sheet_connection()
            return True
        except Exception:
            return False

# Global form services instance
form_services = FormServices()

def get_form_services() -> FormServices:
    """
    Get the global form services instance.
    
    Returns:
        FormServices: The global form services instance
    """
    return form_services

def get_sheet_connection() -> Dict[str, Any]:
    """
    Convenience function to get sheet connection.
    
    Returns:
        Dict[str, Any]: Connection details
    """
    return form_services.get_sheet_connection()

def get_manager_email(user_email: str) -> str:
    """
    Convenience function to get manager email for a user.
    
    Args:
        user_email (str): The user's email address
        
    Returns:
        str: The manager's email address or placeholder if not found
    """
    return form_services.get_manager_email(user_email)

def get_entity_bu_options() -> Dict[str, list]:
    """
    Convenience function to get entity and BU options.
    
    Returns:
        Dict[str, list]: Dictionary with 'entities' and 'business_units' lists
    """
    return form_services.get_entity_bu_options()

def get_entity_bu_mapping() -> Dict[str, list]:
    """
    Convenience function to get entity to BU mapping.
    
    Returns:
        Dict[str, list]: Dictionary with entity as key and list of BUs as value
    """
    return form_services.get_entity_bu_mapping()

def append_user_response(request_data: Dict[str, str]) -> bool:
    """
    Convenience function to append user response to sheet.
    
    Args:
        request_data (Dict[str, str]): Dictionary containing the form data
        
    Returns:
        bool: True if successful, False otherwise
    """
    return form_services.append_user_response(request_data)

def get_user_entity_role(user_email: str) -> Dict[str, str]:
    """
    Convenience function to get user entity and role.
    
    Args:
        user_email (str): The user's email address
        
    Returns:
        Dict[str, str]: Dictionary with 'entity' and 'default_role'
    """
    return form_services.get_user_entity_role(user_email)

def get_database_schema_table_mapping() -> Dict[str, Dict[str, list]]:
    """
    Convenience function to get database, schema, and table mapping.
    
    Returns:
        Dict[str, Dict[str, list]]: Dictionary with database as key, schema as sub-key, and tables as list
    """
    return form_services.get_database_schema_table_mapping()

def get_database_options() -> list:
    """
    Convenience function to get database options.
    
    Returns:
        list: List of distinct database names
    """
    return form_services.get_database_options()

def get_generic_user_role_options(user_entity: str) -> Dict[str, list]:
    """
    Convenience function to get generic user and role options.
    
    Args:
        user_entity (str): The user's entity
        
    Returns:
        Dict[str, list]: Dictionary with 'generic_users' and 'generic_roles' lists
    """
    return form_services.get_generic_user_role_options(user_entity)

def get_rm_approver(user_email: str) -> str:
    """
    Convenience function to get RM approver for a user.
    
    Args:
        user_email (str): The user's email address
        
    Returns:
        str: The RM approver's email address or placeholder if not found
    """
    return form_services.get_rm_approver(user_email)

def get_data_approver(database: str, schema: str) -> str:
    """
    Convenience function to get data approver for database and schema.
    
    Args:
        database (str): The selected database name
        schema (str): The selected schema name
        
    Returns:
        str: The data approver's email address or empty string if not found
    """
    return form_services.get_data_approver(database, schema)

def append_table_access_response(request_data: Dict[str, Any]) -> bool:
    """
    Convenience function to append table access response to sheet.
    
    Args:
        request_data (Dict[str, Any]): Dictionary containing the form data
        
    Returns:
        bool: True if successful, False otherwise
    """
    return form_services.append_table_access_response(request_data)

def append_column_unhashing_response(request_data: Dict[str, Any]) -> bool:
    """
    Convenience function to append column unhashing response to sheet.
    
    Args:
        request_data (Dict[str, Any]): Dictionary containing the form data
        
    Returns:
        bool: True if successful, False otherwise
    """
    return form_services.append_column_unhashing_response(request_data)

def append_gsheet_unmasking_response(request_data: Dict[str, Any]) -> bool:
    """
    Convenience function to append GSheet unmasking response to sheet.
    
    Args:
        request_data (Dict[str, Any]): Dictionary containing the form data
        
    Returns:
        bool: True if successful, False otherwise
    """
    return form_services.append_gsheet_unmasking_response(request_data)

def update_gsheet_unmasking_approval(request_id: str, approver_email: str, approval_status: str) -> bool:
    """
    Convenience function to update GSheet unmasking approval.
    
    Args:
        request_id (str): The request ID to update
        approver_email (str): The approver's email
        approval_status (str): The approval status
        
    Returns:
        bool: True if successful, False otherwise
    """
    return form_services.update_gsheet_unmasking_approval(request_id, approver_email, approval_status)

def get_masked_columns_mapping(user_entity: str) -> Dict[str, Dict[str, Dict[str, list]]]:
    """
    Convenience function to get masked columns mapping.
    
    Args:
        user_entity (str): The user's entity
        
    Returns:
        Dict[str, Dict[str, Dict[str, list]]]: Dictionary with database as key, schema as sub-key, table as sub-sub-key, and columns as list
    """
    return form_services.get_masked_columns_mapping(user_entity)

def get_masked_database_options(user_entity: str) -> list:
    """
    Convenience function to get masked database options.
    
    Args:
        user_entity (str): The user's entity
        
    Returns:
        list: List of distinct database names
    """
    return form_services.get_masked_database_options(user_entity)

def get_request_details(request_id: str) -> Dict[str, Any]:
    """
    Convenience function to get request details.
    
    Args:
        request_id (str): The request ID to search for
        
    Returns:
        Dict[str, Any]: Dictionary containing request details and authorization info
    """
    return form_services.get_request_details(request_id)

def is_user_authorized_for_request(request_id: str, user_email: str) -> Dict[str, Any]:
    """
    Convenience function to check if user is authorized for request.
    
    Args:
        request_id (str): The request ID to check
        user_email (str): The current user's email
        
    Returns:
        Dict[str, Any]: Dictionary containing authorization status and details
    """
    return form_services.is_user_authorized_for_request(request_id, user_email)

def update_user_creation_approval(request_id: str, approver_email: str, approval_status: str) -> bool:
    """
    Convenience function to update user creation approval.
    
    Args:
        request_id (str): The request ID to update
        approver_email (str): The approver's email
        approval_status (str): 'Approved' or 'Rejected'
        
    Returns:
        bool: True if successful, False otherwise
    """
    return form_services.update_user_creation_approval(request_id, approver_email, approval_status)

def update_table_column_approval(request_id: str, approver_email: str, approval_type: str, approval_status: str) -> bool:
    """
    Convenience function to update table/column approval.
    
    Args:
        request_id (str): The request ID to update
        approver_email (str): The approver's email
        approval_type (str): 'RM_APPROVER' or 'DATA_APPROVER'
        approval_status (str): 'Approved' or 'Rejected'
        
    Returns:
        bool: True if successful, False otherwise
    """
    return form_services.update_table_column_approval(request_id, approver_email, approval_type, approval_status)

def update_multi_approver_status(request_id: str, approver_email: str, approval_status: str) -> bool:
    """
    Convenience function to update multi-approver status.
    
    Args:
        request_id (str): The request ID to update
        approver_email (str): The approver's email
        approval_status (str): 'Approved' or 'Rejected'
        
    Returns:
        bool: True if successful, False otherwise
    """
    return form_services.update_multi_approver_status(request_id, approver_email, approval_status)

def send_user_creation_approval_email(request_id: str, approval_status: str, approver_email: str) -> bool:
    """
    Convenience function to send user creation approval email.
    
    Args:
        request_id (str): The request ID
        approval_status (str): 'Approved' or 'Rejected'
        approver_email (str): The approver's email
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    return form_services.send_user_creation_approval_email(request_id, approval_status, approver_email)

def send_table_column_approval_email(request_id: str, approval_type: str, approval_status: str, approver_email: str) -> bool:
    """
    Convenience function to send table/column approval email.
    
    Args:
        request_id (str): The request ID
        approval_type (str): 'RM_APPROVER' or 'DATA_APPROVER'
        approval_status (str): 'Approved' or 'Rejected'
        approver_email (str): The approver's email
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    return form_services.send_table_column_approval_email(request_id, approval_type, approval_status, approver_email)

def send_multi_approver_notification_email(request_id: str, approval_status: str, approver_email: str) -> bool:
    """
    Convenience function to send multi-approver notification email.
    
    Args:
        request_id (str): The request ID
        approval_status (str): 'Approved' or 'Rejected'
        approver_email (str): The approver's email
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    return form_services.send_multi_approver_notification_email(request_id, approval_status, approver_email)
