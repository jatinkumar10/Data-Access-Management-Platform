# =============================================================================
# GOOGLE SSO CONFIGURATION (User Authentication)
# =============================================================================

# Get OAuth credentials from imported JSON file
GOOGLE_CLIENT_ID = "YOUR CLIENT ID HERE"
GOOGLE_CLIENT_SECRET = "YOUR CLIENT SECRET HERE"
GOOGLE_REDIRECT_URI = "YOUR REDIRECT URI HERE"

# =============================================================================
# GOOGLE SHEETS CONFIGURATION (Spreadsheet Access)
# =============================================================================
GOOGLE_SHEETS_CLIENT_ID = "YOUR CLIENT ID HERE"
GOOGLE_SHEETS_CLIENT_SECRET = "YOUR CLIENT SECRET HERE"
GOOGLE_SHEETS_REDIRECT_URI = "YOUR REDIRECT URI HERE"
GOOGLE_SHEETS_SCOPES = ["YOUR SCOPES HERE"]

# Google Sheets Configuration
SPREADSHEET_ID = "YOUR SPREADSHEET ID HERE"

# Token Storage Configuration for Google Sheets (Service Level)
SHEETS_TOKEN_STORAGE = {
    "refresh_token": "YOUR REFRESH TOKEN HERE",
    "access_token": "YOUR ACCESS TOKEN HERE",
    "expires_at": YOUR EXPIRES AT HERE,
    "token_type": "YOUR TOKEN TYPE HERE"
}

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================
APP_SECRET_KEY = "your_app_secret_key_here"
APP_NAME = "Access Management System"

# Database Configuration (if needed later)
DATABASE_URL = "your_database_url_here"

# Email Configuration
SMTP_SERVER = "YOUR SMTP SERVER HERE"
SMTP_PORT = YOUR SMTP PORT HERE
SMTP_USERNAME = "YOUR SMTP USERNAME HERE"
SMTP_PASSWORD = "YOUR SMTP PASSWORD HERE"

# Other Configuration
DEBUG = False
ENVIRONMENT = "production"

# Allowed domains (optional - restrict to specific email domains)
ALLOWED_DOMAINS = [
    "cars24.com",
    "cariotauto.com"
]

# =============================================================================
# CONFIGURATION HELPER FUNCTIONS
# =============================================================================
def get_sso_config():
    """Get SSO-specific configuration for user authentication"""
    return {
        "client_id": GOOGLE_SSO_CLIENT_ID,
        "client_secret": GOOGLE_SSO_CLIENT_SECRET,
        "redirect_uri": GOOGLE_SSO_REDIRECT_URI,
        "scopes": GOOGLE_SSO_SCOPES
    }

def get_sheets_config():
    """Get Google Sheets-specific configuration for spreadsheet access"""
    return {
        "client_id": GOOGLE_SHEETS_CLIENT_ID,
        "client_secret": GOOGLE_SHEETS_CLIENT_SECRET,
        "redirect_uri": GOOGLE_SHEETS_REDIRECT_URI,
        "scopes": GOOGLE_SHEETS_SCOPES
    }
