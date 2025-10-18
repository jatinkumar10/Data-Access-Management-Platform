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
from context.filecontext import get_manager_email, get_entity_bu_mapping, get_entity_bu_options, append_user_response
from services.emailhandler import send_user_creation_notifications

def render_user_creation_request():
    """Render the User Creation Request form component."""
    
    # Initialize session state for submit button disable functionality
    if 'user_creation_submit_disabled' not in st.session_state:
        st.session_state.user_creation_submit_disabled = False
    if 'user_creation_submit_timer' not in st.session_state:
        st.session_state.user_creation_submit_timer = 0
    
    # Get user context and placeholders
    user_context = get_user_context()
    placeholders = get_form_placeholders()
    
    # Generate Request ID
    request_id = f"REQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{st.session_state.get('user_id', '5463')}"
    
    # Fetch manager email from the user_manager worksheet
    user_email = placeholders['email']
    try:
        manager_email_from_sheet = get_manager_email(user_email)
        if not manager_email_from_sheet:
            st.error("❌ **Manager Email not mapped!** Please contact your administrator to set up a manager for your account.")
            manager_email_from_sheet = None
    except Exception as e:
        st.error(f"❌ **Manager Email not mapped!** Could not fetch manager email from sheet: {str(e)}")
        manager_email_from_sheet = None
    
    # Generate user name from email (first part before @)
    user_name = user_email.split('@')[0] if '@' in user_email else user_email
    
    # Fetch Entity and BU options from the user_bu worksheet
    try:
        entity_bu_options = get_entity_bu_options()
        entity_options = entity_bu_options['entities']
        entity_bu_mapping = get_entity_bu_mapping()
        
        # Store mapping in session state for form use
        st.session_state['entity_bu_mapping'] = entity_bu_mapping
        
    except Exception as e:
        st.warning(f"⚠️ Could not fetch Entity/BU options from sheet: {str(e)}")
        entity_options = ["Select Entity", "Cars24", "Spinny", "CarDekho", "Droom", "CarTrade", "CarWale"]
        entity_bu_mapping = {}
        st.session_state['entity_bu_mapping'] = {}
    
    st.write("**User Creation Request**")
    
    # Single column layout - matching image exactly
    st.text_input("Request ID", value=request_id, disabled=True)
    st.text_input("Email ID", value=placeholders['email'], disabled=True)
    st.text_input("User Name", value=user_name, disabled=True)
    manager_email = st.text_input("Manager Email *", value=manager_email_from_sheet, disabled=True)
    
    # Entity and Business Unit selection
    entity = st.selectbox("Entity *", entity_options, key="entity_selector")
    
    # Get BU options based on selected entity
    entity_bu_mapping = st.session_state.get('entity_bu_mapping', {})
    if entity and entity != "Select Entity":
        bu_options = ["Select Business Unit"] + entity_bu_mapping.get(entity, [])
    else:
        bu_options = ["Select Business Unit"]
    
    business_unit = st.selectbox("Business Unit (BU) *", bu_options, key="bu_selector")
    
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
        # Submit button - disabled if manager email is not mapped or if submit is disabled
        if manager_email_from_sheet is None:
            st.error("🚫 **Cannot submit request:** Manager Email is not mapped for your account.")
            submitted = False
        elif st.session_state.user_creation_submit_disabled:
            # Show disabled button with countdown
            current_time = time.time()
            elapsed_time = current_time - st.session_state.user_creation_submit_timer
            remaining_time = max(0, 10 - int(elapsed_time))
            
            if remaining_time > 0:
                st.button(f"Submitting... Please wait {remaining_time}s", disabled=True, key="submit_button")
                # Auto-refresh to update countdown
                time.sleep(1)
                st.rerun()
            else:
                # Re-enable button after 10 seconds
                st.session_state.user_creation_submit_disabled = False
                st.session_state.user_creation_submit_timer = 0
                st.rerun()
        else:
            submitted = st.button("Submit", key="submit_button")
    
    with col2:
        # Show messages in the right column
        if submitted and manager_email_from_sheet is not None:
            # Create a placeholder for processing message
            processing_placeholder = st.empty()
            processing_placeholder.markdown('<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 15px; margin: 10px 0; color: #856404; font-weight: bold; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); animation: pulse 1.5s ease-in-out infinite alternate;">🔄 Processing your request... Please wait</div>', unsafe_allow_html=True)
            
            # Disable submit button and start timer
            st.session_state.user_creation_submit_disabled = True
            st.session_state.user_creation_submit_timer = time.time()
            
            # Validation
            required_fields = {
                "Manager Email": manager_email,
                "Entity": entity,
                "Business Unit (BU)": business_unit
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            
            if missing_fields:
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error(f"❌ Please fill in all required fields: {', '.join(missing_fields)}")
                # Re-enable button if validation fails
                st.session_state.user_creation_submit_disabled = False
                st.session_state.user_creation_submit_timer = 0
            elif entity == "Select Entity":
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Please select an entity")
                # Re-enable button if validation fails
                st.session_state.user_creation_submit_disabled = False
                st.session_state.user_creation_submit_timer = 0
            elif business_unit == "Select Business Unit":
                # Clear the processing placeholder
                processing_placeholder.empty()
                st.error("❌ Please select a business unit")
                # Re-enable button if validation fails
                st.session_state.user_creation_submit_disabled = False
                st.session_state.user_creation_submit_timer = 0
            else:
                # Prepare data for sheet submission
                request_data = {
                    "request_id": request_id,
                    "user_email": placeholders['email'],
                    "user_name": user_name,
                    "manager_email": manager_email,
                    "entity": entity,
                    "business_unit": business_unit
                }
                
                # Append to user_responses worksheet
                try:
                    success = append_user_response(request_data)
                    if success:
                        # Clear the processing placeholder
                        processing_placeholder.empty()
                        st.success("✅ User Creation Request submitted successfully!")
                        st.write(f"**Request ID:** {request_id}")
                        
                        # Send email notifications
                        try:
                            email_result = send_user_creation_notifications(request_data)
                            if email_result['success']:
                                st.success("📧 Email notifications sent to user and manager!")
                            else:
                                st.warning(f"⚠️ Request saved but email notifications failed: {email_result['message']}")
                        except Exception as email_error:
                            st.warning(f"⚠️ Request saved but email notifications failed: {str(email_error)}")
                    else:
                        # Clear the processing placeholder
                        processing_placeholder.empty()
                        st.error("❌ Request submitted but failed to save to database. Please try again.")
                        # Re-enable button if submission fails
                        st.session_state.user_creation_submit_disabled = False
                        st.session_state.user_creation_submit_timer = 0
                except Exception as e:
                    # Clear the processing placeholder
                    processing_placeholder.empty()
                    st.error(f"❌ Error saving request: {str(e)}")
                    # Re-enable button if submission fails
                    st.session_state.user_creation_submit_disabled = False
                    st.session_state.user_creation_submit_timer = 0
