#!/usr/bin/env python3

import sys
import os
from datetime import datetime

# Add parent directory to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def get_email_base_template() -> str:
    """
    Get the base email template with minimal styling.
    
    Returns:
        str: Base HTML template
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 1000px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="background-color: #667eea; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 20px; font-weight: 600;">🚀 Access Management System</h1>
            </div>
            <div style="padding: 30px 20px; background-color: #ffffff;">
                {content}
            </div>
        </div>
    </body>
    </html>
    """

def get_name_from_email(email: str) -> str:
    """
    Extract a readable name from an email address.
    
    Args:
        email (str): Email address
        
    Returns:
        str: Formatted name from email
    """
    if not email or '@' not in email:
        return "Manager"
    
    # Extract the part before @
    name_part = email.split('@')[0]
    
    # Handle common patterns
    if '.' in name_part:
        # Split by dots and capitalize each part
        name_parts = name_part.split('.')
        formatted_name = ' '.join(part.capitalize() for part in name_parts)
    elif '_' in name_part:
        # Split by underscores and capitalize each part
        name_parts = name_part.split('_')
        formatted_name = ' '.join(part.capitalize() for part in name_parts)
    else:
        # Just capitalize the single word
        formatted_name = name_part.capitalize()
    
    return formatted_name

def create_manager_notification_email(request_data: dict) -> str:
    """
    Create HTML email template for manager notification.
    
    Args:
        request_data (dict): Request data containing user details
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    # Get manager name from email
    manager_name = get_name_from_email(request_data.get('manager_email', ''))
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {manager_name},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        A new user creation request on Snowflake has been submitted and requires your approval. 
        Please find the request details below:
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">User Name:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Email ID:</span>
            <span style="color: #555;">{request_data.get('user_email', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Business Unit (BU):</span>
            <span style="color: #555;">{request_data.get('business_unit', 'N/A')}</span>
        </div>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Kindly review and take the necessary action. You can approve or reject this request 
        through the Access Management System dashboard.
    </div>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://access-request.data.c24mlplatform.com/?state={request_data.get('request_id', '')}" style="display: inline-block; background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 0 10px;">
            🔗 Approve/Reject Here
        </a>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Thank you,<br>
        <strong>Access Management System</strong>
    </div>
    """
    
    return base_template.format(
        content=content,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )



