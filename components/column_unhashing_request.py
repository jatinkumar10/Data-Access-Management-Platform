import streamlit as st
from datetime import datetime
import sys
import os
import time

# Add context directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'context'))

# Add services directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

from user_context import get_user_context, get_form_placeholders
from context.filecontext import get_user_entity_role, get_rm_approver, get_masked_database_options, get_masked_columns_mapping, get_generic_user_role_options, append_column_unhashing_response, get_bu_from_snf_user
from services.emailhandler import send_column_unhashing_notifications

def render_column_unhashing_request():
    """Render the Column Unhashing Request form component."""
    
    # Initialize session state for submit button disable functionality
    if 'column_unhashing_submit_disabled' not in st.session_state:
        st.session_state.column_unhashing_submit_disabled = False
    if 'column_unhashing_submit_timer' not in st.session_state:
        st.session_state.column_unhashing_submit_timer = 0
    
    # Get user context and placeholders
    user_context = get_user_context()
    placeholders = get_form_placeholders()
    
    # Generate Request ID
    request_id = f"REQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{st.session_state.get('user_id', '7605')}"
    
    # Fetch user's entity and default role from the snf_user worksheet
    user_email = placeholders['email']
    try:
        user_entity_role = get_user_entity_role(user_email)
        user_entity = user_entity_role.get('entity', '')
        user_default_role = user_entity_role.get('default_role', '')
    except Exception as e:
        st.warning(f"⚠️ Could not fetch user entity/role from sheet: {str(e)}")
        user_entity = ''
        user_default_role = ''
    
    # Fetch user's BU from the snf_user worksheet
    try:
        user_bu = get_bu_from_snf_user(user_email)
    except Exception as e:
        st.warning(f"⚠️ Could not fetch user BU from sheet: {str(e)}")
        user_bu = ''
    
    # Fetch generic role options based on user's entity
    try:
        generic_options = get_generic_user_role_options(user_entity)
        generic_roles = generic_options.get('generic_roles', ["Select Generic Role"])
        
        # Store options in session state for form use
        st.session_state['generic_roles'] = generic_roles
        
    except Exception as e:
        st.warning(f"⚠️ Could not fetch generic role options from sheet: {str(e)}")
        generic_roles = ["Select Generic Role", "D2C_READ_ONLY", "USERADMIN", "TECH_READ_WRITE"]
        st.session_state['generic_roles'] = generic_roles
    
    # Check if L1 approver is available using sequential approval service
    try:
        # Import the sequential approval service
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))
        from sequential_approval_service_fixed import SequentialApprovalService
        
        approval_service = SequentialApprovalService()
        # Create temporary request data to check approvers
        temp_request_data = {
            'user_email': user_email
        }
        approvers = approval_service.get_approvers_for_request(temp_request_data)
        l1_approver_email = approvers.get('L1')
        
        if not l1_approver_email:
            st.error("❌ **L1 Approver not mapped!** Please contact your administrator to set up an L1 approver for your account.")
            st.info("💡 **Tip:** Make sure your email address is correctly added to the 'rm_approvers' sheet in the Google Spreadsheet.")
            st.info(f"💡 **Your Email:** {user_email}")
        
    except Exception as e:
        st.error(f"❌ **L1 Approver not mapped!** Could not fetch L1 approver from sheet: {str(e)}")
        l1_approver_email = None
    
    # Generate user name from email (first part before @)
    user_name = user_email.split('@')[0] if '@' in user_email else user_email
    
    # Fetch masked columns data from the masked_columns worksheet
    try:
        # If user_entity is empty, use a default entity for testing
        if not user_entity:
            user_entity = "CSPL"  # Default entity for testing
            st.warning("⚠️ User entity not found, using default entity: CSPL")
        
        database_options = get_masked_database_options(user_entity)
        masked_columns_mapping = get_masked_columns_mapping(user_entity)
        
        # Store mapping in session state for form use
        st.session_state['masked_columns_mapping'] = masked_columns_mapping
        
        # If no data found, provide sample data for testing
        if not masked_columns_mapping:
            st.warning("⚠️ No masked columns data found, using sample data")
            masked_columns_mapping = {
                "CAPL_GS_DB": {
                    "B2C_ADDON_SERVI": {
                        "INVENTORY": ["REGISTRATION_NO", "LATITUDE", "LONGITUDE", "PINCODE"],
                        "AMC_BOOKING": ["BOOKING_ADDRESS", "NAME", "MOBILE"]
                    },
                    "B2C_CATALOG_SERV": {
                        "PRODUCT_META": ["NAME", "DESCRIPTION"],
                        "WARRANTY_PLAN": ["NAME", "DURATION"]
                    }
                }
            }
            st.session_state['masked_columns_mapping'] = masked_columns_mapping
        
    except Exception as e:
        st.warning(f"⚠️ Could not fetch masked columns data from sheet: {str(e)}")
        database_options = ["Select Database", "CAPL_GS_DB", "CFSPL_AUTOIQ_DB"]
        masked_columns_mapping = {
            "CAPL_GS_DB": {
                "B2C_ADDON_SERVI": {
                    "INVENTORY": ["REGISTRATION_NO", "LATITUDE", "LONGITUDE", "PINCODE"],
                    "AMC_BOOKING": ["BOOKING_ADDRESS", "NAME", "MOBILE"]
                }
            }
        }
        st.session_state['masked_columns_mapping'] = masked_columns_mapping
    
    st.write("**Column Unhashing Request**")
    
    # Single column layout - matching image exactly
    st.text_input("Request ID", value=request_id, disabled=True)
    st.text_input("Email ID", value=placeholders['email'], disabled=True)
    st.text_input("User Name *", value=user_name, disabled=True)
    entity = st.text_input("Entity *", value=user_entity if user_entity else placeholders['entity'], disabled=True)
    
    # Database, Schema, Table, and Column selection
    database = st.selectbox("Database *", database_options, key="unhashing_database_selector")
    
    # Get schema options based on selected database
    masked_columns_mapping = st.session_state.get('masked_columns_mapping', {})
    
    if database and database != "Select Database":
        schema_options = ["Select Schema"] + list(masked_columns_mapping.get(database, {}).keys())
    else:
        schema_options = ["Select Schema"]
    
    schema = st.selectbox("Schema *", schema_options, key="unhashing_schema_selector")
    
    # Get table options based on selected database and schema
    if database and database != "Select Database" and schema and schema != "Select Schema":
        table_options = ["Select Table"] + list(masked_columns_mapping.get(database, {}).get(schema, {}).keys())
    else:
        table_options = ["Select Table"]
    
    table = st.selectbox("Table *", table_options, key="unhashing_table_selector")
    
    # Column Selection radio buttons
    column_selection = st.radio(
        "Column Selection:",
        ["Select Columns", "All Columns"],
        horizontal=True,
        key="column_selection"
    )
    
    # Column dropdown (show for both options)
    if column_selection == "Select Columns":
        # Get column options based on selected database, schema, and table
        if database and database != "Select Database" and schema and schema != "Select Schema" and table and table != "Select Table":
            column_options = masked_columns_mapping.get(database, {}).get(schema, {}).get(table, [])
        else:
            column_options = []
        
        columns = st.multiselect(
            "Select Column(s):",
            column_options,
            placeholder="Select columns to unhash..."
        )
    else:
        # Show all actual columns when "All Columns" is selected
        if database and database != "Select Database" and schema and schema != "Select Schema" and table and table != "Select Table":
            all_column_options = masked_columns_mapping.get(database, {}).get(schema, {}).get(table, [])
        else:
            all_column_options = []
        
        columns = st.multiselect(
            "Select Column(s):",
            all_column_options,
            default=all_column_options,  # Pre-select all columns
            placeholder="All columns selected"
        )
    
    # Requesting For section
    requesting_for = st.radio(
        "Requesting For:",
        ["Self", "Generic Role"],
        horizontal=True,
        key="unhashing_requesting_for"
    )
        
    # Additional requesting for field based on selection
    if requesting_for == "Self":
        requesting_for_value = placeholders['email']  # Show user's email
        st.text_input("Requesting For", value=requesting_for_value, disabled=True)
    elif requesting_for == "Generic Role":
        generic_roles = st.session_state.get('generic_roles', ["Select Generic Role"])
        requesting_for_value = st.selectbox("Select Generic Role", generic_roles, key="unhashing_generic_role_selector")
    else:
        requesting_for_value = ""
    
    # Validity section - disable when Generic Role is selected
    if requesting_for == "Generic Role":
        validity_days = st.number_input(
            "Validity (01-90 days) - Not applicable for Generic Role",
            min_value=1,
            max_value=90,
            value=30,
            step=1,
            disabled=True
        )
        # Set validity to empty for Generic Role requests
        validity_days = ""
    else:
        validity_days = st.number_input(
            "Validity (01-90 days)",
            min_value=1,
            max_value=90,
            value=30,
            step=1
        )
        
    # Reason Category dropdown
    reason_category = st.selectbox(
        "Reason Category *",
        [
            "Select Reason Category",
            "operational use-case - feeding live ops trackers",
            "reporting & analysis",
            "data sharing for 3rd party",
            "data accessibility for internal teams like Finance/HR",
            "data validation - manual tagging or corrections - e.g. marketing channel corrections etc"
        ],
        key="unhashing_reason_category_selector"
    )
    
    # Objective of your analysis that requires unhashed data access
    reason = st.text_area(
        "Objective of your analysis that requires unhashed data access *",
        height=120,
        max_chars=500,
        placeholder=f"Please provide a detailed objective for this column unhashing request (minimum 30 characters)..."
    )
    
    # Approver chain display section
    st.write("**Approval Chain:**")
    
    # Get and display the approval chain
    if user_email:
        try:
            temp_request_data = {
                'user_email': user_email
            }
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
        elif st.session_state.column_unhashing_submit_disabled:
            # Show disabled button with countdown
            current_time = time.time()
            elapsed_time = current_time - st.session_state.column_unhashing_submit_timer
            remaining_time = max(0, 10 - int(elapsed_time))
            
            if remaining_time > 0:
                st.button(f"Submitting... Please wait {remaining_time}s", disabled=True, key="submit_button")
                # Auto-refresh to update countdown
                time.sleep(1)
                st.rerun()
            else:
                # Re-enable button after 10 seconds
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
                st.rerun()
        else:
            submitted = st.button("Submit Request")
    
    with col2:
        # Show messages in the right column
        if submitted and l1_approver_email is not None:
            # Create a placeholder for processing message
            processing_placeholder = st.empty()
            processing_placeholder.markdown('<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 15px; margin: 10px 0; color: #856404; font-weight: bold; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); animation: pulse 1.5s ease-in-out infinite alternate;">🔄 Processing your request... Please wait</div>', unsafe_allow_html=True)
            
            # Disable submit button and start timer
            st.session_state.column_unhashing_submit_disabled = True
            st.session_state.column_unhashing_submit_timer = time.time()
            
            # Validation
            required_fields = {
                "Entity": entity,
                "Database": database,
                "Schema": schema,
                "Table": table,
                "Reason Category": reason_category,
                "Objective of your analysis that requires unhashed data access": reason
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            
            if missing_fields:
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error(f"❌ Please fill in all required fields: {', '.join(missing_fields)}")
                # Re-enable button if validation fails
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
            elif database == "Select Database":
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Please select a database")
                # Re-enable button if validation fails
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
            elif schema == "Select Schema":
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Please select a schema")
                # Re-enable button if validation fails
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
            elif table == "Select Table":
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Please select a table")
                # Re-enable button if validation fails
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
            elif column_selection == "Select Columns" and not columns:
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Please select at least one column")
                # Re-enable button if validation fails
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
            elif reason_category == "Select Reason Category":
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Please select a reason category")
                # Re-enable button if validation fails
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
            elif requesting_for == "Generic Role" and (not requesting_for_value or requesting_for_value == "Select Generic Role"):
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Please select a generic role when requesting for Generic Role")
                # Re-enable button if validation fails
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
            elif len(reason.strip()) < 30:
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Objective of your analysis that requires unhashed data access must be at least 30 characters long")
                # Re-enable button if validation fails
                st.session_state.column_unhashing_submit_disabled = False
                st.session_state.column_unhashing_submit_timer = 0
            else:
                # Prepare request data for submission
                request_data = {
                    "request_id": request_id,
                    "user_name": user_name,
                    "user_email": placeholders['email'],
                    "entity": entity,
                    "business_unit": user_bu,  # Add BU from snf_user
                    "default_role": user_default_role,
                    "database": database,
                    "schema": schema,
                    "column_selection": column_selection,
                    "table": table,
                    "columns": columns,
                    "requesting_for_type": requesting_for,
                    "requesting_for_value": requesting_for_value,
                    "validity_days": validity_days,
                    "reason_category": reason_category,
                    "reason": reason
                }
                
                # Submit to responses worksheet
                try:
                    success = append_column_unhashing_response(request_data)
                    if success:
                        # Clear the processing placeholder
                        processing_placeholder.empty()
                        # Show success message immediately
                        st.success("✅ Column Unhashing Request submitted successfully!")
                        st.write(f"**Request ID:** {request_id}")
                        st.success("📧 Email notification sent to L1 approver!")
                        
                        # Send email notification in background (don't wait for it)
                        try:
                            from sequential_approval_service_fixed import SequentialApprovalService
                            approval_service = SequentialApprovalService()
                            approval_service.send_initial_approval_request(request_data)
                        except Exception as email_error:
                            # Don't show email errors to user since request was already submitted successfully
                            print(f"Email notification failed: {str(email_error)}")
                    else:
                        # Clear the processing placeholder
                        processing_placeholder.empty()
                        st.error("❌ Failed to submit request. Please try again.")
                        # Re-enable button if submission fails
                        st.session_state.column_unhashing_submit_disabled = False
                        st.session_state.column_unhashing_submit_timer = 0
                except Exception as e:
                    # Clear the processing placeholder
                    processing_placeholder.empty()
                    st.error(f"❌ Error submitting request: {str(e)}")
                    # Re-enable button if submission fails
                    st.session_state.column_unhashing_submit_disabled = False
                    st.session_state.column_unhashing_submit_timer = 0
