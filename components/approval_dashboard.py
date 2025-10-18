import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
import time

# Add context directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'context'))

# Add services directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

from user_context import get_user_context, get_form_placeholders
from context.filecontext import (
    get_user_roles, is_approver, get_pending_requests_for_approver, get_distinct_databases,
    get_distinct_databases_from_pending_requests, update_user_creation_approval_dashboard, 
    update_table_column_approval_dashboard, bulk_approve_requests
)

def handle_approval_action(request_id: str, request_type: str, approval_type: str, action: str, user_email: str) -> bool:
    """
    Handle approval or rejection action with processing state management.
    
    Args:
        request_id (str): The request ID
        request_type (str): The request type (User Creation, Table request, etc.)
        approval_type (str): The approval type
        action (str): 'Approved' or 'Rejected'
        user_email (str): The approver's email
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Note: Processing state is already added by the button click handler
    
    try:
        success = False
        
        if request_type == 'User Creation':
            # Update user creation approval
            success = update_user_creation_approval_dashboard(request_id, user_email, action)
        elif request_type == 'GSheet Unmasking':
            # Update GSheet unmasking approval
            from context.filecontext import update_gsheet_unmasking_approval
            success = update_gsheet_unmasking_approval(request_id, user_email, action)
        else:
            # Update table/column approval (handles both single and multi-approver)
            success = update_table_column_approval_dashboard(request_id, user_email, approval_type, action)
        
        if success:
            # Store the success message for this specific request
            is_multi_approver = False  # This would need to be determined from request data
            if is_multi_approver:
                message = f"✅ Request {request_id} has been {action.upper()} successfully as both RM and Data Owner Approver!"
            else:
                # Map approval type for display
                display_approval_type = "Data Owner" if approval_type == "Data" else approval_type
                message = f"✅ Request {request_id} has been {action.upper()} successfully as {display_approval_type} Approver!"
            
            # Store in session state with request ID as key
            st.session_state[f'request_message_{request_id}'] = {
                'message': message,
                'type': 'approval' if action == 'Approved' else 'rejection',
                'timestamp': time.time()
            }
            
            # Clear all cached data to force immediate refresh
            clear_approval_cache(user_specific_only=False)
            
            return True
        else:
            return False
            
    finally:
        # Remove from processing state
        st.session_state.processing_requests.discard(request_id)

def clear_approval_cache(user_specific_only=True):
    """
    Clear cached data related to approval dashboard to force refresh.
    
    Args:
        user_specific_only (bool): If True, only clear data that affects the current user's view.
                                 If False, clear all cached approval data.
    """
    if user_specific_only:
        # Only clear the most critical cache that affects immediate UI state
        cache_keys_to_clear = [key for key in st.session_state.keys() if any([
            'get_pending_requests_for_approver' in key,  # This is the main data source
            'pending_requests' in key,  # Any direct pending requests cache
            'ApprovalDashboardServices' in key,  # Approval dashboard service cache
            'responses_data' in key,  # Responses data cache
            'snf_user_data' in key,  # User data cache
            'get_distinct_databases' in key,  # Database filter cache
            'get_distinct_databases_from_pending_requests' in key  # Pending requests database cache
        ])]
    else:
        # Clear all approval-related cache (for major updates)
        cache_keys_to_clear = [key for key in st.session_state.keys() if any([
            'get_pending_requests_for_approver' in key,
            key.startswith('ApprovalDashboardServices'),
            'responses_data' in key,
            'snf_user_data' in key,
            'pending_requests' in key,
            'get_distinct_databases' in key,
            'get_distinct_databases_from_pending_requests' in key
        ])]
    
    for key in cache_keys_to_clear:
        try:
            del st.session_state[key]
        except KeyError:
            pass  # Key already deleted

def render_approval_dashboard():
    """Render the Approval Dashboard component."""
    
    # Custom CSS for enhanced message styling and button text wrapping
    st.markdown("""
    <style>
    .approval-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #155724;
        font-weight: bold;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .rejection-message {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #721c24;
        font-weight: bold;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .info-message {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        color: #0c5460;
        font-weight: 500;
    }
    .processing-message {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #856404;
        font-weight: bold;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        animation: pulse 1.5s ease-in-out infinite alternate;
    }
    @keyframes pulse {
        from { opacity: 0.8; }
        to { opacity: 1; }
    }
    /* Ensure button text stays on one line */
    .stButton > button {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        min-width: 140px !important;
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Get user context and placeholders
    user_context = get_user_context()
    placeholders = get_form_placeholders()
    user_email = placeholders['email']
    
    # Check if user is an approver
    if not is_approver(user_email):
        st.warning("⚠️ Access Denied: You don't have approval permissions.")
        return
    
    # Clean up old request messages (older than 5 seconds)
    current_time = time.time()
    keys_to_remove = []
    for key in st.session_state.keys():
        if key.startswith('request_message_'):
            message_data = st.session_state[key]
            if current_time - message_data.get('timestamp', 0) > 5:
                keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del st.session_state[key]
    

    
    # Get user roles (needed for filtering logic but not displayed)
    user_roles = get_user_roles(user_email)
    
    # Get pending requests for this approver first
    try:
        pending_requests = get_pending_requests_for_approver(user_email)
    except Exception as e:
        st.error(f"Error fetching pending requests: {str(e)}")
        pending_requests = []
    
    # Filters section - in same line (no heading)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        type_filter = st.selectbox(
            "Filter by Type",
            ["All", "Table request", "Column request", "User Creation", "GSheet Unmasking"],
            key="approval_type_filter"
        )
    
    with col2:
        try:
            databases = ["All"] + get_distinct_databases_from_pending_requests(user_email)
            database_filter = st.selectbox(
                "Filter by Database",
                databases,
                key="approval_database_filter"
            )
        except Exception as e:
            st.error(f"Error loading databases: {str(e)}")
            database_filter = "All"
    
    with col3:
        # Get distinct requestors from pending requests
        try:
            distinct_requestors = ["All"] + sorted(list(set([req.get('Requestor', '') for req in pending_requests if req.get('Requestor', '')])))
            requestor_filter = st.selectbox(
                "Filter by Requestor",
                distinct_requestors,
                key="approval_requestor_filter"
            )
        except Exception as e:
            st.error(f"Error loading requestors: {str(e)}")
            requestor_filter = "All"
    
    with col4:
        search_request_id = st.text_input(
            "Search by Request ID",
            placeholder="Enter Request ID...",
            key="approval_search_request_id"
        )
    
    # Apply filters
    filtered_requests = pending_requests.copy()
    
    if type_filter != "All":
        filtered_requests = [req for req in filtered_requests if type_filter in req.get("Request Type", "")]
    
    if database_filter != "All":
        filtered_requests = [req for req in filtered_requests if database_filter == req.get("Database", "")]
    
    if requestor_filter != "All":
        filtered_requests = [req for req in filtered_requests if requestor_filter == req.get("Requestor", "")]
    
    if search_request_id:
        filtered_requests = [req for req in filtered_requests if search_request_id.lower() in req.get("Request ID", "").lower()]
    
    # Initialize selected requests in session state if not exists
    if 'selected_requests' not in st.session_state:
        st.session_state.selected_requests = set()
    
    # Initialize processing states for individual requests
    if 'processing_requests' not in st.session_state:
        st.session_state.processing_requests = set()
    
    # Initialize processing state for bulk actions
    if 'bulk_processing' not in st.session_state:
        st.session_state.bulk_processing = False
    
    # Calculate summary
    total = len(filtered_requests)
    
    # Summary and buttons section - using same 4-column layout as filters
    col_summary1, col_summary2, col_approve, col_reject = st.columns([2.4, 0.1, 1, 1])
    
    with col_summary1:
        # Summary section (spans first two columns)
        # Show simple pending count
        st.markdown(f'<div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: bold;">Pending: {total}</div>', unsafe_allow_html=True)
    
    with col_summary2:
        # Minimal space to reduce gap between summary and buttons
        st.write("")
    
    with col_approve:
        # Approve button - same size as filters
        if st.button(f"✅ Approve Selected ({len(st.session_state.selected_requests)})", type="primary", use_container_width=True, disabled=len(st.session_state.selected_requests)==0 or st.session_state.bulk_processing):
                if len(st.session_state.selected_requests) > 0:
                    # Create a placeholder for bulk processing message
                    bulk_processing_placeholder = st.empty()
                    bulk_processing_placeholder.markdown('<div class="processing-message">🔄 Processing bulk action... Please wait</div>', unsafe_allow_html=True)
                    
                    # Set bulk processing state
                    st.session_state.bulk_processing = True
                    
                    try:
                        # Get only selected requests
                        selected_requests_list = [req for req in filtered_requests if req.get("Request ID") in st.session_state.selected_requests]
                        
                        # Perform bulk approval on selected requests
                        results = bulk_approve_requests(selected_requests_list, user_email, "Approved")
                        
                        if results["successful"] > 0:
                            # Get the request IDs that were successfully approved
                            successful_request_ids = [req.get("Request ID") for req in selected_requests_list[:results["successful"]]]
                            request_ids_text = ", ".join(successful_request_ids)
                            
                            message = f"✅ **BULK APPROVAL COMPLETED!**\n\n**Successfully Approved Request IDs:** {request_ids_text}\n\n**Total:** {results['successful']} out of {results['total']} selected requests approved successfully!"
                            if results["failed"] > 0:
                                message += f"\n\n**Failed:** {results['failed']} requests"
                            
                            st.session_state.approval_action_message = message
                            st.session_state.approval_action_type = 'approval'
                            # Clear selections after successful approval
                            st.session_state.selected_requests = set()
                            
                            # Clear all cached data to force immediate refresh
                            clear_approval_cache(user_specific_only=False)
                            
                            st.rerun()  # Refresh the page to show updated data
                        else:
                            st.error(f"❌ **BULK APPROVAL FAILED!**")
                            st.error(f"❌ **Failed to approve any requests. {results['failed']} failures.**")
                            st.info("**Error details:**")
                            for error in results["errors"][:3]:  # Show first 3 errors
                                st.error(f"• {error}")
                    finally:
                        # Clear the bulk processing placeholder
                        bulk_processing_placeholder.empty()
                        # Clear bulk processing state
                        st.session_state.bulk_processing = False
                else:
                    st.warning("No requests selected to approve.")
        
    with col_reject:
        # Reject button - same size as filters
        if st.button(f"❌ Reject Selected ({len(st.session_state.selected_requests)})", type="secondary", use_container_width=True, disabled=len(st.session_state.selected_requests)==0 or st.session_state.bulk_processing):
                if len(st.session_state.selected_requests) > 0:
                    # Create a placeholder for bulk processing message
                    bulk_processing_placeholder = st.empty()
                    bulk_processing_placeholder.markdown('<div class="processing-message">🔄 Processing bulk action... Please wait</div>', unsafe_allow_html=True)
                    
                    # Set bulk processing state
                    st.session_state.bulk_processing = True
                    
                    try:
                        # Get only selected requests
                        selected_requests_list = [req for req in filtered_requests if req.get("Request ID") in st.session_state.selected_requests]
                        
                        # Perform bulk rejection on selected requests
                        results = bulk_approve_requests(selected_requests_list, user_email, "Rejected")
                        
                        if results["successful"] > 0:
                            # Get the request IDs that were successfully rejected
                            successful_request_ids = [req.get("Request ID") for req in selected_requests_list[:results["successful"]]]
                            request_ids_text = ", ".join(successful_request_ids)
                            
                            message = f"❌ **BULK REJECTION COMPLETED!**\n\n**Successfully Rejected Request IDs:** {request_ids_text}\n\n**Total:** {results['successful']} out of {results['total']} selected requests rejected successfully!"
                            if results["failed"] > 0:
                                message += f"\n\n**Failed:** {results['failed']} requests"
                            
                            st.session_state.approval_action_message = message
                            st.session_state.approval_action_type = 'rejection'
                            # Clear selections after successful rejection
                            st.session_state.selected_requests = set()
                            
                            # Clear all cached data to force immediate refresh
                            clear_approval_cache(user_specific_only=False)
                            
                            st.rerun()  # Refresh the page to show updated data
                        else:
                            st.error(f"❌ **BULK REJECTION FAILED!**")
                            st.error(f"❌ **Failed to reject any requests. {results['failed']} failures.**")
                            st.info("**Error details:**")
                            for error in results["errors"][:3]:  # Show first 3 errors
                                st.error(f"• {error}")
                    finally:
                        # Clear the bulk processing placeholder
                        bulk_processing_placeholder.empty()
                        # Clear bulk processing state
                        st.session_state.bulk_processing = False
                else:
                    st.warning("No requests selected to reject.")
    
    # Note: Bulk processing messages are now handled via placeholders in the button click handlers
    
    # Display bulk operation messages just after the buttons
    if 'approval_action_message' in st.session_state and st.session_state.approval_action_message:
        message = st.session_state.approval_action_message
        message_type = st.session_state.get('approval_action_type', 'info')
        
        if message_type == 'approval':
            st.markdown(f'<div class="approval-message">{message}</div>', unsafe_allow_html=True)
        elif message_type == 'rejection':
            st.markdown(f'<div class="rejection-message">{message}</div>', unsafe_allow_html=True)
        else:
            st.info(message)
        
        # Clear the bulk message after displaying
        st.session_state.approval_action_message = None
        st.session_state.approval_action_type = None
    
    # Select All checkbox with precise click area
    if filtered_requests:
        all_request_ids = {req.get('Request ID', '') for req in filtered_requests}
        all_selected = all_request_ids.issubset(st.session_state.selected_requests)
        
        # Use a unique key for select all to avoid conflicts
        select_all_key = f"select_all_{len(filtered_requests)}_{hash(tuple(sorted(all_request_ids)))}"
        
        # Create a more precise layout for the checkbox
        col_checkbox, col_space = st.columns([1, 3])
        
        with col_checkbox:
            if st.checkbox("Select All", value=all_selected, key=select_all_key):
                if not all_selected:
                    st.session_state.selected_requests.update(all_request_ids)
                    st.rerun()
            else:
                if all_selected:
                    st.session_state.selected_requests.clear()
                    st.rerun()
        
        with col_space:
            # Empty space to prevent accidental clicks
            st.write("")
    
    # Display filtered requests as cards with checkboxes
    if filtered_requests:
        for i, request in enumerate(filtered_requests):
            request_id = request.get('Request ID', '')
            is_selected = request_id in st.session_state.selected_requests
            
            # Create a card-like container for each request
            with st.container():
                st.markdown("---")
                
                # Request header with checkbox
                col_checkbox, col_header = st.columns([1, 20])
                
                with col_checkbox:
                    # Checkbox for selection with optimized logic
                    if st.checkbox("Select request", value=is_selected, key=f"checkbox_{request_id}", label_visibility="collapsed"):
                        if not is_selected:
                            st.session_state.selected_requests.add(request_id)
                            st.rerun()
                    else:
                        if is_selected:
                            st.session_state.selected_requests.remove(request_id)
                            st.rerun()
                
                with col_header:
                # Request header in one line
                    approval_type = request.get('Approval Type', '')
                    st.write(f"**{request_id} - {request.get('Request Type', '')}** | **request by** [{request.get('Requestor', '')}](mailto:{request.get('Requestor', '')})")
                
                # Display processing message if request is being processed
                if request_id in st.session_state.processing_requests:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="processing-message">🔄 Processing your request... Please wait</div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                
                # Display success message for this specific request if exists
                message_key = f'request_message_{request_id}'
                if message_key in st.session_state:
                    message_data = st.session_state[message_key]
                    current_time = time.time()
                    
                    # Show message if it's less than 5 seconds old
                    if current_time - message_data['timestamp'] < 5:
                        # Add some spacing before the message
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        if message_data['type'] == 'approval':
                            st.markdown(f'<div class="approval-message">{message_data["message"]}</div>', unsafe_allow_html=True)
                        elif message_data['type'] == 'rejection':
                            st.markdown(f'<div class="rejection-message">{message_data["message"]}</div>', unsafe_allow_html=True)
                        
                        # Add some spacing after the message
                        st.markdown("<br>", unsafe_allow_html=True)
                    else:
                        # Remove old message
                        del st.session_state[message_key]
                
                # Main content layout - Left side and Right side
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Left side - Common fields for all request types
                    bu_value = request.get('BU', '')
                    bu_display = bu_value if bu_value else 'N/A'
                    st.write(f"**BU:** {bu_display}")
                    st.write(f"**Entity:** {request.get('Entity', '')}")
                    
                    # Display approval status for sequential approval requests
                    if request.get('Approval Status'):
                        st.write(f"**Approval Status:** {request.get('Approval Status', '')}")
                    
                    if request.get('Reason Category'):
                        st.write(f"**Reason Category:** {request.get('Reason Category', '')}")
                    # Show "Objective" for table/column requests, "Reason" for others
                    if request.get('Request Type') in ['Table request', 'Column request'] and request.get('Objective'):
                        st.write(f"**Objective:** {request.get('Objective', '')}")
                    elif request.get('Reason'):
                        st.write(f"**Reason:** {request.get('Reason', '')}")
                    if request.get('Validity') and request.get('Validity') != 'N/A':
                        st.write(f"**Validity:** {request.get('Validity', '')} days")
                    # Created At on left side for all request types except User Creation
                    if request.get('Created At') and request.get('Request Type') != 'User Creation':
                        st.write(f"**Created At:** {request.get('Created At', '')}")
                
                with col2:
                    # Right side - Request-specific fields
                    if request.get('Requesting For'):
                        st.write(f"**Requesting For:** {request.get('Requesting For', '')}")
                    
                    # GSheet Unmasking specific fields
                    if request.get('Request Type') == 'GSheet Unmasking':
                        if request.get('Spreadsheet ID'):
                            st.write(f"**Spreadsheet ID:** {request.get('Spreadsheet ID', '')}")
                        if request.get('Named Range'):
                            st.write(f"**Named Range:** {request.get('Named Range', '')}")
                        if request.get('Who Has Access'):
                            st.write(f"**Who Has Access:** {request.get('Who Has Access', '')}")
                        if request.get('End User Description'):
                            st.write(f"**End User Description:** {request.get('End User Description', '')}")
                        if request.get('Use Case'):
                            st.write(f"**Use Case:** {request.get('Use Case', '')}")
                        if request.get('Objective'):
                            st.write(f"**Objective:** {request.get('Objective', '')}")
                    else:
                        # Regular database/table fields for other request types
                        if request.get('Database') and request.get('Database') != 'N/A':
                            st.write(f"**Database:** {request.get('Database', '')}")
                        if request.get('Schema') and request.get('Schema') != 'N/A':
                            st.write(f"**Schema:** {request.get('Schema', '')}")
                        if request.get('Table') and request.get('Table') != 'N/A':
                            st.write(f"**Table:** {request.get('Table', '')}")
                        if request.get('Request Type') == 'Column request' and request.get('Column') and request.get('Column') != 'N/A':
                            st.write(f"**Column:** {request.get('Column', '')}")
                    
                    # Created At on right side only for User Creation requests
                    if request.get('Created At') and request.get('Request Type') == 'User Creation':
                        st.write(f"**Created At:** {request.get('Created At', '')}")
                
                # Right-aligned approve/reject buttons - same size as bulk action buttons
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    # Empty space on the left
                    st.write("")
                
                with col2:
                    # Empty space
                    st.write("")
                
                with col3:
                    # Approve button - same size as bulk action buttons
                    is_processing = request_id in st.session_state.processing_requests
                    if st.button(f"✅ Approve", key=f"approve_{i}", use_container_width=True, disabled=is_processing):
                        request_id = request.get('Request ID', '')
                        request_type = request.get('Request Type', '')
                        approval_type = request.get('Approval Type', '')
                        
                        # Create a placeholder for processing message
                        processing_placeholder = st.empty()
                        processing_placeholder.markdown('<div class="processing-message">🔄 Processing your request... Please wait</div>', unsafe_allow_html=True)
                        
                        # Add to processing state
                        st.session_state.processing_requests.add(request_id)
                        
                        # Use the new processing function
                        success = handle_approval_action(request_id, request_type, approval_type, "Approved", user_email)
                        
                        # Clear the processing placeholder
                        processing_placeholder.empty()
                        
                        if success:
                            st.rerun()  # Refresh the page to show updated data
                        else:
                            st.error(f"❌ **Failed to approve request {request_id}**")
                            st.warning("Please check your permissions and try again.")
                
                with col4:
                    # Reject button - same size as bulk action buttons
                    is_processing = request_id in st.session_state.processing_requests
                    if st.button(f"❌ Reject", key=f"reject_{i}", use_container_width=True, disabled=is_processing):
                        request_id = request.get('Request ID', '')
                        request_type = request.get('Request Type', '')
                        approval_type = request.get('Approval Type', '')
                        
                        # Create a placeholder for processing message
                        processing_placeholder = st.empty()
                        processing_placeholder.markdown('<div class="processing-message">🔄 Processing your request... Please wait</div>', unsafe_allow_html=True)
                        
                        # Add to processing state
                        st.session_state.processing_requests.add(request_id)
                        
                        # Use the new processing function
                        success = handle_approval_action(request_id, request_type, approval_type, "Rejected", user_email)
                        
                        # Clear the processing placeholder
                        processing_placeholder.empty()
                        
                        if success:
                            st.rerun()  # Refresh the page to show updated data
                        else:
                            st.error(f"❌ **Failed to reject request {request_id}**")
                            st.warning("Please check your permissions and try again.")
                
                st.markdown("<br>", unsafe_allow_html=True)
    
    else:
        st.info("No pending requests found matching the selected filters.")
    
    # Add some spacing at the bottom
    st.markdown("<br><br>", unsafe_allow_html=True)