def create_approval_notification_email(request_data: dict, approval_status: str, approver_email: str) -> str:
    """
    Create HTML email template for approval notification.
    
    Args:
        request_data (dict): Request data containing user details
        approval_status (str): Approval status (Approved/Rejected)
        approver_email (str): Email of the approver
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    status_emoji = "✅" if approval_status.lower() == "approved" else "❌"
    status_color = "#28a745" if approval_status.lower() == "approved" else "#dc3545"
    status_text = "Approved" if approval_status.lower() == "approved" else "Rejected"
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {request_data.get('user_name', 'User')},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Your Snowflake user creation request has been reviewed and <strong style="color: {status_color};">{status_text}</strong>.
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">User Name:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Email ID:</span>
            <span style="color: #555;">{request_data.get('user_email', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Business Unit (BU):</span>
            <span style="color: #555;">{request_data.get('business_unit', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Status:</span>
            <span style="color: #555;">
                {status_text} <span style="display: inline-block; background-color: {status_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 10px;">{status_emoji}</span>
            </span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Approved By:</span>
            <span style="color: #555;">{approver_email}</span>
        </div>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        {f"🎉 Your request has been approved! The necessary access permissions will be granted shortly." if approval_status.lower() == "approved" else "If you have any questions about this decision, please contact the approver or submit a new request with additional details."}
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Thank you,<br>
        <strong>Access Management System</strong>
    </div>
    """
    
    return base_template.format(
        content=content,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

def create_table_access_manager_notification_email(request_data: dict, approver_type: str = 'RM_APPROVER') -> str:
    """
    Create HTML email template for table access manager notification.
    
    Args:
        request_data (dict): Request data containing user details
        approver_type (str): Type of approver ('RM_APPROVER' or 'DATA_APPROVER')
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    # Get manager name from email based on approver type - Updated for sequential approval
    if approver_type == 'DATA_APPROVER':
        approver_email = request_data.get('data_approver', '')
        approver_title = "Level L1 Approver"  # Updated for sequential approval
    else:
        approver_email = request_data.get('rm_approver', '')
        approver_title = "Level L1 Approver"  # Updated for sequential approval
    
    manager_name = get_name_from_email(approver_email)
    
    # Format tables for display - remove brackets and quotes
    def format_tables_display(tables_data):
        if not tables_data:
            return "N/A"
        if isinstance(tables_data, list):
            return ", ".join(str(item).strip("[]'\"") for item in tables_data)
        else:
            return str(tables_data).strip("[]'\"")
    
    tables_display = format_tables_display(request_data.get('tables', [])) if request_data.get('tables') else "N/A"
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {manager_name},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        A new Snowflake table access request has been submitted and requires your approval as <strong>{approver_title}</strong> in the sequential approval chain. 
        Please find the request details below:
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">User Name:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Email ID:</span>
            <span style="color: #555;">{request_data.get('user_email', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Business Unit (BU):</span>
            <span style="color: #555;">{request_data.get('business_unit', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Database:</span>
            <span style="color: #555;">{request_data.get('database', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Schema:</span>
            <span style="color: #555;">{request_data.get('schema', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Tables:</span>
            <span style="color: #555;">{tables_display}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Requesting For:</span>
            <span style="color: #555;">{request_data.get('requesting_for_value', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Validity:</span>
            <span style="color: #555;">{request_data.get('validity_days', 'N/A')} days</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Objective of your analysis that requires this data access:</span>
            <span style="color: #555;">{request_data.get('objective', request_data.get('reason', 'N/A'))}</span>
        </div>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Kindly review and take the necessary action. You can approve or reject this request 
        through the Access Management System dashboard.
    </div>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://access-request.data.c24mlplatform.com/?state={request_data.get('request_id', '')}" style="display: inline-block; background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 0 10px;">
            🔗 Approve/Reject Here
        </a>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Thank you,<br>
        <strong>Access Management System</strong>
    </div>
    """
    
    return base_template.format(
        content=content,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )



def create_column_unhashing_manager_notification_email(request_data: dict, approver_type: str = 'RM_APPROVER') -> str:
    """
    Create HTML email template for column unhashing manager notification.
    
    Args:
        request_data (dict): Request data containing user details
        approver_type (str): Type of approver ('RM_APPROVER' or 'DATA_APPROVER')
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    # Get manager name from email based on approver type
    if approver_type == 'DATA_APPROVER':
        approver_email = request_data.get('data_approver', '')
        approver_title = "Level L5 Approver"
    else:
        approver_email = request_data.get('rm_approver', '')
        approver_title = "Level L1 Approver"
    
    manager_name = get_name_from_email(approver_email)
    
    # Format columns for display - remove brackets and quotes
    def format_columns_display(columns_data):
        if not columns_data:
            return "N/A"
        if isinstance(columns_data, list):
            return ", ".join(str(item).strip("[]'\"") for item in columns_data)
        else:
            return str(columns_data).strip("[]'\"")
    
    columns_display = format_columns_display(request_data.get('columns', [])) if request_data.get('columns') else "N/A"
    
    # Format table name for display - remove brackets and quotes
    table_display = format_columns_display(request_data.get('table', 'N/A'))
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {manager_name},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        A new Snowflake column unhashing request has been submitted and requires your approval as <strong>{approver_title}</strong>. 
        Please find the request details below:
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">User Name:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Email ID:</span>
            <span style="color: #555;">{request_data.get('user_email', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Business Unit (BU):</span>
            <span style="color: #555;">{request_data.get('business_unit', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Database:</span>
            <span style="color: #555;">{request_data.get('database', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Schema:</span>
            <span style="color: #555;">{request_data.get('schema', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Table:</span>
            <span style="color: #555;">{table_display}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Columns:</span>
            <span style="color: #555;">{columns_display}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Requesting For:</span>
            <span style="color: #555;">{request_data.get('requesting_for_value', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Validity:</span>
            <span style="color: #555;">{request_data.get('validity_days', 'N/A')} days</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Reason Category:</span>
            <span style="color: #555;">{request_data.get('reason_category', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Objective of your analysis that requires unhashed data access:</span>
            <span style="color: #555;">{request_data.get('objective', request_data.get('reason', 'N/A'))}</span>
        </div>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Kindly review and take the necessary action. You can approve or reject this request 
        through the Access Management System dashboard.
    </div>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://access-request.data.c24mlplatform.com/?state={request_data.get('request_id', '')}" style="display: inline-block; background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 0 10px;">
            🔗 Approve/Reject Here
        </a>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Thank you,<br>
        <strong>Access Management System</strong>
    </div>
    """
    
    return base_template.format(
        content=content,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )



def create_table_access_approval_notification_email(request_data: dict, approval_type: str, approval_status: str, approver_email: str) -> str:
    """
    Create HTML email template for table access approval notification.
    
    Args:
        request_data (dict): Request data containing user details
        approval_type (str): 'RM_APPROVER' or 'DATA_APPROVER'
        approval_status (str): 'Approved' or 'Rejected'
        approver_email (str): Email of the approver
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    status_emoji = "✅" if approval_status.lower() == "approved" else "❌"
    status_color = "#28a745" if approval_status.lower() == "approved" else "#dc3545"
    status_text = "Approved" if approval_status.lower() == "approved" else "Rejected"
    
    # Format tables for display - remove brackets and quotes
    def format_tables_display(tables_data):
        if not tables_data:
            return "N/A"
        if isinstance(tables_data, list):
            return ", ".join(str(item).strip("[]'\"") for item in tables_data)
        else:
            return str(tables_data).strip("[]'\"")
    
    tables_display = format_tables_display(request_data.get('tables', [])) if request_data.get('tables') else format_tables_display(request_data.get('table', 'N/A'))
    
    # Format approval type for display
    if approval_type == 'DATA_APPROVER':
        approval_type_display = 'Level L5 Approver'
    else:
        approval_type_display = 'Level L1 Approver'
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {request_data.get('user_name', 'User')},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Your Snowflake table access request has been reviewed by the <strong>{approval_type_display}</strong> and has been <strong style="color: {status_color};">{status_text}</strong>.
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">User Name:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Email ID:</span>
            <span style="color: #555;">{request_data.get('user_email', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Database:</span>
            <span style="color: #555;">{request_data.get('database', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Schema:</span>
            <span style="color: #555;">{request_data.get('schema', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Tables:</span>
            <span style="color: #555;">{tables_display}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Requesting For:</span>
            <span style="color: #555;">{request_data.get('requesting_for_value', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Validity:</span>
            <span style="color: #555;">{request_data.get('validity_days', 'N/A')} days</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Objective:</span>
            <span style="color: #555;">{request_data.get('objective', request_data.get('reason', 'N/A'))}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Status:</span>
            <span style="color: #555;">
                {status_text} by {approval_type_display} <span style="display: inline-block; background-color: {status_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 10px;">{status_emoji}</span>
            </span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Approved By:</span>
            <span style="color: #555;">{approver_email}</span>
        </div>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        {f"🎉 Your Snowflake table access request has been approved by the {approval_type_display}! The necessary permissions will be granted shortly." if approval_status.lower() == "approved" else f"Your Snowflake table access request has been rejected by the {approval_type_display}. If you have any questions about this decision, please contact the approver or submit a new request with additional details."}
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Thank you,<br>
        <strong>Access Management System</strong>
    </div>
    """
    
    return base_template.format(
        content=content,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

def create_column_unhashing_approval_notification_email(request_data: dict, approval_type: str, approval_status: str, approver_email: str) -> str:
    """
    Create HTML email template for column unhashing approval notification.
    
    Args:
        request_data (dict): Request data containing user details
        approval_type (str): 'RM_APPROVER' or 'DATA_APPROVER'
        approval_status (str): 'Approved' or 'Rejected'
        approver_email (str): Email of the approver
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    status_emoji = "✅" if approval_status.lower() == "approved" else "❌"
    status_color = "#28a745" if approval_status.lower() == "approved" else "#dc3545"
    status_text = "Approved" if approval_status.lower() == "approved" else "Rejected"
    
    # Format columns for display - remove brackets and quotes
    def format_columns_display(columns_data):
        if not columns_data:
            return "N/A"
        if isinstance(columns_data, list):
            return ", ".join(str(item).strip("[]'\"") for item in columns_data)
        else:
            return str(columns_data).strip("[]'\"")
    
    columns_display = format_columns_display(request_data.get('columns', [])) if request_data.get('columns') else format_columns_display(request_data.get('column', 'N/A'))
    
    # Format table name for display - remove brackets and quotes
    table_display = format_columns_display(request_data.get('table', 'N/A'))
    
    # Format approval type for display
    if approval_type == 'DATA_APPROVER':
        approval_type_display = 'Level L5 Approver'
    else:
        approval_type_display = 'Level L1 Approver'
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {request_data.get('user_name', 'User')},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Your Snowflake column unhashing request has been reviewed by the <strong>{approval_type_display}</strong> and has been <strong style="color: {status_color};">{status_text}</strong>.
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">User Name:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Email ID:</span>
            <span style="color: #555;">{request_data.get('user_email', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Database:</span>
            <span style="color: #555;">{request_data.get('database', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Schema:</span>
            <span style="color: #555;">{request_data.get('schema', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Table:</span>
            <span style="color: #555;">{table_display}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Columns:</span>
            <span style="color: #555;">{columns_display}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Requesting For:</span>
            <span style="color: #555;">{request_data.get('requesting_for_value', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Validity:</span>
            <span style="color: #555;">{request_data.get('validity_days', 'N/A')} days</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Objective:</span>
            <span style="color: #555;">{request_data.get('objective', request_data.get('reason', 'N/A'))}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Status:</span>
            <span style="color: #555;">
                {status_text} by {approval_type_display} <span style="display: inline-block; background-color: {status_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 10px;">{status_emoji}</span>
            </span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Approved By:</span>
            <span style="color: #555;">{approver_email}</span>
        </div>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        {f"🎉 Your Snowflake column unhashing request has been approved by the {approval_type_display}! The necessary permissions will be granted shortly." if approval_status.lower() == "approved" else f"Your Snowflake column unhashing request has been rejected by the {approval_type_display}. If you have any questions about this decision, please contact the approver or submit a new request with additional details."}
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Thank you,<br>
        <strong>Access Management System</strong>
    </div>
    """
    
    return base_template.format(
        content=content,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

def create_multi_approver_notification_email(request_data: dict, approval_status: str, approver_email: str) -> str:
    """
    Create HTML email template for multi-approver notification (same person is both L1 and L5 approver).
    
    Args:
        request_data (dict): Request data containing user details
        approval_status (str): 'Approved' or 'Rejected'
        approver_email (str): Email of the approver
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    status_emoji = "✅" if approval_status.lower() == "approved" else "❌"
    status_color = "#28a745" if approval_status.lower() == "approved" else "#dc3545"
    status_text = "Approved" if approval_status.lower() == "approved" else "Rejected"
    
    # Format data based on request type
    def format_data_display(data):
        if not data:
            return "N/A"
        if isinstance(data, list):
            return ", ".join(str(item).strip("[]'\"") for item in data)
        else:
            return str(data).strip("[]'\"")
    
    if request_data.get('request_type') == 'Table request':
        data_display = format_data_display(request_data.get('tables', [])) if request_data.get('tables') else format_data_display(request_data.get('table', 'N/A'))
        data_label = "Tables"
        request_type_display = "Table Access"
    else:  # Column request
        data_display = format_data_display(request_data.get('columns', [])) if request_data.get('columns') else format_data_display(request_data.get('column', 'N/A'))
        data_label = "Columns"
        request_type_display = "Column Unhashing"
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {request_data.get('user_name', 'User')},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Your {request_type_display.lower()} request has been reviewed and <strong style="color: {status_color};">{status_text}</strong> by both Level L1 and Level L5 Approver.
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">User Name:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Email ID:</span>
            <span style="color: #555;">{request_data.get('user_email', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Database:</span>
            <span style="color: #555;">{request_data.get('database', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Schema:</span>
            <span style="color: #555;">{request_data.get('schema', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">{data_label}:</span>
            <span style="color: #555;">{data_display}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Requesting For:</span>
            <span style="color: #555;">{request_data.get('requesting_for_value', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Validity:</span>
            <span style="color: #555;">{request_data.get('validity_days', 'N/A')} days</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Objective:</span>
            <span style="color: #555;">{request_data.get('objective', request_data.get('reason', 'N/A'))}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Status:</span>
            <span style="color: #555;">
                {status_text} by Both Approvers <span style="display: inline-block; background-color: {status_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 10px;">{status_emoji}</span>
            </span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Approved By:</span>
            <span style="color: #555;">{approver_email} (Level L1 & Level L5 Approver)</span>
        </div>
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        {f"🎉 Your Snowflake {request_type_display.lower()} request has been approved by both RM and Data Owner Approver! The necessary permissions will be granted shortly." if approval_status.lower() == "approved" else f"Your Snowflake {request_type_display.lower()} request has been rejected by both RM and Data Owner Approver. If you have any questions about this decision, please contact the approver or submit a new request with additional details."}
    </div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Thank you,<br>
        <strong>Access Management System</strong>
    </div>
    """
    
    return base_template.format(
        content=content,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )




def create_gsheet_unmasking_notification_email(request_data: dict, approver_level: str = 'L1') -> str:
    """
    Create HTML email template for GSheet unmasking request notification.
    
    Args:
        request_data (dict): Request data containing all form fields
        approver_level (str): Current approver level (L1, L2, etc.)
        
    Returns:
        str: HTML email content
    """
    print(f"DEBUG: create_gsheet_unmasking_notification_email called with approver_level: {approver_level}")
    base_template = get_email_base_template()
    
    # Get approver name from email (try multiple sources)
    approver_email = (
        request_data.get('l1_approver', '') or 
        request_data.get('current_approver_email', '') or
        request_data.get('approver_email', '')
    )
    approver_name = get_name_from_email(approver_email)
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {approver_name},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        A GSheet Unmasking request requires your approval as <strong>Level {approver_level} Approver</strong> in the sequential approval chain. 
        Please find the request details below:
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Requester:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')} ({request_data.get('user_email', 'N/A')})</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Spreadsheet ID:</span>
            <span style="color: #555;">{request_data.get('spreadsheet_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Named Range:</span>
            <span style="color: #555;">{request_data.get('named_range', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Who Has Access:</span>
            <span style="color: #555;">{request_data.get('who_has_access', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">End User Details:</span>
            <span style="color: #555;">{request_data.get('end_user_description', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Use Case:</span>
            <span style="color: #555;">{request_data.get('use_case', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Validity:</span>
            <span style="color: #555;">{request_data.get('validity_days', 'N/A')} days</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Objective of the sheet/analysis:</span>
            <span style="color: #555;">{request_data.get('remarks', 'N/A')}</span>
        </div>
    </div>
    
    <div style="background-color: #e8f5e8; border: 1px solid #d4edda; border-radius: 5px; padding: 15px; margin: 20px 0;">
        <div style="font-weight: 600; color: #155724; margin-bottom: 10px;">🔒 Action Required</div>
        <div style="color: #155724; font-size: 14px; margin-bottom: 15px;">
            Please review and approve/reject this request by clicking the link below:
        </div>
        <div style="text-align: center;">
            <a href="https://access-request.data.c24mlplatform.com/?state={request_data.get('request_id', '')}" style="display: inline-block; background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 0 10px;">
                🔗 Approve/Reject
            </a>
        </div>
    </div>
    
    <div style="margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 20px;">
        <div>This is an automated email from the Access Management System.</div>
        <div>Please do not reply to this email.</div>
        <div>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    """
    
    return base_template.format(content=content)

def get_gsheet_unmasking_email_template(
    spreadsheet_id,
    named_range,
    access_type,
    end_user_description,
    use_case,
    remarks,
    requester_email
):
    """
    Returns subject and body for Gsheet Unmasking Request email.
    DEPRECATED: Use create_gsheet_unmasking_notification_email instead.
    """
    subject = "Gsheet_unmasking_requests"
    body = f"""
    Dear User,<br><br>
    A new Google Sheet unmasking request has been submitted.<br><br>
    <b>Spreadsheet ID:</b> {spreadsheet_id}<br>
    <b>Named Range:</b> {named_range}<br>
    <b>Who Has Access:</b> {access_type}<br>
    <b>END_USER_DESCRIPTION:</b> {end_user_description if access_type.startswith('Others') else '-'}<br>
    <b>Use Case:</b> {use_case}<br>
    <b>Remarks:</b> {remarks}<br>
    <b>Requester Email:</b> {requester_email}<br><br>
    Please review and take appropriate action.<br><br>
    <button>Approve</button> <button>Reject</button>
    """
    return subject, body

def create_sequential_approval_notification_email(request_data: dict, approver_level: str, previous_approvers: list) -> str:
    """
    Create HTML email template for sequential approval notification.
    
    Args:
        request_data (dict): Request data containing user details
        approver_level (str): Current approver level (L1, L2, etc.)
        previous_approvers (list): List of previous approvers who have approved
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    # Get approver name from email
    approver_name = get_name_from_email(request_data.get('current_approver_email', ''))
    
    # Create previous approvers section
    if previous_approvers:
        previous_approvers_html = "<div style='margin-top: 15px;'><strong>Previous Approvals:</strong><ul>"
        for level in previous_approvers:
            previous_approvers_html += f"<li>Level {level} - Approved ✅</li>"
        previous_approvers_html += "</ul></div>"
    else:
        previous_approvers_html = ""
    
    # Handle different request types
    request_type = request_data.get('request_type', 'Data Access')
    
    # Check if it's a table or column request based on available data
    is_table_request = request_data.get('table_name') or request_data.get('tables')
    is_column_request = request_data.get('column_name') or request_data.get('columns')
    
    if is_table_request:
        request_type = "Table Access"
    elif is_column_request:
        request_type = "Column Unhashing"
    elif 'table' in str(request_type).lower():
        request_type = "Table Access"
        is_table_request = True
    elif 'column' in str(request_type).lower():
        request_type = "Column Unhashing"
        is_column_request = True
    
    # Format table name to remove brackets and quotes
    def format_table_name(table_data):
        if not table_data:
            return 'N/A'
        if isinstance(table_data, list):
            # Join list items with comma and remove any brackets/quotes
            return ', '.join(str(item).strip("[]'\"") for item in table_data)
        else:
            # Remove brackets and quotes from string
            return str(table_data).strip("[]'\"")
    
    # Format column name to remove brackets and quotes
    def format_column_name(column_data):
        if not column_data:
            return 'N/A'
        if isinstance(column_data, list):
            # Join list items with comma and remove any brackets/quotes
            return ', '.join(str(item).strip("[]'\"") for item in column_data)
        else:
            # Remove brackets and quotes from string
            return str(column_data).strip("[]'\"")
    
    # Build the request details section
    request_details = f"""
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Requester:</span>
            <span style="color: #555;">{request_data.get('user_name', 'N/A')} ({request_data.get('user_email', 'N/A')})</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Entity:</span>
            <span style="color: #555;">{request_data.get('entity', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Database:</span>
            <span style="color: #555;">{request_data.get('database', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Schema:</span>
            <span style="color: #555;">{request_data.get('schema', 'N/A')}</span>
        </div>"""
    
    # Add table name for both table requests and column requests
    if is_table_request or is_column_request:
        table_name = format_table_name(request_data.get('table_name', request_data.get('tables', request_data.get('table'))))
        request_details += f"""
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Table Name:</span>
            <span style="color: #555;">{table_name}</span>
        </div>"""
    
    # Add column name only for column requests
    if is_column_request:
        column_name = format_column_name(request_data.get('column_name', request_data.get('columns')))
        request_details += f"""
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Column Name:</span>
            <span style="color: #555;">{column_name}</span>
        </div>"""
    
    # Add reason
    request_details += f"""
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Objective of your analysis that requires this data access:</span>
            <span style="color: #555;">{request_data.get('objective', request_data.get('reason', 'N/A'))}</span>
        </div>
        {previous_approvers_html}
    </div>"""
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {approver_name},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        A Snowflake {request_type} request requires your approval as <strong>Level {approver_level} Approver</strong> in the sequential approval chain. 
        Please find the request details below:
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0;">{request_details}
    
    <div style="background-color: #e8f5e8; border: 1px solid #d4edda; border-radius: 5px; padding: 15px; margin: 20px 0;">
        <div style="font-weight: 600; color: #155724; margin-bottom: 10px;">🔒 Action Required</div>
        <div style="color: #155724; font-size: 14px; margin-bottom: 15px;">
            Please review and approve/reject this request by clicking the link below:
        </div>
        <div style="text-align: center;">
            <a href="https://access-request.data.c24mlplatform.com/?state={request_data.get('request_id', '')}" style="display: inline-block; background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 0 10px;">
                🔗 Approve/Reject
            </a>
        </div>
    </div>
    
    <div style="margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 20px;">
        <div>This is an automated email from the Access Management System.</div>
        <div>Please do not reply to this email.</div>
        <div>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    """
    
    return base_template.format(content=content)

def create_requester_approval_confirmation_email(request_data: dict, approver_email: str, approver_level: str) -> str:
    """
    Create HTML email template for requester approval confirmation.
    
    Args:
        request_data (dict): Request data
        approver_email (str): Email of the approver who approved
        approver_level (str): Level of the approver (L1, L2, etc.)
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    # Get requester name from email
    requester_name = get_name_from_email(request_data.get('user_email', ''))
    approver_name = get_name_from_email(approver_email)
    
    # Determine if this is the final approval by checking if there are any higher-level approvers configured
    approver_levels = ['L1', 'L2', 'L3', 'L4', 'L5']
    current_level_index = approver_levels.index(approver_level) if approver_level in approver_levels else -1
    
    # Check if there are configured approvers after current level
    has_next_approver = False
    if current_level_index >= 0 and current_level_index < len(approver_levels) - 1:
        for next_level in approver_levels[current_level_index + 1:]:
            next_approver_key = f"{next_level.lower()}_approver"
            next_approver_email = request_data.get(next_approver_key, '').strip()
            if next_approver_email and next_approver_email.lower() != 'n/a':
                has_next_approver = True
                break
    
    # This is the final approval if there are no more approvers configured
    is_final_approval = not has_next_approver
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {requester_name},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        Good news! Your Snowflake data access request has been approved by <strong>{approver_level}</strong> approver.
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #28a745; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Approved by:</span>
            <span style="color: #555;">{approver_name} ({approver_level})</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Status:</span>
            <span style="color: #28a745; font-weight: 600;">✅ Approved</span>
        </div>
    </div>
    
    <div style="background-color: {'#d4edda' if is_final_approval else '#fff3cd'}; border: 1px solid {'#c3e6cb' if is_final_approval else '#ffeaa7'}; border-radius: 5px; padding: 15px; margin: 20px 0;">
        <div style="font-weight: 600; color: {'#155724' if is_final_approval else '#856404'}; margin-bottom: 10px;">
            {'🎉 Request Completed' if is_final_approval else 'ℹ️ Next Steps'}
        </div>
        <div style="color: {'#155724' if is_final_approval else '#856404'}; font-size: 14px;">
            {'''Congratulations! Your request has been fully approved and is now complete. You should have access to the requested resources within 24 hours.''' if is_final_approval else '''Your request is now forwarded to the next approver in the chain. You will receive another notification once the entire approval process is complete.'''}
        </div>
    </div>
    
    <div style="margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 20px;">
        <div>This is an automated email from the Access Management System.</div>
        <div>Please do not reply to this email.</div>
        <div>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    """
    
    return base_template.format(content=content)

def create_requester_rejection_notification_email(request_data: dict, approver_email: str, approver_level: str, rejection_reason: str = None) -> str:
    """
    Create HTML email template for requester rejection notification.
    
    Args:
        request_data (dict): Request data
        approver_email (str): Email of the approver who rejected
        approver_level (str): Level of the approver (L1, L2, etc.)
        rejection_reason (str): Optional reason for rejection
        
    Returns:
        str: HTML email content
    """
    base_template = get_email_base_template()
    
    # Get requester name from email
    requester_name = get_name_from_email(request_data.get('user_email', ''))
    approver_name = get_name_from_email(approver_email)
    
    rejection_reason_html = ""
    if rejection_reason:
        rejection_reason_html = f"""
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Reason:</span>
            <span style="color: #555;">{rejection_reason}</span>
        </div>
        """
    
    content = f"""
    <div style="font-size: 18px; font-weight: 600; color: #2c3e50; margin-bottom: 20px;">Dear {requester_name},</div>
    
    <div style="font-size: 14px; line-height: 1.8; color: #555; margin-bottom: 25px;">
        We regret to inform you that your Snowflake data access request has been rejected by the <strong>{approver_level}</strong> approver.
    </div>
    
    <div style="background-color: #f8f9fa; border-left: 4px solid #dc3545; padding: 20px; margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Request ID:</span>
            <span style="color: #555;">{request_data.get('request_id', 'N/A')}</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Rejected by:</span>
            <span style="color: #555;">{approver_name} ({approver_level})</span>
        </div>
        <div style="margin-bottom: 10px;">
            <span style="font-weight: 600; color: #2c3e50; display: inline-block; width: 150px;">Status:</span>
            <span style="color: #dc3545; font-weight: 600;">❌ Rejected</span>
        </div>
        {rejection_reason_html}
    </div>
    
    <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; padding: 15px; margin: 20px 0;">
        <div style="font-weight: 600; color: #721c24; margin-bottom: 10px;">📝 What's Next?</div>
        <div style="color: #721c24; font-size: 14px;">
            If you believe this rejection was in error or you have additional information to support your request, please contact the approver directly or submit a new request with updated details.
        </div>
    </div>
    
    <div style="margin-top: 30px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 20px;">
        <div>This is an automated email from the Access Management System.</div>
        <div>Please do not reply to this email.</div>
        <div>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    """
    
    return base_template.format(content=content)