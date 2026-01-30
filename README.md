# Smart Job Portal

A local job aggregator dashboard with "Drip Feed" notifications.

## Setup

1.  **Install Requirements** (Already done if you see this):
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    - Open `.env` and fill in your Gmail credentials (App Password required).

3.  **Google Calendar Setup**:
    - Go to [Google Cloud Console](https://console.cloud.google.com/).
    - Create a project, enable **Google Calendar API**.
    - Create OAuth 2.0 Credentials (Desktop App).
    - Download the JSON file, rename it to `credentials.json`, and place it in this folder.

## Running the App

1.  **Start the Dashboard**:
    ```bash
    streamlit run app.py
    ```
    This will open the portal in your browser (usually http://localhost:8501).

2.  **Background Processes**:
    - The scraper and scheduler start automatically when `app.py` runs (via a background thread).
    - You can manually trigger a scrape from the dashboard.

## Features

- **Inbox**: View new jobs. Select them to "Process" (send email + add to calendar).
- **History**: View past notifications.
- **Drip Feed**: Automatically processes the top 1 job every hour (max 2 per day) if not manually handled.
