import streamlit as st
import sys
import os
from pathlib import Path
from login import verify_user, get_user_info

# Page configuration - set this before importing forms to avoid conflicts
st.set_page_config(
    page_title="Data Access Management System",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Add the current directory to Python path to import the form modules
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Import the form modules
form_modules = {}
try:
    import table
    form_modules['table'] = table
except Exception:
    form_modules['table'] = None

try:
    import unhashing
    form_modules['unhashing'] = unhashing
except Exception:
    form_modules['unhashing'] = None

try:
    import user_creation
    form_modules['user_creation'] = user_creation
except Exception:
    form_modules['user_creation'] = None

try:
    import user_dashboard
    form_modules['dashboard'] = user_dashboard
except Exception:
    form_modules['dashboard'] = None

try:
    import approver_dashboard
    form_modules['approver_dashboard'] = approver_dashboard
except Exception:
    form_modules['approver_dashboard'] = None

def show_form_error(form_name):
    """Display a simple error message for form loading issues"""
    st.error(f"{form_name} form is not available. Please check your configuration.")

def run_table_form():
    """Run the table form module"""
    if form_modules['table'] is None:
        show_form_error("Table Access Request")
        return
    
    try:
        form_modules['table'].main()
    except Exception:
        st.error("Table Access Request form is not available.")

def run_unhashing_form():
    """Run the unhashing form module"""
    if form_modules['unhashing'] is None:
        show_form_error("Column Unhashing Request")
        return
    
    try:
        form_modules['unhashing'].main()
    except Exception as e:
        st.error(f"Column Unhashing Request form error: {str(e)}")
        st.info("This might be due to Google Sheets connection issues or missing data.")

def run_user_creation_form():
    """Run the user creation form module"""
    if form_modules['user_creation'] is None:
        show_form_error("User Creation Request")
        return
    
    try:
        form_modules['user_creation'].main()
    except Exception as e:
        st.error(f"User Creation Request form error: {str(e)}")
        st.info("This might be due to Google Sheets connection issues or missing data.")

def run_dashboard():
    """Run the dashboard module"""
    if form_modules['dashboard'] is None:
        show_form_error("Dashboard")
        return
    
    try:
        form_modules['dashboard'].create_dashboard()
    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")
        st.info("This might be due to Google Sheets connection issues or missing data.")

def run_approver_dashboard():
    """Run the approver dashboard module"""
    if form_modules['approver_dashboard'] is None:
        show_form_error("Approver Dashboard")
        return
    
    try:
        form_modules['approver_dashboard'].create_approver_dashboard()
    except Exception as e:
        st.error(f"Approver Dashboard error: {str(e)}")
        st.info("This might be due to Google Sheets connection issues or missing data.")

def main():
    """Main application with integrated forms"""
    
    # Check authentication
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        # Show login form
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2c3e50;">🔐 Data Access Management System</h1>
            <p style="color: #7f8c8d; font-size: 18px;">Please login to continue</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Center the login form
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="Enter your email address")
                submit_button = st.form_submit_button("Login", type="primary")
                
                if submit_button:
                    if not email or not email.strip():
                        st.error("Please enter your email address")
                    elif not verify_user(email):
                        st.error("❌ Email not found. Please check your email address or contact your administrator.")
                    else:
                        # Store user info in session state
                        user_info = get_user_info(email)
                        st.session_state.authenticated = True
                        st.session_state.user_email = email.strip()
                        st.session_state.user_entity = user_info.get('entity', '')
                        st.session_state.user_role = user_info.get('role', '')
                        
                        st.success("✅ Login successful! Redirecting...")
                        st.rerun()
            
            # Add some styling
            st.markdown("""
            
            <style>
            .stForm {
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border: 1px solid #dee2e6;
            }
            </style>
            """, unsafe_allow_html=True)
        return
    
    # User is authenticated, show the main application
    st.markdown(f"""
    <div style="text-align: right; margin-bottom: 20px;">
        <p style="color: #7f8c8d; font-size: 14px;">
            Logged in as: <strong>{st.session_state.user_email}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if any modules are available
    if not any(form_modules.values()):
        st.error("No forms are available. Please check your configuration.")
        return
    
    # Check if user is an approver
    approver_roles = {'rm': False, 'data': False, 'manager': False}
    if form_modules['approver_dashboard']:
        try:
            approver_roles = form_modules['approver_dashboard'].get_user_approver_roles(st.session_state.user_email)
        except Exception:
            pass
    
    # Create tabs for different forms
    if any(approver_roles.values()):
        # User is an approver, show approver dashboard tab
        tab_names = [" Table Access Request", " Column Unhashing Request", " User Creation Request", " 📊 Dashboard", " 🔐 Approver Dashboard"]
        tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)
        
        with tab1:
            run_table_form()
        
        with tab2:
            run_unhashing_form()
        
        with tab3:
            run_user_creation_form()
        
        with tab4:
            run_dashboard()
        
        with tab5:
            run_approver_dashboard()
    else:
        # User is not an approver, show regular tabs
        tab_names = [" Table Access Request", " Column Unhashing Request", " User Creation Request", " 📊 Dashboard"]
        tab1, tab2, tab3, tab4 = st.tabs(tab_names)
        
        with tab1:
            run_table_form()
        
        with tab2:
            run_unhashing_form()
        
        with tab3:
            run_user_creation_form()
        
        with tab4:
            run_dashboard()

if __name__ == "__main__":
    main()
