import streamlit as st
from typing import Optional, Dict, Any
import sys
import os

# Add components directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'components'))

# Import component render functions
from table_access_request import render_table_access_request
from column_unhashing_request import render_column_unhashing_request
from user_creation_request import render_user_creation_request
from user_dashboard import render_user_dashboard
from approval_dashboard import render_approval_dashboard
from gsheet_unmasking_request import render_gsheet_unmasking_request

class ComponentContext:
    """
    Context management system for form components.
    Manages the selected component and provides rendering logic.
    """
    
    def __init__(self):
        self.components = {
            "Raise Requests": {
                "sub_components": {
                    "User Creation Request": "user_creation_request",
                    "Table Access Request": "table_access_request",
                    "Column Unhashing Request": "column_unhashing_request"
                },
                "icon": "📝",
                "description": "Submit various types of access requests"
            },
            "GSheet Unmasking Request": {
                "sub_components": {},
                "icon": "🔓",
                "description": "Unmask a named range in a Google Spreadsheet"
            },
            "User Dashboard": {
                "sub_components": {},
                "icon": "📊",
                "description": "View user information and statistics"
            },
            "Approval Dashboard": {
                "sub_components": {},
                "icon": "✅",
                "description": "Manage and approve pending requests"
            }
        }
    
    def get_selected_component(self, key: str = "nav_selector") -> Optional[str]:
        """Get the currently selected main component."""
        return st.session_state.get(f"{key}_selected")
    
    def get_selected_sub_component(self, key: str = "nav_selector") -> Optional[str]:
        """Get the currently selected sub-component (for Raise Requests)."""
        return st.session_state.get(f"{key}_request_type")
    
    def get_component_info(self, component_name: str) -> Dict[str, Any]:
        """Get information about a specific component."""
        return self.components.get(component_name, {})
    
    def is_component_selected(self, component_name: str, key: str = "nav_selector") -> bool:
        """Check if a specific component is selected."""
        return self.get_selected_component(key) == component_name
    
    def is_sub_component_selected(self, sub_component_name: str, key: str = "nav_selector") -> bool:
        """Check if a specific sub-component is selected."""
        return self.get_selected_sub_component(key) == sub_component_name
    
    def get_available_components(self) -> list:
        """Get list of all available main components."""
        return list(self.components.keys())
    
    def get_component_icons(self) -> list:
        """Get list of icons for all components."""
        return [self.components[comp]["icon"] for comp in self.components.keys()]
    
    def get_sub_components(self, component_name: str) -> list:
        """Get list of sub-components for a specific component."""
        return list(self.components.get(component_name, {}).get("sub_components", {}).keys())
    
    def get_component_description(self, component_name: str) -> str:
        """Get description for a specific component."""
        return self.components.get(component_name, {}).get("description", "")

# Global context instance
component_context = ComponentContext()

def get_context() -> ComponentContext:
    """Get the global component context instance."""
    return component_context

def render_component_content(selected_component: str, selected_sub_component: Optional[str] = None):
    """
    Render the appropriate content based on selected component and sub-component.
    This function will be called from the horizontal selector to display the correct form.
    """
    context = get_context()
    
    if selected_component == "Raise Requests":
        if selected_sub_component == "User Creation Request":
            return render_user_creation_request()
        elif selected_sub_component == "Table Access Request":
            return render_table_access_request()
        elif selected_sub_component == "Column Unhashing Request":
            return render_column_unhashing_request()
        else:
            return render_raise_requests_overview()
    
    elif selected_component == "User Dashboard":
        return render_user_dashboard()
    
    elif selected_component == "Approval Dashboard":
        return render_approval_dashboard()
    
    elif selected_component == "GSheet Unmasking Request":
        return render_gsheet_unmasking_request()
    
    else:
        return render_default_content()


def render_raise_requests_overview():
    """Render the overview for Raise Requests when no sub-component is selected."""
    st.subheader("📝 Raise Requests")
    st.info("Please select a request type from the options above.")
    st.write("Available request types:")
    st.write("- User Creation Request")
    st.write("- Table Access Request")
    st.write("- Column Unhashing Request")

def render_default_content():
    """Render default content when no component is selected."""
    st.subheader("🎯 Welcome")
    st.info("Please select a component from the navigation above.")
    st.write("Available components:")
    st.write("- Raise Requests (with sub-options)")
    st.write("- User Dashboard")
    st.write("- Approval Dashboard")
