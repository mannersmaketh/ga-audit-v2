import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
import requests
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import re

# --------------- CONFIG ---------------
# Check if secrets are configured
try:
    client_id = st.secrets["client_id"]
    client_secret = st.secrets["client_secret"]
except KeyError:
    st.error("""
    ## 🔧 OAuth Credentials Not Configured
    
    This app requires Google OAuth credentials to access Google Analytics and Google Sheets.
    
    ### To set up your credentials:
    
    1. **Create a Google Cloud Project** at https://console.cloud.google.com/
    2. **Enable the APIs**:
       - Google Analytics Data API
       - Google Sheets API
    3. **Create OAuth 2.0 credentials**:
       - Go to "APIs & Services" > "Credentials"
       - Click "Create Credentials" > "OAuth 2.0 Client IDs"
       - Set application type to "Web application"
       - Add authorized redirect URI: `https://ga-audit-v2.streamlit.app`
    4. **Configure Streamlit secrets**:
       - In your Streamlit Cloud app settings
       - Add the following to your secrets:
       ```toml
       [secrets]
       client_id = "your-oauth-client-id"
       client_secret = "your-oauth-client-secret"
       ```
    
    ### For local development:
    Create a `.streamlit/secrets.toml` file with the above configuration.
    """)
    st.stop()

redirect_uri = "https://ga-audit-v2-8ggow5j56ek8ry7q5prvfi.streamlit.app"
authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
token_url = "https://oauth2.googleapis.com/token"
scope = "https://www.googleapis.com/auth/analytics.readonly https://www.googleapis.com/auth/analytics.manage.users.readonly https://www.googleapis.com/auth/analytics.edit"

# Google Sheets scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

st.set_page_config(page_title="GA4 Audit V2", layout="wide")
st.title("📊 GA4 Audit V2 - Executive Report")

# --------------- SPREADSHEET URL INPUT ---------------
st.markdown("### 📊 Google Sheets Export Setup")
st.markdown("Enter your Google Sheets URL below to automatically export audit results:")

sheet_url = st.text_input(
    "Google Sheets URL",
    placeholder="https://docs.google.com/spreadsheets/d/...",
    help="Paste the URL of the Google Sheet where you want the results to be exported. A new sheet will be created for each audit."
)

if sheet_url:
    st.success("✅ Google Sheets URL configured")
else:
    st.info("ℹ️ You can still run the audit and download CSV results without configuring Google Sheets")

st.markdown("---")

# --------------- GOOGLE SHEETS AUTH ---------------
def get_google_sheets_auth():
    """Handle Google Sheets authentication"""
    if 'sheets_creds' not in st.session_state:
        st.session_state.sheets_creds = None
    
    # Check if we have valid credentials
    if st.session_state.sheets_creds and st.session_state.sheets_creds.valid:
        return st.session_state.sheets_creds
    
    # Check if we have expired credentials that can be refreshed
    if st.session_state.sheets_creds and st.session_state.sheets_creds.expired and st.session_state.sheets_creds.refresh_token:
        try:
            st.session_state.sheets_creds.refresh(Request())
            return st.session_state.sheets_creds
        except:
            st.session_state.sheets_creds = None
    
    return None

def authenticate_google_sheets():
    """Authenticate with Google Sheets using OAuth2"""
    sheets_oauth = OAuth2Session(
        client_id, 
        redirect_uri=redirect_uri, 
        scope="https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive"
    )
    auth_url, state = sheets_oauth.create_authorization_url(authorize_url)
    st.session_state["sheets_oauth_state"] = state
    
    # Create a clickable link for Google Sheets auth
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <a href="{auth_url}" target="_self" style="
            display: inline-block;
            background-color: #4285f4;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            font-size: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        ">
            📊 Connect Google Sheets
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("Click the button above to connect your Google Sheets account for automatic export functionality.")
    st.stop()

