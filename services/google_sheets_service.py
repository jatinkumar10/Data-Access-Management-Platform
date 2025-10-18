import requests
import pandas as pd
from typing import Tuple, Dict, Optional
import json
from datetime import datetime, timedelta
import os
import sys

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import get_sheets_config, SHEETS_TOKEN_STORAGE, SPREADSHEET_ID

class GoogleSheetsService:
    """
    Service for interacting with Google Sheets API using separate OAuth credentials.
    This service handles authentication and data retrieval for Google Sheets.
    Completely separate from SSO authentication.
    """
    
    def __init__(self):
        self.config = get_sheets_config()
        self.base_url = "https://sheets.googleapis.com/v4/spreadsheets"
        self.token_storage = SHEETS_TOKEN_STORAGE.copy()
        
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests with current access token"""
        return {
            "Authorization": f"Bearer {self.token_storage.get('access_token', '')}",
            "Content-Type": "application/json"
        }
    
    def is_token_valid(self) -> bool:
        """Check if the current access token is valid"""
        if not self.token_storage.get('access_token'):
            return False
        
        expires_at = self.token_storage.get('expires_at', 0)
        return datetime.now().timestamp() < expires_at
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        Returns True if successful, False otherwise.
        """
        try:
            refresh_token = self.token_storage.get('refresh_token')
            if not refresh_token:
                return False
            
            # Google OAuth token refresh endpoint
            refresh_url = "https://oauth2.googleapis.com/token"
            refresh_data = {
                'client_id': self.config['client_id'],
                'client_secret': self.config['client_secret'],
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(refresh_url, data=refresh_data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Update token storage
            self.token_storage.update({
                'access_token': token_data['access_token'],
                'expires_at': datetime.now().timestamp() + token_data.get('expires_in', 3600),
                'token_type': token_data.get('token_type', 'Bearer')
            })
            
            return True
            
        except Exception as e:
            print(f"Error refreshing Google Sheets access token: {e}")
            return False
    
    def get_sheet_data(self, spreadsheet_id: str = None, worksheet_name: str = None) -> Tuple[pd.DataFrame, str]:
        """
        Fetch data from Google Sheets using the service's access token.
        
        Args:
            spreadsheet_id (str, optional): The ID of the Google Spreadsheet. 
                                          If None, uses the default from config.
            worksheet_name (str, optional): Name of the specific worksheet. 
                                          If None, uses the first sheet.
        
        Returns:
            Tuple[pd.DataFrame, str]: A tuple containing:
                - DataFrame with the sheet data
                - Sheet ID (GID) of the worksheet
        
        Raises:
            Exception: If the request fails or the sheet is not found
        """
        
        # Use default spreadsheet ID if not provided
        if not spreadsheet_id:
            spreadsheet_id = SPREADSHEET_ID
        
        # Ensure we have a valid token
        if not self.is_token_valid():
            if not self.refresh_access_token():
                raise Exception("Unable to obtain valid access token for Google Sheets")
        
        headers = self.get_headers()
        
        try:
            # First, get the spreadsheet metadata to find the worksheet
            metadata_url = f"{self.base_url}/{spreadsheet_id}"
            metadata_response = requests.get(metadata_url, headers=headers)
            metadata_response.raise_for_status()
            
            spreadsheet_data = metadata_response.json()
            sheets = spreadsheet_data.get('sheets', [])
            
            if not sheets:
                raise Exception("No sheets found in the spreadsheet")
            
            # Find the target worksheet
            target_sheet = None
            if worksheet_name:
                # Look for the specific worksheet by name
                for sheet in sheets:
                    if sheet.get('properties', {}).get('title') == worksheet_name:
                        target_sheet = sheet
                        break
                
                if not target_sheet:
                    raise Exception(f"Worksheet '{worksheet_name}' not found in the spreadsheet")
            else:
                # Use the first sheet if no specific worksheet is provided
                target_sheet = sheets[0]
            
            # Get the sheet ID (GID)
            sheet_id = target_sheet.get('properties', {}).get('sheetId')
            sheet_title = target_sheet.get('properties', {}).get('title')
            
            if not sheet_id:
                raise Exception("Could not determine sheet ID")
            
            # Get the data from the specific worksheet
            data_url = f"{self.base_url}/{spreadsheet_id}/values/{sheet_title}"
            data_response = requests.get(data_url, headers=headers)
            data_response.raise_for_status()
            
            sheet_data = data_response.json()
            values = sheet_data.get('values', [])
            
            if not values:
                # Return empty DataFrame if no data
                return pd.DataFrame(), str(sheet_id)
            
            # Convert to DataFrame
            df = pd.DataFrame(values[1:], columns=values[0])  # First row as headers
            
            return df, str(sheet_id)
            
        except requests.exceptions.RequestException as e:
            if e.response and e.response.status_code == 401:
                # Try to refresh token and retry once
                if self.refresh_access_token():
                    return self.get_sheet_data(spreadsheet_id, worksheet_name)
                else:
                    raise Exception("Invalid or expired access token. Please refresh your token.")
            elif e.response and e.response.status_code == 404:
                raise Exception(f"Spreadsheet with ID '{spreadsheet_id}' not found or access denied.")
            else:
                raise Exception(f"Failed to fetch data from Google Sheets: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing sheet data: {str(e)}")
    
    def update_sheet_data(self, spreadsheet_id: str, worksheet_name: str, data: list, range_start: str = "A1") -> bool:
        """
        Update data in Google Sheets.
        
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet
            worksheet_name (str): Name of the worksheet to update
            data (list): 2D list of data to write
            range_start (str): Starting cell for the update (e.g., "A1")
        
        Returns:
            bool: True if successful, False otherwise
        """
        
        # Ensure we have a valid token
        if not self.is_token_valid():
            if not self.refresh_access_token():
                raise Exception("Unable to obtain valid access token for Google Sheets")
        
        headers = self.get_headers()
        
        try:
            # Prepare the update request
            range_name = f"{worksheet_name}!{range_start}"
            update_data = {
                "values": data
            }
            
            # Google Sheets API update endpoint
            update_url = f"{self.base_url}/{spreadsheet_id}/values/{range_name}?valueInputOption=RAW"
            
            response = requests.put(update_url, headers=headers, json=update_data)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            print(f"Error updating sheet data: {e}")
            return False
    
    def get_worksheet_names(self, spreadsheet_id: str = None) -> list:
        """
        Get list of worksheet names in the spreadsheet.
        
        Args:
            spreadsheet_id (str, optional): The ID of the Google Spreadsheet.
                                          If None, uses the default from config.
        
        Returns:
            list: List of worksheet names
        """
        
        if not spreadsheet_id:
            spreadsheet_id = SPREADSHEET_ID
        
        # Ensure we have a valid token
        if not self.is_token_valid():
            if not self.refresh_access_token():
                raise Exception("Unable to obtain valid access token for Google Sheets")
        
        headers = self.get_headers()
        
        try:
            metadata_url = f"{self.base_url}/{spreadsheet_id}"
            metadata_response = requests.get(metadata_url, headers=headers)
            metadata_response.raise_for_status()
            
            spreadsheet_data = metadata_response.json()
            sheets = spreadsheet_data.get('sheets', [])
            
            return [sheet.get('properties', {}).get('title', '') for sheet in sheets]
            
        except Exception as e:
            print(f"Error getting worksheet names: {e}")
            return []

# Global instance for easy access
sheets_service = GoogleSheetsService()

def get_sheet_data(access_token: str = None, spreadsheet_id: str = None, worksheet_name: str = None) -> Tuple[pd.DataFrame, str]:
    """
    Convenience function that uses the GoogleSheetsService.
    Maintains backward compatibility with the original function.
    """
    return sheets_service.get_sheet_data(spreadsheet_id, worksheet_name)
