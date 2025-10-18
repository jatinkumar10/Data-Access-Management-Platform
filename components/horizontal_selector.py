import streamlit as st
import sys
import os

# Add context directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'context'))

from component_context import get_context, render_component_content

def horizontal_selector_three_items(title="Select an option", options=None, icons=None, key="selector"):
    """
    A reusable component that displays a horizontal list of three selectable items in a single row.
    When "Raise Requests" is selected, shows three radio button options.
    Uses context system to render appropriate component content.
    
    Args:
        title (str): The title to display above the selector
        options (list): List of three options to display
        icons (list): List of three icons to display (optional)
        key (str): Unique key for the component
    
    Returns:
        str: The selected option
    """
    
    # Get context
    context = get_context()
    
    # Default options if none provided
    if options is None:
        options = context.get_available_components()
    
    # Default icons if none provided
    if icons is None:
        icons = context.get_component_icons()
    
    # Ensure we have at least one option
    if len(options) == 0:
        st.error("No components available for selection.")
        return None
    
    # Initialize default selection if not already set
    if f"{key}_selected" not in st.session_state:
        st.session_state[f"{key}_selected"] = "Raise Requests"
    
    # Initialize default sub-component selection for "Raise Requests"
    if f"{key}_request_type" not in st.session_state:
        st.session_state[f"{key}_request_type"] = "User Creation Request"
    
    # Custom CSS for the three-item horizontal selector - matching image design exactly
    st.markdown("""
    <style>
        /* Style Streamlit buttons to look like dark blue tabs */
        .stButton > button {
            background-color: #1e3a8a !important;
            border: none !important;
            border-radius: 4px !important;
            box-shadow: none !important;
            color: white !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 0.75rem 1.5rem !important;
            margin: 0 0.25rem !important;
            transition: all 0.3s ease !important;
            text-align: center !important;
            min-height: 45px !important;
            position: relative !important;
            user-select: none !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0.5rem !important;
        }
        
        /* Hover effect */
        .stButton > button:hover {
            background-color: #1e40af !important;
            color: white !important;
            transform: none !important;
            box-shadow: none !important;
        }
        
        /* Active state - slightly lighter blue */
        .stButton > button[data-selected="true"] {
            background-color: #3b82f6 !important;
            color: white !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }
        
        .stButton > button[data-selected="true"]:hover {
            background-color: #3b82f6 !important;
            color: white !important;
        }
        
        /* Container styling for tab appearance */
        [data-testid="column"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0.25rem !important;
        }
        
        .selector-title {
            text-align: center;
            color: #1f77b4;
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 0.25rem;
        }
        .dropdown-container {
            background-color: transparent;
            padding: 0.25rem 0;
            border-radius: 0;
            border: none;
            margin-top: 0.25rem;
        }
        .dropdown-title {
            color: #495057;
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 0.1rem;
        }
        .component-content {
            background-color: transparent;
            padding: 0.25rem 0;
            border-radius: 0;
            border: none;
            margin-top: 0.25rem;
        }
        /* Remove all borders and styling from form elements */
        .stForm {
            border: none !important;
            background: transparent !important;
        }
        .stForm > div {
            border: none !important;
            background: transparent !important;
        }
        /* Style form inputs to match image - theme aware */
        .stTextInput > div > div > input {
            background-color: var(--background-color, #f8f9fa) !important;
            border: 1px solid var(--border-color, #e9ecef) !important;
            border-radius: 4px !important;
            color: var(--text-color, #333) !important;
        }
        .stSelectbox > div > div > div {
            background-color: var(--background-color, #f8f9fa) !important;
            border: 1px solid var(--border-color, #e9ecef) !important;
            border-radius: 4px !important;
            color: var(--text-color, #333) !important;
        }
        .stSelectbox > div {
            background-color: transparent !important;
            border: none !important;
        }
        
        /* Dark theme variables */
        [data-theme="dark"] {
            --background-color: #0e1117;
            --text-color: #ffffff;
            --border-color: #4a5568;
        }
        
        [data-theme="light"] {
            --background-color: #f8f9fa;
            --text-color: #333;
            --border-color: #e9ecef;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Display title
    st.markdown(f'<div class="selector-title">{title}</div>', unsafe_allow_html=True)
    
    # Create dynamic columns for the options
    cols = st.columns(len(options))
    current_selection = st.session_state.get(f"{key}_selected", options[0])
    # Create buttons for each option
    for i, (col, opt, icon) in enumerate(zip(cols, options, icons)):
        with col:
            is_active = current_selection == opt
            if st.button(f"{icon} {opt}", key=f"{key}_btn_{i}", use_container_width=True):
                st.session_state[f"{key}_selected"] = opt
                st.rerun()
            # Add CSS to mark this button as active if it's selected
            if is_active:
                st.markdown(f"""
                <style>
                [data-testid="stButton"] button[kind="secondary"]:has-text('{icon} {opt}') {{
                    background-color: white !important;
                    color: #dc3545 !important;
                    font-weight: 600 !important;
                    border-bottom: 2px solid #dc3545 !important;
                }}
                </style>
                """, unsafe_allow_html=True)
    selected_option = st.session_state.get(f"{key}_selected", options[0])
    
    # Display current selection and render content
    if f"{key}_selected" in st.session_state:
        selected_component = st.session_state[f"{key}_selected"]
        
        # Show dropdown when "Raise Requests" is selected
        if selected_component == "Raise Requests":
            st.markdown('<div class="dropdown-container">', unsafe_allow_html=True)
            
            # Get sub-components from context
            sub_components = context.get_sub_components("Raise Requests")
            
            # Dropdown for request types
            request_type = st.selectbox(
                "Choose your request type:",
                sub_components,
                key=f"{key}_dropdown",
                index=0
            )
            
            if request_type:
                st.session_state[f"{key}_request_type"] = request_type
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Render component content based on selection
        st.markdown('<div class="component-content">', unsafe_allow_html=True)
        
        selected_sub_component = st.session_state.get(f"{key}_request_type")
        render_component_content(selected_component, selected_sub_component)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        return selected_component
    
    return selected_option