def extract_sheet_id_from_url(url):
    """Extract sheet ID from Google Sheets URL"""
    # Pattern for Google Sheets URL
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def push_to_google_sheet(sheet_url, audit_data, funnel_data, unassigned_mediums, duplicate_transaction_ids):
    """Push audit results to Google Sheet"""
    try:
        # Extract sheet ID from URL
        sheet_id = extract_sheet_id_from_url(sheet_url)
        if not sheet_id:
            st.error("❌ Invalid Google Sheets URL. Please provide a valid Google Sheets URL.")
            return False, None
        
        # Get authenticated client
        creds = get_google_sheets_auth()
        if not creds:
            st.error("❌ Google Sheets authentication required. Please authenticate first.")
            return False, None
        
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        try:
            spreadsheet = client.open_by_key(sheet_id)
        except gspread.SpreadsheetNotFound:
            st.error("❌ Spreadsheet not found. Please check the URL and ensure you have edit access.")
            return False, None
        except gspread.APIError as e:
            st.error(f"❌ Google Sheets API error: {e}")
            return False, None
        
        # Create a new worksheet with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sheet_name = f"GA4 Audit V2 - {timestamp}"
        
        try:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=10)
        except gspread.WorksheetNotFound:
            # Fallback if add_worksheet fails
            worksheet = spreadsheet.worksheet("Sheet1")
            worksheet.clear()
            worksheet.update('A1', f'GA4 Audit V2 - {timestamp}')
        
        # Prepare data for Google Sheets
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Header
        worksheet.update('A1', f'GA4 Audit V2 Results - {sheet_name}')
        worksheet.update('A2', f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        worksheet.update('A3', '')
        
        # Section 1: Sessions and Users
        worksheet.update('A4', '1. SESSIONS AND USERS ANALYSIS (Last 90 Days)')
        worksheet.update('A5', 'Metric')
        worksheet.update('B5', 'Value')
        
        row = 6
        worksheet.update(f'A{row}', 'Total Sessions')
        worksheet.update(f'B{row}', audit_data['total_sessions'])
        row += 1
        worksheet.update(f'A{row}', 'Total Users')
        worksheet.update(f'B{row}', audit_data['total_users'])
        row += 1
        worksheet.update(f'A{row}', 'Sessions per User')
        worksheet.update(f'B{row}', audit_data['sessions_per_user'])
        row += 2
        
        # Section 2: Unassigned Traffic
        worksheet.update(f'A{row}', '2. UNASSIGNED TRAFFIC ANALYSIS')
        row += 1
        worksheet.update(f'A{row}', 'Unassigned Sessions')
        worksheet.update(f'B{row}', audit_data['unassigned_sessions'])
        row += 1
        worksheet.update(f'A{row}', 'Percent of Total Sessions')
        worksheet.update(f'B{row}', f"{audit_data['percent_unassigned']}%")
        row += 1
        
        if unassigned_mediums:
            worksheet.update(f'A{row}', 'Session Medium Breakdown (Unassigned):')
            row += 1
            for medium_data in unassigned_mediums:
                worksheet.update(f'A{row}', f"- {medium_data['medium']}")
                worksheet.update(f'B{row}', medium_data['sessions'])
                row += 1
        row += 1
        
        # Section 3: Transactions and Revenue
        worksheet.update(f'A{row}', '3. TRANSACTIONS AND REVENUE ANALYSIS')
        row += 1
        worksheet.update(f'A{row}', 'Total Transactions')
        worksheet.update(f'B{row}', audit_data['total_transactions'])
        row += 1
        worksheet.update(f'A{row}', 'Total Revenue')
        worksheet.update(f'B{row}', f"${audit_data['total_revenue']:,.2f}")
        row += 1
        
        if duplicate_transaction_ids:
            worksheet.update(f'A{row}', 'Duplicate Transaction IDs:')
            row += 1
            for dup_data in duplicate_transaction_ids:
                worksheet.update(f'A{row}', f"- {dup_data['transaction_id']}")
                worksheet.update(f'B{row}', dup_data['count'])
                row += 1
        row += 1
        
        # Section 4: Funnel Analysis
        worksheet.update(f'A{row}', '4. CONVERSION FUNNEL ANALYSIS')
        row += 1
        worksheet.update(f'A{row}', 'View Item Events')
        worksheet.update(f'B{row}', funnel_data['view_item'])
        row += 1
        worksheet.update(f'A{row}', 'Add to Cart Events')
        worksheet.update(f'B{row}', funnel_data['add_to_cart'])
        row += 1
        worksheet.update(f'A{row}', 'Begin Checkout Events')
        worksheet.update(f'B{row}', funnel_data['begin_checkout'])
        row += 1
        worksheet.update(f'A{row}', 'Purchase Events')
        worksheet.update(f'B{row}', funnel_data['purchase'])
        row += 1
        
        # Funnel conversion rates
        if funnel_data['view_item'] > 0:
            view_to_cart = round((funnel_data['add_to_cart'] / funnel_data['view_item']) * 100, 2)
            cart_to_checkout = round((funnel_data['begin_checkout'] / funnel_data['add_to_cart']) * 100, 2) if funnel_data['add_to_cart'] > 0 else 0
            checkout_to_purchase = round((funnel_data['purchase'] / funnel_data['begin_checkout']) * 100, 2) if funnel_data['begin_checkout'] > 0 else 0
            view_to_purchase = round((funnel_data['purchase'] / funnel_data['view_item']) * 100, 2)
            
            row += 1
            worksheet.update(f'A{row}', 'FUNNEL CONVERSION RATES:')
            row += 1
            worksheet.update(f'A{row}', 'View → Cart')
            worksheet.update(f'B{row}', f"{view_to_cart}%")
            row += 1
            worksheet.update(f'A{row}', 'Cart → Checkout')
            worksheet.update(f'B{row}', f"{cart_to_checkout}%")
            row += 1
            worksheet.update(f'A{row}', 'Checkout → Purchase')
            worksheet.update(f'B{row}', f"{checkout_to_purchase}%")
            row += 1
            worksheet.update(f'A{row}', 'View → Purchase')
            worksheet.update(f'B{row}', f"{view_to_purchase}%")
        
        # Format the sheet
        worksheet.format('A1:B1', {'textFormat': {'bold': True, 'fontSize': 14}})
        worksheet.format('A4:A4', {'textFormat': {'bold': True, 'fontSize': 12}})
        worksheet.format('A8:A8', {'textFormat': {'bold': True, 'fontSize': 12}})
        worksheet.format('A12:A12', {'textFormat': {'bold': True, 'fontSize': 12}})
        worksheet.format('A16:A16', {'textFormat': {'bold': True, 'fontSize': 12}})
        
        return True, sheet_name
        
    except Exception as e:
        st.error(f"❌ Error pushing to Google Sheets: {str(e)}")
        return False, None

# --------------- OAUTH FLOW ---------------
if "access_token" not in st.session_state:
    if "code" not in st.query_params:
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        auth_url, state = oauth.create_authorization_url(authorize_url)
        st.session_state["oauth_state"] = state
        
        # Create a clickable link that will redirect in the same tab
        st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <a href="{auth_url}" target="_self" style="
                display: inline-block;
                background-color: #ff4b4b;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            ">
                🔗 Connect Google Analytics
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("Click the button above to connect your Google Analytics account. You'll be redirected to Google's authorization page and then back to this app.")
        st.stop()
    else:
        code = st.query_params["code"]
        oauth = OAuth2Session(client_id, client_secret, redirect_uri=redirect_uri)
        token = oauth.fetch_token(token_url, code=code)
        st.session_state["access_token"] = token["access_token"]

# --------------- GOOGLE SHEETS SETUP ---------------
# Handle Google Sheets OAuth callback
if "sheets_code" in st.query_params and "sheets_oauth_state" in st.session_state:
    sheets_code = st.query_params["sheets_code"]
    sheets_oauth = OAuth2Session(
        client_id, 
        client_secret, 
        redirect_uri=redirect_uri,
        scope="https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive"
    )
    sheets_token = sheets_oauth.fetch_token(token_url, code=sheets_code)
    
    # Convert to Credentials object for gspread
    from google.oauth2.credentials import Credentials
    st.session_state["sheets_creds"] = Credentials(
        token=sheets_token["access_token"],
        refresh_token=sheets_token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )

# Google Sheets authentication
sheets_creds = get_google_sheets_auth()
if not sheets_creds:
    st.warning("⚠️ Google Sheets authentication required for sheet export")
    if st.button("🔐 Authenticate Google Sheets"):
        authenticate_google_sheets()
else:
    st.success("✅ Google Sheets authenticated")

# --------------- RETRIEVE PROPERTIES ---------------
headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
resp = requests.get("https://analyticsadmin.googleapis.com/v1beta/accountSummaries", headers=headers)
summaries = resp.json().get("accountSummaries", [])

options = []
for summary in summaries:
    account = summary.get("displayName", "Unnamed Account")
    for prop in summary.get("propertySummaries", []):
        options.append({
            "label": f"{account} — {prop.get('displayName')} ({prop.get('property')})",
            "id": prop.get("property")
        })

property_labels = [opt["label"] for opt in options]
property_ids = {opt["label"]: opt["id"] for opt in options}
selected_label = st.selectbox("Choose a GA4 Property", property_labels)

# Add Run Audit button
run_audit = False
if selected_label:
    run_audit = st.button("🚀 Run GA4 Audit V2", type="primary")
    
    if run_audit:
        property_id = property_ids[selected_label]
        run_report_url = f"https://analyticsdata.googleapis.com/v1beta/{property_id}:runReport"
        
        # Progress bar for audit process
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Update progress
        status_text.text("🔍 Starting GA4 Audit V2...")
        progress_bar.progress(10)

        def fetch_metric_report(metrics, dimensions=None, filters=None, date_range="90daysAgo"):
            body = {
                "dateRanges": [{"startDate": date_range, "endDate": "today"}],
                "metrics": [{"name": m} for m in metrics]
            }
            if dimensions:
                body["dimensions"] = [{"name": d} for d in dimensions]
            if filters:
                body["dimensionFilter"] = filters

            response = requests.post(run_report_url, headers=headers, json=body)
            try:
                result = response.json()
            except ValueError:
                st.error("❌ Invalid JSON response from GA4 API.")
                st.stop()

            if "error" in result:
                st.error(f"❌ GA4 API error: {result['error'].get('message', 'Unknown error')}")
                st.stop()

            return result

        # ---------- SECTION 1: SESSIONS AND USERS ANALYSIS ----------
        status_text.text("📊 Analyzing Sessions and Users (Last 90 Days)...")
        progress_bar.progress(20)
        
        # Get total sessions and users for last 90 days
        sessions_users_data = fetch_metric_report(["sessions", "totalUsers"])
        
        if "rows" in sessions_users_data and sessions_users_data["rows"]:
            total_sessions = int(sessions_users_data["rows"][0]["metricValues"][0]["value"])
            total_users = int(sessions_users_data["rows"][0]["metricValues"][1]["value"])
            sessions_per_user = round(total_sessions / total_users, 2) if total_users > 0 else 0
        else:
            st.error("❌ Failed to retrieve sessions and users data")
            st.stop()

        # ---------- SECTION 2: UNASSIGNED TRAFFIC ANALYSIS ----------
        status_text.text("🔍 Analyzing Unassigned Traffic...")
        progress_bar.progress(40)
        
        # Get sessions by channel grouping
        channel_data = fetch_metric_report(["sessions"], ["defaultChannelGrouping"])
        
        # Calculate unassigned sessions
        unassigned_sessions = 0
        total_sessions_from_channels = 0
        
        for row in channel_data.get("rows", []):
            channel = row["dimensionValues"][0]["value"]
            sessions_count = int(row["metricValues"][0]["value"])
            total_sessions_from_channels += sessions_count
            if channel == "Unassigned":
                unassigned_sessions = sessions_count
        
        percent_unassigned = round((unassigned_sessions / total_sessions) * 100, 2) if total_sessions > 0 else 0
        
        # Get session medium breakdown for unassigned traffic
        unassigned_medium_data = fetch_metric_report(
            ["sessions"], 
            ["sessionMedium"], 
            filters={"filter": {"fieldName": "defaultChannelGrouping", "stringFilter": {"value": "Unassigned"}}}
        )
        
        unassigned_mediums = []
        for row in unassigned_medium_data.get("rows", []):
            medium = row["dimensionValues"][0]["value"]
            sessions_count = int(row["metricValues"][0]["value"])
            unassigned_mediums.append({"medium": medium, "sessions": sessions_count})

        # ---------- SECTION 3: TRANSACTIONS AND REVENUE ANALYSIS ----------
        status_text.text("💰 Analyzing Transactions and Revenue...")
        progress_bar.progress(60)
        
        # Get total transactions and revenue
        transactions_revenue_data = fetch_metric_report(["transactions", "totalRevenue"])
        
        if "rows" in transactions_revenue_data and transactions_revenue_data["rows"]:
            total_transactions = int(transactions_revenue_data["rows"][0]["metricValues"][0]["value"])
            total_revenue = float(transactions_revenue_data["rows"][0]["metricValues"][1]["value"])
        else:
            total_transactions = 0
            total_revenue = 0
        
        # Get transaction IDs with more than 1 transaction
        transaction_id_data = fetch_metric_report(
            ["transactions"], 
            ["transactionId"], 
            filters={"filter": {"fieldName": "transactions", "numericFilter": {"operation": "GREATER_THAN", "value": {"int64Value": "1"}}}}
        )
        
        duplicate_transaction_ids = []
        for row in transaction_id_data.get("rows", []):
            transaction_id = row["dimensionValues"][0]["value"]
            transaction_count = int(row["metricValues"][0]["value"])
            duplicate_transaction_ids.append({"transaction_id": transaction_id, "count": transaction_count})

        # ---------- SECTION 4: FUNNEL ANALYSIS ----------
        status_text.text("🔄 Analyzing Conversion Funnel...")
        progress_bar.progress(80)
        
        # Get funnel event counts
        funnel_events = ["view_item", "add_to_cart", "begin_checkout", "purchase"]
        funnel_data = {}
        
        for event in funnel_events:
            event_data = fetch_metric_report(
                ["eventCount"], 
                filters={"filter": {"fieldName": "eventName", "stringFilter": {"value": event}}}
            )
            
            if "rows" in event_data and event_data["rows"]:
                funnel_data[event] = int(event_data["rows"][0]["metricValues"][0]["value"])
            else:
                funnel_data[event] = 0

        # ---------- FINAL OUTPUT ----------
        status_text.text("✅ Audit Complete! Generating Report...")
        progress_bar.progress(100)
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Store audit data for export
        audit_data = {
            'total_sessions': total_sessions,
            'total_users': total_users,
            'sessions_per_user': sessions_per_user,
            'unassigned_sessions': unassigned_sessions,
            'percent_unassigned': percent_unassigned,
            'total_transactions': total_transactions,
            'total_revenue': total_revenue
        }
        
        # Display results in organized sections
        st.markdown("## 📊 GA4 Audit V2 Results (Last 90 Days)")
        
        # Section 1: Sessions and Users
        st.markdown("### 1️⃣ Sessions and Users Analysis")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Sessions", f"{total_sessions:,}")
        with col2:
            st.metric("Total Users", f"{total_users:,}")
        with col3:
            st.metric("Sessions per User", f"{sessions_per_user}")
        
        # Section 2: Unassigned Traffic
        st.markdown("### 2️⃣ Unassigned Traffic Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Unassigned Sessions", f"{unassigned_sessions:,}")
            st.metric("Percent of Total", f"{percent_unassigned}%")
        
        with col2:
            if unassigned_mediums:
                st.markdown("**Session Medium Breakdown (Unassigned Traffic):**")
                for medium_data in unassigned_mediums:
                    st.write(f"- **{medium_data['medium']}**: {medium_data['sessions']:,} sessions")
            else:
                st.info("No unassigned traffic found or no medium data available")
        
        # Section 3: Transactions and Revenue
        st.markdown("### 3️⃣ Transactions and Revenue Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Transactions", f"{total_transactions:,}")
            st.metric("Total Revenue", f"${total_revenue:,.2f}")
        
        with col2:
            if duplicate_transaction_ids:
                st.markdown("**Transaction IDs with >1 Transaction:**")
                for dup_data in duplicate_transaction_ids[:10]:  # Show first 10
                    st.write(f"- **{dup_data['transaction_id']}**: {dup_data['count']} transactions")
                if len(duplicate_transaction_ids) > 10:
                    st.write(f"... and {len(duplicate_transaction_ids) - 10} more")
            else:
                st.info("No duplicate transaction IDs found")
        
        # Section 4: Funnel Analysis
        st.markdown("### 4️⃣ Conversion Funnel Analysis")
        
        # Create funnel visualization
        funnel_cols = st.columns(4)
        funnel_labels = ["View Item", "Add to Cart", "Begin Checkout", "Purchase"]
        
        for i, (event, label) in enumerate(zip(funnel_events, funnel_labels)):
            with funnel_cols[i]:
                st.metric(label, f"{funnel_data[event]:,}")
        
        # Funnel conversion rates
        st.markdown("**Funnel Conversion Rates:**")
        if funnel_data["view_item"] > 0:
            view_to_cart = round((funnel_data["add_to_cart"] / funnel_data["view_item"]) * 100, 2)
            cart_to_checkout = round((funnel_data["begin_checkout"] / funnel_data["add_to_cart"]) * 100, 2) if funnel_data["add_to_cart"] > 0 else 0
            checkout_to_purchase = round((funnel_data["purchase"] / funnel_data["begin_checkout"]) * 100, 2) if funnel_data["begin_checkout"] > 0 else 0
            view_to_purchase = round((funnel_data["purchase"] / funnel_data["view_item"]) * 100, 2)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("View → Cart", f"{view_to_cart}%")
            col2.metric("Cart → Checkout", f"{cart_to_checkout}%")
            col3.metric("Checkout → Purchase", f"{checkout_to_purchase}%")
            col4.metric("View → Purchase", f"{view_to_purchase}%")
        
        # ---------- EXPORT OPTIONS ----------
        st.markdown("### 📥 Export Options")
        
        # Google Sheets Export
        if sheet_url and sheet_url.strip():
            if st.button("📊 Push to Google Sheets", type="secondary"):
                with st.spinner("Pushing data to Google Sheets..."):
                    success, sheet_name = push_to_google_sheet(
                        sheet_url, 
                        audit_data, 
                        funnel_data, 
                        unassigned_mediums, 
                        duplicate_transaction_ids
                    )
                    if success:
                        st.success(f"✅ Data successfully pushed to Google Sheets! New sheet: '{sheet_name}'")
                    else:
                        st.error("❌ Failed to push data to Google Sheets. Please check the URL and permissions.")
        
        # CSV Download
        st.markdown("**Or download as CSV:**")
        
        # Prepare data for CSV export
        csv_audit_data = [
            ("Total Sessions (L90)", total_sessions),
            ("Total Users (L90)", total_users),
            ("Sessions per User", sessions_per_user),
            ("Unassigned Sessions (L90)", unassigned_sessions),
            ("Percent Unassigned Sessions", f"{percent_unassigned}%"),
            ("Total Transactions (L90)", total_transactions),
            ("Total Revenue (L90)", total_revenue),
            ("View Item Events", funnel_data["view_item"]),
            ("Add to Cart Events", funnel_data["add_to_cart"]),
            ("Begin Checkout Events", funnel_data["begin_checkout"]),
            ("Purchase Events", funnel_data["purchase"]),
        ]
        
        # Add unassigned medium data
        for medium_data in unassigned_mediums:
            csv_audit_data.append((f"Unassigned - {medium_data['medium']}", medium_data['sessions']))
        
        # Add duplicate transaction IDs
        for dup_data in duplicate_transaction_ids:
            csv_audit_data.append((f"Duplicate Transaction - {dup_data['transaction_id']}", dup_data['count']))

        df_csv = pd.DataFrame(csv_audit_data, columns=["Metric", "Value"])
        csv = df_csv.to_csv(index=False).encode("utf-8")
        
        st.download_button(
            "📊 Download Full Audit Report (CSV)", 
            csv, 
            f"ga4_audit_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
            "text/csv"
        )
        
        # Summary insights
        st.markdown("### 💡 Key Insights")
        
        insights = []
        if sessions_per_user < 1.5:
            insights.append("⚠️ **Low sessions per user** - Consider improving user engagement")
        if percent_unassigned > 20:
            insights.append("⚠️ **High unassigned traffic** - Review UTM parameters and attribution")
        if len(duplicate_transaction_ids) > 0:
            insights.append("⚠️ **Duplicate transactions detected** - Review e-commerce implementation")
        if funnel_data["purchase"] == 0:
            insights.append("⚠️ **No purchase events** - Check e-commerce tracking setup")
        
        if insights:
            for insight in insights:
                st.write(insight)
        else:
            st.success("✅ All metrics look healthy!")
