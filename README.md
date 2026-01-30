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

3. **RAG Based AI Companion and Resume Upload Vector Based Job Match**:
    - AI Companion helps to interact and suggest skills and makes improvement in our career and also helps to find the suitable job search 
    - You can Upload the resume here to retrive the job based on your skillset and position


4. **Application Portal**
<img width="1874" height="891" alt="image" src="https://github.com/user-attachments/assets/1f474edf-a199-4f1c-bc5a-ba720187058c" />

5. **Filter Search**

<img width="1910" height="805" alt="image" src="https://github.com/user-attachments/assets/f4699b18-786a-4c35-823e-82ec4f160d95" />

6. **Source Search**
<img width="1913" height="550" alt="image" src="https://github.com/user-attachments/assets/9a839f53-1eaf-4569-9866-dcc28fbf4cc7" />


5. **AI Based Companion**

<img width="1537" height="843" alt="image" src="https://github.com/user-attachments/assets/5f416f14-2608-43e0-9cd6-60244cd222b9" />


7. **Resume Upload and Missing Skills**
<img width="1896" height="930" alt="image" src="https://github.com/user-attachments/assets/7480f802-3664-428d-a1d8-afbb79267d5f" />



