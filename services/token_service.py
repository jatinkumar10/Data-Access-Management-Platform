import requests
import time
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import GOOGLE_SHEETS_CLIENT_ID, GOOGLE_SHEETS_CLIENT_SECRET, SHEETS_TOKEN_STORAGE

class TokenService:
    """
    Service to manage Google Sheets OAuth tokens, check expiration, and refresh expired tokens.
    This service is specifically for Google Sheets API access, separate from SSO authentication.
    """
    
    def __init__(self):
        self.client_id = GOOGLE_SHEETS_CLIENT_ID
        self.client_secret = GOOGLE_SHEETS_CLIENT_SECRET
        self.token_storage = SHEETS_TOKEN_STORAGE
        self.google_token_url = "https://oauth2.googleapis.com/token"
    
    def store_tokens(self, access_token: str, refresh_token: str, expires_in: int = 3600):
        """
        Store Google Sheets tokens in the configuration.
        
        Args:
            access_token (str): The access token from Google
            refresh_token (str): The refresh token from Google
            expires_in (int): Token expiration time in seconds (default 3600 = 1 hour)
        """
        global SHEETS_TOKEN_STORAGE
        
        # Calculate expiration timestamp (Unix timestamp)
        expires_at = time.time() + expires_in
        
        # Update token storage
        SHEETS_TOKEN_STORAGE.update({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "token_type": "Bearer"
        })
        
        # Update the config file with new tokens
        self._update_config_file(access_token, refresh_token, expires_at)
    
    def _update_config_file(self, access_token: str, refresh_token: str, expires_at: float):
        """
        Update the config.py file with new Google Sheets token values.
        
        Args:
            access_token (str): The new access token
            refresh_token (str): The refresh token
            expires_at (float): The expiration timestamp
        """
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
            
            # Read the current config file
            with open(config_path, 'r', encoding='utf-8') as file:
                config_content = file.read()
            
            # Update the SHEETS_TOKEN_STORAGE section
            import re
            
            # Pattern to match the SHEETS_TOKEN_STORAGE dictionary
            pattern = r'SHEETS_TOKEN_STORAGE\s*=\s*\{[^}]*\}'
            
            # Create new SHEETS_TOKEN_STORAGE content
            new_token_storage = f'''SHEETS_TOKEN_STORAGE = {{
    "refresh_token": "{refresh_token}",
    "access_token": "{access_token}",
    "expires_at": {int(expires_at)},
    "token_type": "Bearer"
}}'''
            
            # Replace the SHEETS_TOKEN_STORAGE section
            updated_content = re.sub(pattern, new_token_storage, config_content, flags=re.DOTALL)
            
            # Write the updated content back to the file
            with open(config_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
                
        except Exception as e:
            print(f"Warning: Could not update config file: {str(e)}")
    
    def is_token_expired(self) -> bool:
        """
        Check if the current Google Sheets access token is expired.
        
        Returns:
            bool: True if token is expired or doesn't exist, False otherwise
        """
        if not self.token_storage["access_token"] or not self.token_storage["expires_at"]:
            return True
        
        # Add 5 minute buffer to refresh token before it actually expires
        buffer_time = 300  # 5 minutes in seconds
        current_time = time.time()
        
        return current_time >= (self.token_storage["expires_at"] - buffer_time)
    
    def refresh_access_token(self) -> str:
        """
        Refresh the Google Sheets access token using the refresh token.
        
        Returns:
            str: The new valid access token
            
        Raises:
            Exception: If refresh token is missing or refresh fails
        """
        if not self.token_storage["refresh_token"]:
            raise Exception("No refresh token available for Google Sheets. Service needs to re-authenticate.")
        
        # Prepare the refresh request
        refresh_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.token_storage["refresh_token"],
            "grant_type": "refresh_token"
        }
        
        try:
            # Make the refresh request
            response = requests.post(self.google_token_url, data=refresh_data)
            response.raise_for_status()
            
            # Parse the response
            token_data = response.json()
            
            # Extract new access token and expiration
            new_access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            
            if not new_access_token:
                raise Exception("Failed to get new access token from Google for Sheets API")
            
            # Store the new token
            self.store_tokens(
                access_token=new_access_token,
                refresh_token=self.token_storage["refresh_token"],  # Keep the same refresh token
                expires_in=expires_in
            )
            
            return new_access_token
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to refresh Google Sheets access token: {str(e)}")
        except Exception as e:
            raise Exception(f"Error refreshing Google Sheets access token: {str(e)}")
    
    def get_valid_access_token(self) -> str:
        """
        Get a valid Google Sheets access token. If the current token is expired, try to refresh it.
        If refresh fails, return the current token anyway for sheet access.
        
        Returns:
            str: A valid access token (or current token if refresh fails)
            
        Raises:
            Exception: If no tokens are available at all
        """
        # Check if we have any tokens stored
        if not self.token_storage["access_token"] or self.token_storage["access_token"] == "None":
            raise Exception("No Google Sheets access token available. Service needs to authenticate first.")
        
        # Check if token is expired
        if self.is_token_expired():
            try:
                # Try to refresh the token
                return self.refresh_access_token()
            except Exception as e:
                print(f"Warning: Google Sheets token refresh failed: {str(e)}")
                print("Using current token for sheet access...")
                # Return the current token anyway - it might still work for some operations
                return self.token_storage["access_token"]
        
        # Return the current valid token
        return self.token_storage["access_token"]
    
    def clear_tokens(self):
        """
        Clear all stored Google Sheets tokens (useful for service reset).
        """
        global SHEETS_TOKEN_STORAGE
        
        SHEETS_TOKEN_STORAGE.update({
            "refresh_token": None,
            "access_token": None,
            "expires_at": None,
            "token_type": "Bearer"
        })
    
    def get_token_info(self) -> dict:
        """
        Get information about the current Google Sheets token status.
        
        Returns:
            dict: Token information including expiration status
        """
        if not self.token_storage["access_token"] or self.token_storage["access_token"] == "None":
            return {
                "has_token": False,
                "is_expired": True,
                "expires_at": None,
                "expires_at_unix": None,
                "time_until_expiry": None,
                "created_at": None,
                "created_at_unix": None
            }
        
        is_expired = self.is_token_expired()
        expires_at_unix = self.token_storage["expires_at"]
        
        if expires_at_unix:
            current_time = time.time()
            time_until_expiry = expires_at_unix - current_time
            
            # Format expiration time
            expires_at_formatted = datetime.fromtimestamp(expires_at_unix).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Calculate creation time (assuming 1 hour default expiry)
            created_at_unix = expires_at_unix - 3600  # Default 1 hour
            created_at_formatted = datetime.fromtimestamp(created_at_unix).strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            time_until_expiry = None
            expires_at_formatted = None
            expires_at_unix = None
            created_at_formatted = None
            created_at_unix = None
        
        return {
            "has_token": True,
            "is_expired": is_expired,
            "expires_at": expires_at_formatted,
            "expires_at_unix": expires_at_unix,
            "time_until_expiry": time_until_expiry,
            "created_at": created_at_formatted,
            "created_at_unix": created_at_unix,
            "token_type": self.token_storage["token_type"]
        }

# Global token service instance
token_service = TokenService()

def get_token_service() -> TokenService:
    """
    Get the global Google Sheets token service instance.
    
    Returns:
        TokenService: The global token service instance
    """
    return token_service
