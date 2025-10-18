import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add context directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'context'))

# Add services directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

from user_context import get_user_context, get_form_placeholders
from context.filecontext import get_user_requests, get_request_summary

def render_user_dashboard():
    """Render the User Dashboard component."""
    
    # Get user context and placeholders
    user_context = get_user_context()
    placeholders = get_form_placeholders()
    user_email = placeholders['email']
    
    # Get real request data from sheets
    try:
        request_data = get_user_requests(user_email)
    except Exception as e:
        st.warning(f"⚠️ Could not fetch request data: {str(e)}")
        request_data = []
    
    # Calculate summary based on all data (before filtering)
    total = len(request_data)
    pending = sum(1 for req in request_data if "⏳" in req.get("Overall Status", ""))
    approved = sum(1 for req in request_data if "✅" in req.get("Overall Status", ""))
    rejected = sum(1 for req in request_data if "❌" in req.get("Overall Status", ""))
    
    # Summary section - single line format (before filters)
    st.write(f"**Summary: Total: {total} | Pending: {pending} ⏳ | Approved: {approved} ✅ | Rejected: {rejected} ❌**")
    
    # Filters section
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Pending", "Approved", "Rejected"],
            key="status_filter"
        )
    
    with col2:
        type_filter = st.selectbox(
            "Filter by Type",
            ["All", "Table request", "Column request", "User Creation", "GSheet Unmasking"],
            key="type_filter"
        )
    
    with col3:
        search_request_id = st.text_input(
            "Search by Request ID",
            placeholder="Enter Request ID...",
            key="search_request_id"
        )
    
    # Apply filters
    filtered_data = request_data.copy()
    
    if status_filter != "All":
        if status_filter == "Pending":
            filtered_data = [row for row in filtered_data if "⏳" in row.get("Overall Status", "")]
        elif status_filter == "Approved":
            filtered_data = [row for row in filtered_data if "✅" in row.get("Overall Status", "")]
        elif status_filter == "Rejected":
            filtered_data = [row for row in filtered_data if "❌" in row.get("Overall Status", "")]
    
    if type_filter != "All":
        filtered_data = [row for row in filtered_data if type_filter in row.get("Request Type", "")]
    
    if search_request_id:
        filtered_data = [row for row in filtered_data if search_request_id.lower() in row.get("Request ID", "").lower()]
    
    st.markdown("---")
    
    # Table title
    st.write("**Your Requests**")
    
    # Create DataFrame and display table
    if filtered_data:
        # Remove "Source" column from the data
        display_data = []
        for row in filtered_data:
            display_row = {k: v for k, v in row.items() if k != "Source"}
            display_data.append(display_row)
        
        df = pd.DataFrame(display_data)
        
        # Custom CSS for table styling
        st.markdown("""
        <style>
        .dataframe {
            font-family: Arial, sans-serif;
            border-collapse: collapse;
            width: 100%;
        }
        .dataframe th {
            background-color: #f8f9fa;
            color: #495057;
            font-weight: bold;
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        .dataframe td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #f8f9fa;
        }
        .dataframe tr:hover {
            background-color: #f8f9fa;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display the table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Request ID": st.column_config.TextColumn("Request ID", width="medium"),
                "Request Type": st.column_config.TextColumn("Request Type", width="medium"),
                "L1 Status": st.column_config.TextColumn("L1 Status", width="small"),
                "L2 Status": st.column_config.TextColumn("L2 Status", width="small"),
                "L3 Status": st.column_config.TextColumn("L3 Status", width="small"),
                "L4 Status": st.column_config.TextColumn("L4 Status", width="small"),
                "L5 Status": st.column_config.TextColumn("L5 Status", width="small"),
                "Overall Status": st.column_config.TextColumn("Overall Status", width="medium"),
                "Created At": st.column_config.TextColumn("Created At", width="medium")
            }
        )
    else:
        st.info("No requests found matching the selected filters.")
    
    # Add some spacing at the bottom
    st.markdown("<br><br>", unsafe_allow_html=True)
