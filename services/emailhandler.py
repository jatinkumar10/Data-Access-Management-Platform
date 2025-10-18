import smtplib
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

class EmailHandler:
    """
    Service to handle email sending functionality for the Access Management System.
    Sends simple HTML emails with content as parameter.
    """
    
    def __init__(self):
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.smtp_username = SMTP_USERNAME
        self.smtp_password = SMTP_PASSWORD
        self.sender_email = SMTP_USERNAME
    
    def send_email(self, 
                  to_email: str, 
                  subject: str, 
                  content: str,
                  cc_emails: list = None) -> Dict[str, Any]:
        """
        Send a simple HTML email with optional CC recipients.
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            content (str): HTML email content
            cc_emails (list): List of CC email addresses
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add CC if provided
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Attach HTML content
            msg.attach(MIMEText(content, 'html'))
            
            # Prepare recipients list (to + cc)
            all_recipients = [to_email]
            if cc_emails:
                all_recipients.extend(cc_emails)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg, from_addr=self.sender_email, to_addrs=all_recipients)
            
            return {
                'success': True,
                'message': f'Email sent successfully to {to_email}' + (f' with CC to {", ".join(cc_emails)}' if cc_emails else ''),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'recipients': all_recipients
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    

    
    def send_user_creation_notifications(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email notifications for user creation request.
        
        Args:
            request_data (Dict[str, Any]): Request data containing user details
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Import email templates
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emails'))
            from emailtemplates import create_manager_notification_email
            
            user_email = request_data.get('user_email')
            manager_email = request_data.get('manager_email')
            
            if not user_email or not manager_email:
                return {
                    'success': False,
                    'message': 'Missing user email or manager email',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'Required email addresses not provided'
                }
            
            # Create email content
            manager_email_content = create_manager_notification_email(request_data)
            
            # Send email to manager with user in CC
            manager_result = self.send_email(
                to_email=manager_email,
                subject=f"User Creation Request - {request_data.get('request_id', 'N/A')}",
                content=manager_email_content,
                cc_emails=[user_email]
            )
            
            # Check if email was sent successfully
            if manager_result['success']:
                return {
                    'success': True,
                    'message': f'Email notification sent successfully to manager with user in CC',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'manager_email': manager_email,
                    'user_email': user_email
                }
            else:
                return {
                    'success': False,
                    'message': f'Failed to send email notification',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'manager_result': manager_result
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send email notifications: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def send_table_access_notifications(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email notifications for table access request.
        
        DEPRECATED: This method is deprecated in favor of sequential approval system.
        Table access requests now use the sequential approval service.
        
        Args:
            request_data (Dict[str, Any]): Request data containing user details
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        return {
            'success': False,
            'message': 'This method is deprecated. Table access requests now use sequential approval system.',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': 'Method deprecated - use sequential approval service instead'
        }
    
    def send_column_unhashing_notifications(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email notifications for column unhashing request.
        
        DEPRECATED: This method is deprecated in favor of sequential approval system.
        Column unhashing requests now use the sequential approval service.
        
        Args:
            request_data (Dict[str, Any]): Request data containing user details
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        return {
            'success': False,
            'message': 'This method is deprecated. Column unhashing requests now use sequential approval system.',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': 'Method deprecated - use sequential approval service instead'
        }
    
    def send_approval_notification(self, request_data: Dict[str, Any], approval_status: str, approver_email: str) -> Dict[str, Any]:
        """
        Send approval notification email to user.
        
        Args:
            request_data (Dict[str, Any]): Request data containing user details
            approval_status (str): Approval status (Approved/Rejected)
            approver_email (str): Email of the approver
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Import email templates
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emails'))
            from emailtemplates import create_approval_notification_email
            
            user_email = request_data.get('user_email')
            
            if not user_email:
                return {
                    'success': False,
                    'message': 'Missing user email',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'User email not provided'
                }
            
            # Create email content
            email_content = create_approval_notification_email(request_data, approval_status, approver_email)
            
            # Send email to user
            result = self.send_email(
                to_email=user_email,
                subject=f"User Creation Request {approval_status} - {request_data.get('request_id', 'N/A')}",
                content=email_content
            )
            
            return result
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send approval notification: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the email connection.
        
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            
            return {
                'success': True,
                'message': 'Email connection test successful',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Email connection test failed: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def send_sequential_approval_notification(self, request_data: dict, approver_level: str, previous_approvers: list) -> Dict[str, Any]:
        """
        Send approval notification to the next approver in the sequential chain.
        
        Args:
            request_data (dict): Request data
            approver_level (str): Current approver level (L1, L2, etc.)
            previous_approvers (list): List of previous approvers who have approved
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Import email templates
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emails'))
            from emailtemplates import create_sequential_approval_notification_email, create_gsheet_unmasking_notification_email
            
            approver_email = request_data.get('current_approver_email')
            request_id = request_data.get('request_id', 'N/A')
            
            if not approver_email:
                return {
                    'success': False,
                    'message': 'Approver email not provided',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Check if this is a GSheet unmasking request
            is_gsheet_request = (
                request_data.get('spreadsheet_id') or 
                request_data.get('named_range') or
                'gsheet' in str(request_data.get('request_id', '')).lower() or
                'unmasking' in str(request_data.get('request_type', '')).lower()
            )
            
            if is_gsheet_request:
                # Use GSheet-specific template
                print(f"DEBUG: Creating GSheet email for approver level: {approver_level}")
                email_content = create_gsheet_unmasking_notification_email(request_data, approver_level)
                subject = f"GSheet Unmasking Request Approval Required ({approver_level}) - {request_id}"
                print(f"DEBUG: GSheet email subject: {subject}")
            else:
                # Use generic template for other request types
                email_content = create_sequential_approval_notification_email(
                    request_data, approver_level, previous_approvers
                )
                subject = f"Data Access Request Approval Required ({approver_level}) - {request_id}"
            
            # Send email to current approver with requester in CC
            result = self.send_email(
                to_email=approver_email,
                subject=subject,
                content=email_content,
                cc_emails=[request_data.get('user_email', '')]
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send sequential approval notification: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def send_requester_approval_confirmation(self, request_data: dict, approver_email: str, approver_level: str) -> Dict[str, Any]:
        """
        Send confirmation to requester that their request has been approved by an approver.
        
        Args:
            request_data (dict): Request data
            approver_email (str): Email of the approver who approved
            approver_level (str): Level of the approver (L1, L2, etc.)
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            # Import email templates
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emails'))
            from emailtemplates import create_requester_approval_confirmation_email
            
            requester_email = request_data.get('user_email', request_data.get('requester_email'))
            request_id = request_data.get('request_id', 'N/A')
            
            if not requester_email:
                return {
                    'success': False,
                    'message': 'Requester email not provided',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Create email content
            email_content = create_requester_approval_confirmation_email(
                request_data, approver_email, approver_level
            )
            
            # Send email to requester
            result = self.send_email(
                to_email=requester_email,
                subject=f"Your Data Access Request has been Approved by {approver_level} - {request_id}",
                content=email_content
            )
            if result.get('success'):
                print(f"Mail sent to {approver_level} to '{approver_email}'")
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send requester approval confirmation: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def send_requester_rejection_notification(self, request_data: dict, approver_email: str, approver_level: str, rejection_reason: str = None) -> Dict[str, Any]:
        """
        Send rejection notification to requester.
        
        Args:
            request_data (dict): Request data
            approver_email (str): Email of the approver who rejected
            approver_level (str): Level of the approver (L1, L2, etc.)
            rejection_reason (str): Optional reason for rejection
            
        Returns:
            Dict[str, Any]: Result with success status and message
        """
        try:
            print(f"DEBUG: send_requester_rejection_notification called with request_data: {request_data}")
            print(f"DEBUG: approver_email: {approver_email}, approver_level: {approver_level}, rejection_reason: {rejection_reason}")
            # Import email templates
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emails'))
            from emailtemplates import create_requester_rejection_notification_email
            
            requester_email = request_data.get('user_email', request_data.get('requester_email'))
            request_id = request_data.get('request_id', 'N/A')
            
            if not requester_email:
                return {
                    'success': False,
                    'message': 'Requester email not provided',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Create email content
            email_content = create_requester_rejection_notification_email(
                request_data, approver_email, approver_level, rejection_reason
            )
            
            # Send email to requester
            print(f"DEBUG: Sending rejection email to {requester_email}")
            print(f"DEBUG: Subject: Your Data Access Request has been Rejected by {approver_level} - {request_id}")
            result = self.send_email(
                to_email=requester_email,
                subject=f"Your Data Access Request has been Rejected by {approver_level} - {request_id}",
                content=email_content
            )
            print(f"DEBUG: Email send result: {result}")
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send requester rejection notification: {str(e)}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }

# Global email handler instance
email_handler = EmailHandler()

def get_email_handler() -> EmailHandler:
    """
    Get the global email handler instance.
    
    Returns:
        EmailHandler: The global email handler instance
    """
    return email_handler

# Convenience functions
def send_email(to_email: str, subject: str, content: str, cc_emails: list = None) -> Dict[str, Any]:
    """
    Convenience function to send a simple HTML email.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        content (str): HTML email content
        cc_emails (list): List of CC email addresses
        
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    return email_handler.send_email(to_email, subject, content, cc_emails)

def send_user_creation_notifications(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to send user creation notifications.
    
    Args:
        request_data (Dict[str, Any]): Request data containing user details
        
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    return email_handler.send_user_creation_notifications(request_data)

def send_table_access_notifications(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to send table access notifications.
    
    DEPRECATED: This function is deprecated in favor of sequential approval system.
    
    Args:
        request_data (Dict[str, Any]): Request data containing user details
        
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    return email_handler.send_table_access_notifications(request_data)

def send_column_unhashing_notifications(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to send column unhashing notifications.
    
    DEPRECATED: This function is deprecated in favor of sequential approval system.
    
    Args:
        request_data (Dict[str, Any]): Request data containing user details
        
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    return email_handler.send_column_unhashing_notifications(request_data)

def send_approval_notification(request_data: Dict[str, Any], approval_status: str, approver_email: str) -> Dict[str, Any]:
    """
    Convenience function to send approval notification.
    
    Args:
        request_data (Dict[str, Any]): Request data containing user details
        approval_status (str): Approval status (Approved/Rejected)
        approver_email (str): Email of the approver
        
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    return email_handler.send_approval_notification(request_data, approval_status, approver_email)


def send_gsheet_unmasking_notifications(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send email notifications for GSheet Unmasking Request.
    Args:
        request_data (Dict[str, Any]): Request data containing all submitted fields
    Returns:
        Dict[str, Any]: Result with success status and message
    """
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emails'))
        from emailtemplates import create_gsheet_unmasking_notification_email
        
        # Create email content using the new template
        email_content = create_gsheet_unmasking_notification_email(request_data)
        
        # Get L1 approver email
        l1_approver_email = request_data.get('l1_approver', '')
        requester_email = request_data.get('user_email', '')
        request_id = request_data.get('request_id', 'N/A')
        
        if not l1_approver_email:
            return {
                'success': False,
                'message': 'L1 approver email not found',
                'error': 'L1 approver not configured'
            }
        
        # Send email to L1 approver with requester in CC
        result = send_email(
            to_email=l1_approver_email,
            subject=f"GSheet Unmasking Request Approval Required (L1) - {request_id}",
            content=email_content,
            cc_emails=[requester_email]
        )
        
        return {
            'success': result.get('success', False),
            'message': result.get('message', 'Email sent to L1 approver'),
            'recipients': [l1_approver_email],
            'cc_recipients': [requester_email],
            'request_id': request_id
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to send GSheet Unmasking email notifications: {str(e)}',
            'error': str(e)
        }
