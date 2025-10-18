import streamlit as st
import time
from typing import Dict, Any, List
from functools import wraps
import sys
import os

# Add services directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

from formservices import get_form_services
from userdashboardservices import get_user_dashboard_services
from approvaldashboardservices import get_approval_dashboard_services

class FileContext:

    def get_gsheet_unmasking_options(self) -> dict:
        """
        Get cached spreadsheet IDs and named ranges for unmasking requests (all users).
        Filtering for user should be done in the component, not here.
        """
        cache_key = self._get_cache_key("gsheet_unmasking_options", "all")
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        # Fetch fresh data from form services (no user filter)
        data = self.form_services.get_gsheet_unmasking_options()
        self._set_cache(cache_key, data)
        return data

    """
    Centralized caching system for all Google Sheets data.
    Provides cached data to all components with 2-minute TTL.
    """
    
    def __init__(self):
        self.form_services = get_form_services()
        self.user_dashboard_services = get_user_dashboard_services()
        self.approval_dashboard_services = get_approval_dashboard_services()
        self.cache_duration = 120  # 2 minutes in seconds
    
    def _get_cache_key(self, data_type: str, *args) -> str:
        """Generate a unique cache key for data type and arguments."""
        args_str = "_".join(str(arg) for arg in args)
        return f"filecontext_{data_type}_{args_str}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid (less than 2 minutes old)."""
        if cache_key not in st.session_state:
            return False
        
        cached_data = st.session_state[cache_key]
        if not isinstance(cached_data, dict) or 'timestamp' not in cached_data:
            return False
        
        return time.time() - cached_data['timestamp'] < self.cache_duration
    
    def _set_cache(self, cache_key: str, data: Any):
        """Store data in cache with current timestamp."""
        st.session_state[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def _get_cache(self, cache_key: str) -> Any:
        """Get data from cache if valid."""
        if self._is_cache_valid(cache_key):
            return st.session_state[cache_key]['data']
        return None
    
    # ==================== FORM SERVICES CACHE ====================
    
    def get_manager_email(self, user_email: str) -> str:
        """Get cached manager email for user."""
        cache_key = self._get_cache_key("manager_email", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_manager_email(user_email)
        self._set_cache(cache_key, data)
        return data
    
    def get_entity_bu_mapping(self) -> Dict[str, list]:
        """Get cached entity to BU mapping."""
        cache_key = self._get_cache_key("entity_bu_mapping")
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_entity_bu_mapping()
        self._set_cache(cache_key, data)
        return data
    
    def get_entity_bu_options(self) -> Dict[str, list]:
        """Get cached entity and BU options."""
        cache_key = self._get_cache_key("entity_bu_options")
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_entity_bu_options()
        self._set_cache(cache_key, data)
        return data
    
    def get_user_entity_role(self, user_email: str) -> Dict[str, str]:
        """Get cached user entity and role."""
        cache_key = self._get_cache_key("user_entity_role", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_user_entity_role(user_email)
        self._set_cache(cache_key, data)
        return data
    
    def get_database_schema_table_mapping(self) -> Dict[str, Dict[str, list]]:
        """Get cached database schema table mapping."""
        cache_key = self._get_cache_key("database_schema_table_mapping")
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_database_schema_table_mapping()
        self._set_cache(cache_key, data)
        return data
    
    def get_database_options(self) -> list:
        """Get cached database options."""
        cache_key = self._get_cache_key("database_options")
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_database_options()
        self._set_cache(cache_key, data)
        return data
    
    def get_generic_user_role_options(self, user_entity: str) -> Dict[str, list]:
        """Get cached generic user role options."""
        cache_key = self._get_cache_key("generic_user_role_options", user_entity)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_generic_user_role_options(user_entity)
        self._set_cache(cache_key, data)
        return data
    
    def get_rm_approver(self, user_email: str) -> str:
        """Get cached RM approver."""
        cache_key = self._get_cache_key("rm_approver", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_rm_approver(user_email)
        self._set_cache(cache_key, data)
        return data
    
    def get_data_approver(self, database: str, schema: str) -> str:
        """Get cached data approver."""
        cache_key = self._get_cache_key("data_approver", database, schema)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_data_approver(database, schema)
        self._set_cache(cache_key, data)
        return data
    
    def get_masked_columns_mapping(self, user_entity: str) -> Dict[str, Dict[str, Dict[str, list]]]:
        """Get cached masked columns mapping."""
        cache_key = self._get_cache_key("masked_columns_mapping", user_entity)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_masked_columns_mapping(user_entity)
        self._set_cache(cache_key, data)
        return data
    
    def get_masked_database_options(self, user_entity: str) -> list:
        """Get cached masked database options."""
        cache_key = self._get_cache_key("masked_database_options", user_entity)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_masked_database_options(user_entity)
        self._set_cache(cache_key, data)
        return data
    
    def get_bu_from_snf_user(self, user_email: str) -> str:
        """Get cached BU from snf_user worksheet."""
        cache_key = self._get_cache_key("bu_from_snf_user", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.approval_dashboard_services.get_bu_from_snf_user(user_email)
        self._set_cache(cache_key, data)
        return data
    
    def get_request_details(self, request_id: str) -> Dict[str, Any]:
        """Get cached request details."""
        cache_key = self._get_cache_key("request_details", request_id)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.get_request_details(request_id)
        self._set_cache(cache_key, data)
        return data
    
    def is_user_authorized_for_request(self, request_id: str, user_email: str) -> Dict[str, Any]:
        """Check if user is authorized for request (cached)."""
        cache_key = self._get_cache_key("user_authorization", request_id, user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.form_services.is_user_authorized_for_request(request_id, user_email)
        self._set_cache(cache_key, data)
        return data
    
    # ==================== USER DASHBOARD SERVICES CACHE ====================
    
    def get_user_requests(self, user_email: str) -> List[Dict[str, Any]]:
        """Get cached user requests."""
        cache_key = self._get_cache_key("user_requests", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.user_dashboard_services.get_user_requests(user_email)
        self._set_cache(cache_key, data)
        return data
    
    def get_request_summary(self, user_email: str) -> Dict[str, int]:
        """Get cached request summary."""
        cache_key = self._get_cache_key("request_summary", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.user_dashboard_services.get_request_summary(user_email)
        self._set_cache(cache_key, data)
        return data
    
    # ==================== APPROVAL DASHBOARD SERVICES CACHE ====================
    
    def get_user_roles(self, user_email: str) -> List[str]:
        """Get cached user roles."""
        cache_key = self._get_cache_key("user_roles", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.approval_dashboard_services.get_user_roles(user_email)
        self._set_cache(cache_key, data)
        return data
    
    def is_approver(self, user_email: str) -> bool:
        """Check if user is approver (cached)."""
        cache_key = self._get_cache_key("is_approver", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.approval_dashboard_services.is_approver(user_email)
        self._set_cache(cache_key, data)
        return data
    
    def get_pending_requests_for_approver(self, user_email: str) -> List[Dict[str, Any]]:
        """Get cached pending requests for approver."""
        cache_key = self._get_cache_key("pending_requests_for_approver", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.approval_dashboard_services.get_pending_requests_for_approver(user_email)
        self._set_cache(cache_key, data)
        return data
    
    def get_distinct_databases(self) -> List[str]:
        """Get cached distinct databases."""
        cache_key = self._get_cache_key("distinct_databases")
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.approval_dashboard_services.get_distinct_databases()
        self._set_cache(cache_key, data)
        return data
    
    def get_distinct_databases_from_pending_requests(self, user_email: str) -> List[str]:
        """Get cached distinct databases from pending requests for a specific approver."""
        cache_key = self._get_cache_key("distinct_databases_pending", user_email)
        cached_data = self._get_cache(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch fresh data
        data = self.approval_dashboard_services.get_distinct_databases_from_pending_requests(user_email)
        self._set_cache(cache_key, data)
        return data
    
    # ==================== CACHE MANAGEMENT ====================
    
    def clear_cache(self, data_type: str = None):
        """Clear specific cache or all cache."""
        if data_type:
            # Clear specific cache type
            keys_to_remove = [key for key in st.session_state.keys() if key.startswith(f"filecontext_{data_type}_")]
            for key in keys_to_remove:
                del st.session_state[key]
        else:
            # Clear all filecontext cache
            keys_to_remove = [key for key in st.session_state.keys() if key.startswith("filecontext_")]
            for key in keys_to_remove:
                del st.session_state[key]
    
    def refresh_cache(self, data_type: str = None):
        """Force refresh cache by clearing and refetching."""
        self.clear_cache(data_type)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about current cache status."""
        cache_info = {
            'total_cached_items': 0,
            'cache_duration_seconds': self.cache_duration,
            'cached_data_types': {}
        }
        
        for key in st.session_state.keys():
            if key.startswith("filecontext_"):
                cache_info['total_cached_items'] += 1
                
                if key in st.session_state:
                    cached_data = st.session_state[key]
                    if isinstance(cached_data, dict) and 'timestamp' in cached_data:
                        age_seconds = time.time() - cached_data['timestamp']
                        cache_info['cached_data_types'][key] = {
                            'age_seconds': age_seconds,
                            'is_valid': age_seconds < self.cache_duration
                        }
        
        return cache_info

# Global file context instance
_file_context = None

def get_file_context() -> FileContext:
    """Get the global file context instance."""
    global _file_context
    if _file_context is None:
        _file_context = FileContext()
    return _file_context

# ==================== CONVENIENCE FUNCTIONS ====================

# Form Services
def get_manager_email(user_email: str) -> str:
    return get_file_context().get_manager_email(user_email)

def get_entity_bu_mapping() -> Dict[str, list]:
    return get_file_context().get_entity_bu_mapping()

def get_entity_bu_options() -> Dict[str, list]:
    return get_file_context().get_entity_bu_options()

def get_user_entity_role(user_email: str) -> Dict[str, str]:
    return get_file_context().get_user_entity_role(user_email)

def get_database_schema_table_mapping() -> Dict[str, Dict[str, list]]:
    return get_file_context().get_database_schema_table_mapping()

def get_database_options() -> list:
    return get_file_context().get_database_options()

def get_generic_user_role_options(user_entity: str) -> Dict[str, list]:
    return get_file_context().get_generic_user_role_options(user_entity)

def get_rm_approver(user_email: str) -> str:
    return get_file_context().get_rm_approver(user_email)

def get_data_approver(database: str, schema: str) -> str:
    return get_file_context().get_data_approver(database, schema)

def get_masked_columns_mapping(user_entity: str) -> Dict[str, Dict[str, Dict[str, list]]]:
    return get_file_context().get_masked_columns_mapping(user_entity)

def get_masked_database_options(user_entity: str) -> list:
    return get_file_context().get_masked_database_options(user_entity)

def get_bu_from_snf_user(user_email: str) -> str:
    return get_file_context().get_bu_from_snf_user(user_email)

def get_gsheet_unmasking_options() -> dict:
    return get_file_context().get_gsheet_unmasking_options()

def get_request_details(request_id: str) -> Dict[str, Any]:
    return get_file_context().get_request_details(request_id)

def is_user_authorized_for_request(request_id: str, user_email: str) -> Dict[str, Any]:
    return get_file_context().is_user_authorized_for_request(request_id, user_email)

# Approval Update Functions (No caching needed for write operations)
def update_user_creation_approval_form(request_id: str, approver_email: str, approval_status: str) -> bool:
    return get_file_context().form_services.update_user_creation_approval(request_id, approver_email, approval_status)

def update_table_column_approval_form(request_id: str, approver_email: str, approval_type: str, approval_status: str) -> bool:
    return get_file_context().form_services.update_table_column_approval(request_id, approver_email, approval_type, approval_status)

def update_multi_approver_status_form(request_id: str, approver_email: str, approval_status: str) -> bool:
    return get_file_context().form_services.update_multi_approver_status(request_id, approver_email, approval_status)

# Email Notification Functions (No caching needed for write operations)
def send_user_creation_approval_email(request_id: str, approval_status: str, approver_email: str) -> bool:
    return get_file_context().form_services.send_user_creation_approval_email(request_id, approval_status, approver_email)

def send_table_column_approval_email(request_id: str, approval_type: str, approval_status: str, approver_email: str) -> bool:
    return get_file_context().form_services.send_table_column_approval_email(request_id, approval_type, approval_status, approver_email)

def send_multi_approver_notification_email(request_id: str, approval_status: str, approver_email: str) -> bool:
    return get_file_context().form_services.send_multi_approver_notification_email(request_id, approval_status, approver_email)

# Form Append Functions (No caching needed for write operations)
def append_user_response(request_data: Dict[str, str]) -> bool:
    return get_file_context().form_services.append_user_response(request_data)

def append_table_access_response(request_data: Dict[str, Any]) -> bool:
    return get_file_context().form_services.append_table_access_response(request_data)

def append_column_unhashing_response(request_data: Dict[str, Any]) -> bool:
    return get_file_context().form_services.append_column_unhashing_response(request_data)

def append_gsheet_unmasking_response(request_data: Dict[str, Any]) -> bool:
    return get_file_context().form_services.append_gsheet_unmasking_response(request_data)

def update_gsheet_unmasking_approval(request_id: str, approver_email: str, approval_status: str) -> bool:
    return get_file_context().form_services.update_gsheet_unmasking_approval(request_id, approver_email, approval_status)

# User Dashboard Services
def get_user_requests(user_email: str) -> List[Dict[str, Any]]:
    return get_file_context().get_user_requests(user_email)

def get_request_summary(user_email: str) -> Dict[str, int]:
    return get_file_context().get_request_summary(user_email)

# Approval Dashboard Services
def get_user_roles(user_email: str) -> List[str]:
    return get_file_context().get_user_roles(user_email)

def is_approver(user_email: str) -> bool:
    return get_file_context().is_approver(user_email)

def get_pending_requests_for_approver(user_email: str) -> List[Dict[str, Any]]:
    return get_file_context().get_pending_requests_for_approver(user_email)

def get_distinct_databases() -> List[str]:
    return get_file_context().get_distinct_databases()

def get_distinct_databases_from_pending_requests(user_email: str) -> List[str]:
    return get_file_context().get_distinct_databases_from_pending_requests(user_email)

# Approval Dashboard Write Functions (No caching needed for write operations)
def update_user_creation_approval_dashboard(request_id: str, approver_email: str, approval_status: str) -> bool:
    return get_file_context().approval_dashboard_services.update_user_creation_approval(request_id, approver_email, approval_status)

def update_table_column_approval_dashboard(request_id: str, approver_email: str, approval_type: str, approval_status: str) -> bool:
    print(f"DEBUG: update_table_column_approval_dashboard called - Request: {request_id}, Approver: {approver_email}, Type: {approval_type}, Status: {approval_status}")
    # The approval_dashboard_services.update_table_column_approval already handles sequential approval and emails
    # No need to call sequential service again to avoid duplicate emails
    success = get_file_context().approval_dashboard_services.update_table_column_approval(request_id, approver_email, approval_type, approval_status)
    if success:
        print(f"Table/column approval updated successfully for {request_id} by {approver_email}")
    return success

def bulk_approve_requests(requests: List[Dict[str, Any]], approver_email: str, approval_status: str) -> Dict[str, Any]:
    return get_file_context().approval_dashboard_services.bulk_approve_requests(requests, approver_email, approval_status)

# Cache Management
def clear_cache(data_type: str = None):
    get_file_context().clear_cache(data_type)

def refresh_cache(data_type: str = None):
    get_file_context().refresh_cache(data_type)

def get_cache_info() -> Dict[str, Any]:
    return get_file_context().get_cache_info()
