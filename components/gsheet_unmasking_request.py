import streamlit as st
from datetime import datetime
import sys
import os
import time

# Add context and services directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'context'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

def render_gsheet_unmasking_request():
    """
    Render the GSheet Unmasking Request form component.
    Allows user to submit a request to unmask a named range in a Google Spreadsheet.
    """
    
    # Initialize session state for submit button disable functionality
    if 'gsheet_unmasking_submit_disabled' not in st.session_state:
        st.session_state.gsheet_unmasking_submit_disabled = False
    if 'gsheet_unmasking_submit_timer' not in st.session_state:
        st.session_state.gsheet_unmasking_submit_timer = 0
    
    # ============================================================================
    # HEADER AND REQUEST ID GENERATION
    # ============================================================================
    st.subheader("🔓 GSheet Unmasking Request")
    
    # Generate unique request ID
    request_id = f"REQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{st.session_state.get('user_id', '1219')}"
    st.text_input("Request ID", value=request_id, disabled=True, key="gsheet_request_id")

    # ============================================================================
    # USER INFORMATION SETUP
    # ============================================================================
    from user_context import get_user_context, get_form_placeholders
    from context.filecontext import get_user_entity_role
    
    # Get user context and placeholders
    user_context = get_user_context()
    placeholders = get_form_placeholders()
    user_email = placeholders['email']
    
    # Generate user name from email
    user_name = user_email.split('@')[0] if '@' in user_email else user_email
    
    # Fetch user's entity from the snf_user worksheet
    try:
        user_entity_role = get_user_entity_role(user_email)
        user_entity = user_entity_role.get('entity', '')
    except Exception as e:
        st.warning(f"⚠️ Could not fetch user entity from sheet: {str(e)}")
        user_entity = placeholders.get('entity', '')
    
    # Display user information fields
    st.text_input("Email ID", value=user_email, disabled=True)
    st.text_input("User Name *", value=user_name, disabled=True)
    entity = st.text_input("Entity *", value=user_entity, disabled=True)

    # ============================================================================
    # APPROVER VALIDATION (SHOW ERROR AT TOP IF NOT MAPPED)
    # ============================================================================
    l1_approver_email = None
    
    try:
        from sequential_approval_service_fixed import SequentialApprovalService
        
        approval_service = SequentialApprovalService()
        temp_request_data = {'user_email': user_email}
        approvers = approval_service.get_approvers_for_request(temp_request_data)
        l1_approver_email = approvers.get('L1')
        
        if not l1_approver_email:
            st.error("❌ **L1 Approver not mapped!** Please contact your administrator to set up an L1 approver for your account.")
            st.info("💡 **Tip:** Make sure your email address is correctly added to the 'rm_approvers' sheet in the Google Spreadsheet.")
            st.info(f"💡 **Your Email:** {user_email}")
            
    except Exception as e:
        st.error(f"❌ **L1 Approver not mapped!** Could not fetch L1 approver from sheet: {str(e)}")

    # ============================================================================
    # SPREADSHEET AND NAMED RANGE SELECTION
    # ============================================================================
    from context.filecontext import get_file_context
    
    # Get spreadsheet options from cache
    file_context = get_file_context()
    all_options = file_context.get_gsheet_unmasking_options()
    
    # Filter spreadsheet IDs (currently showing all, but can be filtered by user's snowflake account)
    filtered_spreadsheet_ids = list(all_options.keys())
    
    # Spreadsheet ID dropdown
    spreadsheet_options = ["Select Spreadsheet ID"] + filtered_spreadsheet_ids
    spreadsheet_id = st.selectbox("Select Spreadsheet ID *", options=spreadsheet_options, key="gsheet_spreadsheet_id")
    
    # Reset to None if default option is selected
    if spreadsheet_id == "Select Spreadsheet ID":
        spreadsheet_id = None

    # Named Range dropdown (depends on selected spreadsheet_id)
    named_range_options = all_options.get(spreadsheet_id, []) if spreadsheet_id else []
    if spreadsheet_id and named_range_options:
        named_range_options = ["Select Named Range"] + named_range_options
    else:
        named_range_options = ["Select Named Range"]
    
    named_range = st.selectbox("Select Named Range *", options=named_range_options, key="gsheet_named_range")
    
    # Reset to None if default option is selected
    if named_range == "Select Named Range":
        named_range = None

    # ============================================================================
    # ACCESS AND USE CASE INFORMATION
    # ============================================================================
    
    # WHO HAS ACCESS TO THIS SHEET?
    access_options = [
        "used within C24 team - mention team/person",
        "shared with external agents",
        "shared with 3rd party vendor",
        "others - mention in end user details"
    ]
    selected_access = st.multiselect("Who Has Access To This Sheet? *", access_options, key="gsheet_access")
    
    # Convert list to comma-separated string for storage
    if selected_access:
        selected_access_str = ", ".join(selected_access)
    else:
        selected_access_str = None

    # END_USER_DESCRIPTION field - always shown
    end_user_description = st.text_input("End User Details (min 15 chars) *", key="gsheet_end_user_desc")
    if end_user_description and len(end_user_description) < 15:
        st.warning("End User Details must be at least 15 characters.")

    # USE CASE
    use_case_options = [
        "Select Use Case",
        "operational use-case - feeding live ops trackers",
        "reporting & analysis",
        "data sharing for 3rd party",
        "data accessibility for internal teams like finance/hr",
        "data validation - manual tagging or corrections - e.g. marketing channel corrections etc",
        "other (mention in objective)"
    ]
    selected_use_case = st.selectbox("Use Case *", use_case_options, key="gsheet_use_case")
    
    # Reset to None if default option is selected
    if selected_use_case == "Select Use Case":
        selected_use_case = None

    # Validity (01-90 days)
    validity_days = st.number_input(
        "Validity (01-90 days) *",
        min_value=1,
        max_value=90,
        value=30,
        step=1,
        key="gsheet_validity"
    )

    # Remarks (mandatory, min 20 chars)
    remarks = st.text_area("Objective of the sheet/analysis (required, min 20 chars) *", key="gsheet_remarks")
    if remarks and len(remarks) < 20:
        st.warning("Objective must be at least 20 characters.")

    # ============================================================================
    # APPROVAL CHAIN DISPLAY
    # ============================================================================
    st.write("**Approval Chain:**")
    
    if user_email:
        try:
            temp_request_data = {'user_email': user_email}
            approvers = approval_service.get_approvers_for_request(temp_request_data)
            
            # Display approvers in a clean format
            for i, level in enumerate(['L1', 'L2', 'L3', 'L4', 'L5'], 1):
                approver_email = approvers.get(level, '')
                if approver_email:
                    st.text_input(f"L{i} Approver", value=approver_email, disabled=True)
                    
        except Exception as e:
            st.warning(f"⚠️ Could not fetch approval chain: {str(e)}")
            st.text_input("L1 Approver", value="Not configured", disabled=True)
    else:
        st.text_input("L1 Approver", value="Not configured", disabled=True)

    # ============================================================================
    # FORM VALIDATION
    # ============================================================================
    valid = True
    error_messages = []
    
    # Validate all required fields
    if not spreadsheet_id:
        valid = False
        error_messages.append("Please select a Spreadsheet ID")
    
    if not named_range:
        valid = False
        error_messages.append("Please select a Named Range")
    
    if not selected_access or len(selected_access) == 0:
        valid = False
        error_messages.append("Please select who has access to this sheet")
    
    if not end_user_description or len(end_user_description) < 15:
        valid = False
        error_messages.append("END_USER_DETAILS is required and must be at least 15 characters")
    
    if not selected_use_case:
        valid = False
        error_messages.append("Please select a Use Case")
    
    if not validity_days or validity_days < 1 or validity_days > 90:
        valid = False
        error_messages.append("Validity must be between 1 and 90 days")
    
    if not remarks or len(remarks) < 20:
        valid = False
        error_messages.append("Objective is required and must be at least 20 characters")

    # ============================================================================
    # FORM SUBMISSION
    # ============================================================================
    
    # Custom CSS for submit button styling and processing animation
    st.markdown("""
    <style>
    .stButton > button {
        background-color: #1e3a8a !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        transition: background-color 0.3s ease !important;
    }
    .stButton > button:hover {
        background-color: #1e40af !important;
        color: white !important;
    }
    @keyframes pulse {
        from { opacity: 0.8; }
        to { opacity: 1; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create horizontal layout for button and messages
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Submit button - disabled if L1 approver is not mapped or if submit is disabled
        if l1_approver_email is None:
            st.error("🚫 **Cannot submit request:** L1 Approver is not mapped for your account.")
            submitted = False
        elif st.session_state.gsheet_unmasking_submit_disabled:
            # Show disabled button with countdown
            current_time = time.time()
            elapsed_time = current_time - st.session_state.gsheet_unmasking_submit_timer
            remaining_time = max(0, 10 - int(elapsed_time))
            
            if remaining_time > 0:
                st.button(f"Submitting... Please wait {remaining_time}s", disabled=True, key="gsheet_submit_button")
                # Auto-refresh to update countdown
                time.sleep(1)
                st.rerun()
            else:
                # Re-enable button after 10 seconds
                st.session_state.gsheet_unmasking_submit_disabled = False
                st.session_state.gsheet_unmasking_submit_timer = 0
                st.rerun()
        else:
            submitted = st.button("Submit Request", key="gsheet_unmasking_submit")
    
    with col2:
        # Show messages in the right column
        if submitted and l1_approver_email is not None:
            # Create a placeholder for processing message
            processing_placeholder = st.empty()
            processing_placeholder.markdown('<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 15px; margin: 10px 0; color: #856404; font-weight: bold; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); animation: pulse 1.5s ease-in-out infinite alternate;">🔄 Processing your request... Please wait</div>', unsafe_allow_html=True)
            
            # Disable submit button and start timer
            st.session_state.gsheet_unmasking_submit_disabled = True
            st.session_state.gsheet_unmasking_submit_timer = time.time()
            
            # Validation
            if not valid:
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("Please fill all required fields with valid input.")
                for error in error_messages:
                    st.error(f"• {error}")
                # Re-enable button if validation fails
                st.session_state.gsheet_unmasking_submit_disabled = False
                st.session_state.gsheet_unmasking_submit_timer = 0
            else:
                # Clear the processing placeholder
                processing_placeholder.empty()
                # Show immediate success message for request submission
                st.success(f"✅ **Request submitted successfully!** Request ID: {request_id}")
                
                # Get approver information for storage
                approvers = {}
                try:
                    temp_request_data = {'user_email': user_email}
                    approvers = approval_service.get_approvers_for_request(temp_request_data)
                except Exception as e:
                    st.warning(f"Could not fetch approver information: {str(e)}")
                
                # Prepare request data for storage and email
                request_data = {
                    'request_id': request_id,
                    'user_name': user_name,
                    'user_email': user_email,
                    'entity': entity,
                    'default_role': user_entity_role.get('default_role', '') if 'user_entity_role' in locals() else '',
                    'spreadsheet_id': spreadsheet_id,
                    'named_range': named_range,
                    'who_has_access': selected_access_str,
                    'end_user_description': end_user_description,
                    'use_case': selected_use_case,
                    'validity_days': validity_days,
                    'remarks': remarks,
                    'l1_approver': approvers.get('L1', ''),
                    'l2_approver': approvers.get('L2', ''),
                    'l3_approver': approvers.get('L3', ''),
                    'l4_approver': approvers.get('L4', ''),
                    'l5_approver': approvers.get('L5', ''),
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Store response to Google Sheet
                try:
                    from context.filecontext import append_gsheet_unmasking_response
                    success = append_gsheet_unmasking_response(request_data)
                    
                    if success:
                        # Show email success message after storage
                        st.success("📧 **Email notification sent to L1 approver!**")
                    else:
                        st.error("❌ Failed to submit request. Please try again.")
                        # Re-enable button if submission fails
                        st.session_state.gsheet_unmasking_submit_disabled = False
                        st.session_state.gsheet_unmasking_submit_timer = 0
                        
                except Exception as e:
                    st.error(f"❌ Error submitting request: {str(e)}")
                    # Re-enable button if submission fails
                    st.session_state.gsheet_unmasking_submit_disabled = False
                    st.session_state.gsheet_unmasking_submit_timer = 0