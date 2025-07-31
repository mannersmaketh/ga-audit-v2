# GA4 Audit V2

A comprehensive Google Analytics 4 audit tool that provides detailed insights into your GA4 property's performance and data quality, with automatic export to Google Sheets.

## 🚀 Features

### 1. Sessions and Users Analysis (Last 90 Days)
- **Total Sessions**: Complete session count from the last 90 days
- **Total Users**: Unique user count from the last 90 days  
- **Sessions per User**: Calculated ratio showing user engagement

### 2. Unassigned Traffic Analysis
- **Unassigned Sessions**: Total sessions from unassigned traffic channel
- **Percent of Total**: Percentage of unassigned sessions vs total sessions
- **Session Medium Breakdown**: Detailed breakdown of session mediums under unassigned traffic

### 3. Transactions and Revenue Analysis
- **Total Transactions**: Complete transaction count from last 90 days
- **Total Revenue**: Total revenue generated in the last 90 days
- **Duplicate Transaction Detection**: Identifies transaction IDs with more than 1 transaction

### 4. Conversion Funnel Analysis
- **View Item Events**: Total count of view_item events
- **Add to Cart Events**: Total count of add_to_cart events
- **Begin Checkout Events**: Total count of begin_checkout events
- **Purchase Events**: Total count of purchase events
- **Funnel Conversion Rates**: Calculated conversion rates between funnel stages

### 5. 📊 Google Sheets Integration
- **Automatic Export**: Push audit results directly to Google Sheets
- **Formatted Reports**: Clean, organized data with proper formatting
- **Real-time Updates**: Instant data transfer to your chosen spreadsheet
- **Multiple Export Options**: Choose between Google Sheets or CSV download

## 🔐 Authentication

The app uses OAuth 2.0 to securely connect to your Google Analytics and Google Sheets accounts. You'll need to:

1. Set up a Google Cloud Project
2. Enable the Google Analytics Data API and Google Sheets API
3. Create OAuth 2.0 credentials with the required scopes
4. Configure the redirect URI

### Required Scopes
- **Google Analytics**: `https://www.googleapis.com/auth/analytics.readonly`, `https://www.googleapis.com/auth/analytics.manage.users.readonly`, `https://www.googleapis.com/auth/analytics.edit`
- **Google Sheets**: `https://www.googleapis.com/auth/spreadsheets`, `https://www.googleapis.com/auth/drive`

## 📊 Data Requirements

The audit analyzes data from the last 90 days and requires access to:
- Google Analytics 4 property data
- Google Sheets for export functionality (optional)

## 🛠️ Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your Streamlit secrets with your Google OAuth credentials:
   ```toml
   [secrets]
   client_id = "your-oauth-client-id"
   client_secret = "your-oauth-client-secret"
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## 📈 Key Insights

The app provides automated insights including:
- **Low sessions per user** warnings
- **High unassigned traffic** alerts
- **Duplicate transaction** detection
- **Missing purchase events** identification

## 📥 Export Options

### Google Sheets Export
1. **Authenticate**: Click "Authenticate Google Sheets" in the sidebar
2. **Provide URL**: Paste your Google Sheets URL in the sidebar
3. **Run Audit**: Execute the audit and click "Push to Google Sheets"
4. **View Results**: Data will be automatically formatted and pushed to a new worksheet

### CSV Download
- Download comprehensive audit results as a timestamped CSV file
- Includes all metrics, funnel data, and detailed breakdowns

## 🔄 Version History

### V2 Changes
- Complete redesign of data analysis focus
- New funnel analysis capabilities
- Enhanced transaction tracking
- Improved unassigned traffic insights
- **NEW**: Google Sheets integration for automatic export
- Better visualization and reporting

### V1 Features (Legacy)
- Configuration audits
- Device mix analysis
- Conversion rate consistency
- Top events analysis

## 🚀 Getting Started with Google Sheets Export

1. **First Time Setup**:
   - Click "Authenticate Google Sheets" in the sidebar
   - Grant permissions to access your Google Sheets
   - You'll be redirected back to the app

2. **For Each Audit**:
   - Paste your Google Sheets URL in the sidebar
   - Run the GA4 audit
   - Click "Push to Google Sheets" to export results

3. **Sheet Format**:
   - Creates a new worksheet called "GA4 Audit V2"
   - Includes timestamp and organized sections
   - Automatically formats headers and data