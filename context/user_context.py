import streamlit as st
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

class UserContext:
    """Context class to manage user information and provide it to forms using session state and file storage."""
    
    def __init__(self):
        self.storage_file = "user_data.json"
        self.user_info = None
        self.oauth_response = None
        self.authenticated = False
        self.current_user = None
        self.load_from_storage()
    
    def save_to_storage(self):
        """Save user data to persistent storage."""
        data = {
            'user_info': self.user_info,
            'oauth_response': self.oauth_response,
            'authenticated': self.authenticated,
            'current_user': self.current_user,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            # Save to file for cross-session persistence
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Save to Streamlit session state with persistence
            st.session_state['user_data'] = data
            st.session_state['user_authenticated'] = self.authenticated
            st.session_state['user_email'] = self.current_user
            
            print(f"💾 User data saved to persistent storage: {self.storage_file}")
            print(f"💾 User data also saved to Streamlit session state")
        except Exception as e:
            print(f"❌ Error saving to persistent storage: {e}")
    
    def load_from_storage(self):
        """Load user data from persistent storage."""
        try:
            # First try to load from Streamlit session state (survives refreshes)
            if 'user_data' in st.session_state:
                data = st.session_state['user_data']
                self.user_info = data.get('user_info')
                self.oauth_response = data.get('oauth_response')
                self.authenticated = data.get('authenticated', False)
                self.current_user = data.get('current_user')
                print(f"📂 User data loaded from Streamlit session state")
                if self.authenticated and self.user_info:
                    print(f"   👤 Loaded user: {self.user_info.get('name', 'N/A')} ({self.user_info.get('email', 'N/A')})")
                return
            
            # Second try loading from file (survives restarts)
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                
                self.user_info = data.get('user_info')
                self.oauth_response = data.get('oauth_response')
                self.authenticated = data.get('authenticated', False)
                self.current_user = data.get('current_user')
                
                # Also save to session state for future refreshes
                st.session_state['user_data'] = data
                st.session_state['user_authenticated'] = self.authenticated
                st.session_state['user_email'] = self.current_user
                
                print(f"📂 User data loaded from file storage: {self.storage_file}")
                if self.authenticated and self.user_info:
                    print(f"   👤 Loaded user: {self.user_info.get('name', 'N/A')} ({self.user_info.get('email', 'N/A')})")
            else:
                print("📂 No existing user data found in persistent storage")
        except Exception as e:
            print(f"❌ Error loading from persistent storage: {e}")
    
    def clear_storage(self):
        """Clear persistent storage."""
        try:
            # Clear file storage
            if os.path.exists(self.storage_file):
                os.remove(self.storage_file)
                print(f"🗑️ File storage cleared: {self.storage_file}")
            
            # Clear session state
            if 'user_data' in st.session_state:
                del st.session_state['user_data']
            if 'user_authenticated' in st.session_state:
                del st.session_state['user_authenticated']
            if 'user_email' in st.session_state:
                del st.session_state['user_email']
            print(f"🗑️ Session state cleared")
        except Exception as e:
            print(f"❌ Error clearing persistent storage: {e}")
    
    def set_user_info(self, user_info: Dict[str, Any], oauth_response: Optional[Dict[str, Any]] = None):
        """Set user information from OAuth response and save to persistent storage."""
        self.user_info = user_info
        self.oauth_response = oauth_response
        self.authenticated = True
        self.current_user = user_info.get('email', '')
        
        # Save to persistent storage
        self.save_to_storage()
        
        # Print update information
        print(f"🔄 User Context Updated:")
        print(f"   👤 User: {user_info.get('name', 'N/A')} ({user_info.get('email', 'N/A')})")
        print(f"   🏢 Domain: {user_info.get('hd', 'N/A')}")
        print(f"   ✅ Verified: {user_info.get('verified_email', 'N/A')}")
        print(f"   🔐 Authenticated: {self.authenticated}")
        print(f"   💾 Saved to persistent storage")
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information."""
        return self.user_info
    
    def get_user_email(self) -> str:
        """Get user email address."""
        if self.user_info:
            return self.user_info.get('email', '')
        return self.current_user or ''
    
    def get_user_name(self) -> str:
        """Get user full name."""
        if self.user_info:
            return self.user_info.get('name', '')
        return ''
    
    def get_user_domain(self) -> str:
        """Get user domain."""
        if self.user_info:
            return self.user_info.get('hd', '') or self.user_info.get('email', '').split('@')[1] if '@' in self.user_info.get('email', '') else ''
        return ''
    
    def get_user_picture(self) -> str:
        """Get user profile picture URL."""
        if self.user_info:
            return self.user_info.get('picture', '')
        return ''
    
    def is_verified_email(self) -> bool:
        """Check if user email is verified."""
        if self.user_info:
            return self.user_info.get('verified_email', False)
        return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.authenticated
    
    def get_oauth_response(self) -> Optional[Dict[str, Any]]:
        """Get OAuth response data."""
        return self.oauth_response
    
    def clear_user_info(self):
        """Clear user information (logout) and remove from persistent storage."""
        self.user_info = None
        self.oauth_response = None
        self.authenticated = False
        self.current_user = None
        
        # Clear persistent storage
        self.clear_storage()
        
        # Print logout information
        print("🚪 User Context Cleared - User Logged Out")
        print("🗑️ Persistent storage cleared")
    
    def get_form_placeholders(self) -> Dict[str, str]:
        """Get placeholders for form fields based on user information."""
        return {
            'email': self.get_user_email(),
            'name': self.get_user_name(),
            'domain': self.get_user_domain(),
            'entity': self.get_user_domain().upper() if self.get_user_domain() else '',
            'manager_email': self.get_user_email(),  # Default to current user
            'requesting_for': self.get_user_email(),
            'rm_approver': f"{self.get_user_name()} <{self.get_user_email()}>" if self.get_user_name() else self.get_user_email(),
            'data_approver': "himanshu1.rathore@cars24.com"  # Default data approver
        }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the persistent storage."""
        return {
            'storage_file': self.storage_file,
            'file_exists': os.path.exists(self.storage_file),
            'file_size': os.path.getsize(self.storage_file) if os.path.exists(self.storage_file) else 0,
            'session_state_has_data': 'user_data' in st.session_state,
            'last_updated': self.get_last_updated()
        }
    
    def get_last_updated(self) -> str:
        """Get the last update timestamp from storage."""
        try:
            if 'user_data' in st.session_state:
                return st.session_state['user_data'].get('last_updated', 'N/A')
            elif os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                return data.get('last_updated', 'N/A')
        except:
            pass
        return 'N/A'

# Streamlit cache for cross-session persistence
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cached_user_data():
    """Get cached user data that persists across sessions."""
    return {}

def get_user_context() -> UserContext:
    """Get the global user context instance with persistent storage."""
    if 'user_context' not in st.session_state:
        st.session_state.user_context = UserContext()
    
    return st.session_state.user_context

def update_user_context_from_session():
    """Update user context from session state (for backward compatibility)."""
    context = get_user_context()
    
    # Only update if session state has data and context doesn't
    if st.session_state.get('authenticated', False) and not context.is_authenticated():
        user_info = st.session_state.get('user_info')
        oauth_response = st.session_state.get('oauth_response')
        if user_info:
            context.set_user_info(user_info, oauth_response)

def get_form_placeholders() -> Dict[str, str]:
    """Get placeholders for form fields."""
    context = get_user_context()
    return context.get_form_placeholders()

def clear_persistent_storage():
    """Clear all persistent storage data."""
    context = get_user_context()
    context.clear_storage()
    print("🗑️ All persistent storage data cleared")

def get_storage_status() -> Dict[str, Any]:
    """Get the status of persistent storage."""
    context = get_user_context()
    return context.get_storage_info()

# Alternative persistence methods for different use cases
def save_to_streamlit_secrets():
    """Save user data to Streamlit secrets (for production)."""
    # This would require setting up secrets.toml
    pass

def save_to_database():
    """Save user data to database (for production)."""
    # This would require database connection
    pass
