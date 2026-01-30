import streamlit as st
import pandas as pd
from models import Session, Job, JobStatus, engine
from scraper import scrape_jobs
from data_export import export_jobs_to_excel
from scheduler_service import start_scheduler
from notifications import send_email_notification
from calendar_integration import create_calendar_note

import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables


# Page Config
st.set_page_config(page_title="Smart Job Portal", layout="wide")

if 'scheduler_started' not in st.session_state:
    try:
        start_scheduler()
        st.session_state['scheduler_started'] = True
    except:
        pass 

def get_session():
    return Session()

st.title("🚀 Smart Job Portal V3")

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔎 Search & Filters")
search_query = st.sidebar.text_input("Keywords (Title/Company)")
location_filter = st.sidebar.text_input("Location")

# Dynamic Source Filter
session = get_session()
# Get unique sources for multiselect
sources = [r[0] for r in session.query(Job.source).distinct()]
source_filter = st.sidebar.multiselect("Filter by Source", sources, default=[])
date_sort = st.sidebar.selectbox("Sort By Date", ["Newest First", "Oldest First"])

# Stats
new_count = session.query(Job).filter(Job.status.in_([JobStatus.NEW, JobStatus.QUEUED])).count()
notified_count = session.query(Job).filter(Job.status == JobStatus.NOTIFIED).count()
archived_count = session.query(Job).filter(Job.status == JobStatus.ARCHIVED).count()

col1, col2, col3, col4 = st.columns(4)
col1.metric("New Jobs", new_count)
col2.metric("Notified Jobs", notified_count)
col3.metric("Archived", archived_count)

if col4.button("🔄 Manual Scrape"):
    with st.spinner("Scraping..."):
        scrape_jobs()
        export_jobs_to_excel()
    st.success("Scrape & Export Complete!")
    st.rerun()

if os.path.exists("jobs_list.xlsx"):
    with open("jobs_list.xlsx", "rb") as file:
        st.sidebar.download_button(
            label="📥 Download Excel",
            data=file,
            file_name="jobs_list.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- AI COACH INTEGRATION ---
try:
    from ai_service import get_ai_coach, extract_text_from_pdf
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

if 'ai_coach' not in st.session_state and AI_AVAILABLE:
    coach = get_ai_coach()
    # Set Gemini Key from .env
    gemini_key = os.getenv("Google_token")
    if gemini_key:
        coach.set_gemini_key(gemini_key)
    else:
        st.toast("⚠️ Google_token not found in .env via os.getenv")
    
    st.session_state['ai_coach'] = coach

# --- MAIN TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📥 Inbox", "🚀 My Applications", "📊 Analytics", "📜 History", "🗑️ Archived", "🤖 AI Career Coach"])

with tab1:
    st.subheader("Inbox (New Jobs)")
    
    # Filter Logic
    query = session.query(Job).filter(Job.status.in_([JobStatus.NEW, JobStatus.QUEUED]))
    if source_filter:
        query = query.filter(Job.source.in_(source_filter))
    if location_filter:
        query = query.filter(Job.location.ilike(f"%{location_filter}%"))
    if search_query:
        query = query.filter(
            (Job.title.ilike(f"%{search_query}%")) |
            (Job.company.ilike(f"%{search_query}%"))
        )
        
    jobs = query.order_by(Job.posted_date.desc()).limit(200).all()
    
    if jobs:
        with st.form("process_jobs"):
            data = []
            for j in jobs:
                data.append({
                    "id": j.id,
                    "Select": False,
                    "Title": j.title,
                    "Company": j.company,
                    "Location": j.location,
                    "Source": j.source, 
                    "URL": j.url,
                    "Posted Date": j.posted_date
                })
            
            df = pd.DataFrame(data)
            edited_df = st.data_editor(df, column_config={
                "Select": st.column_config.CheckboxColumn("Select", default=False),
                "URL": st.column_config.LinkColumn("Link"),
                "Posted Date": st.column_config.DatetimeColumn("Posted Date", format="D MMM YYYY, h:mm a"),
                "Source": st.column_config.TextColumn("Source")
            }, disabled=["id", "Title", "Company", "Location", "Source", "URL", "Posted Date"], hide_index=True)
            
            c1, c2, c3 = st.columns([1, 1, 4])
            with c1:
                apply_btn = st.form_submit_button("🚀 Mark Applied")
            with c2:
                archive_btn = st.form_submit_button("🗑️ Archive")
            
            if apply_btn:
                selected_rows = edited_df[edited_df["Select"] == True]
                for index, row in selected_rows.iterrows():
                    job = session.query(Job).get(row['id'])
                    job.status = JobStatus.APPLIED
                session.commit()
                st.success(f"Moved {len(selected_rows)} jobs to Applications!")
                st.rerun()

            if archive_btn:
                selected_rows = edited_df[edited_df["Select"] == True]
                for index, row in selected_rows.iterrows():
                    job = session.query(Job).get(row['id'])
                    job.status = JobStatus.ARCHIVED
                session.commit()
                st.success("Archived.")
                st.rerun()
    else:
        st.info("No jobs found matching filters.")

with tab2:
    st.subheader("My Application Tracker")
    apps = session.query(Job).filter(Job.status.in_([JobStatus.APPLIED, JobStatus.INTERVIEW, JobStatus.OFFER, JobStatus.REJECTED])).order_by(Job.posted_date.desc()).all()
    
    if apps:
        for job in apps:
            with st.expander(f"{job.title} @ {job.company} ({job.status.value.upper()})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Source:** {job.source}")
                    st.write(f"**Location:** {job.location}")
                    st.write(f"**Pay:** {job.pay}")
                    st.markdown(f"[Job Link]({job.url})")
                    
                    # Notes Field
                    new_note = st.text_area("My Notes", value=job.notes if job.notes else "", key=f"note_{job.id}")
                    if st.button("Save Note", key=f"savenote_{job.id}"):
                        job.notes = new_note
                        session.commit()
                        st.success("Saved!")
                
                with c2:
                    st.write("Update Status:")
                    s1, s2, s3, s4 = st.columns(4)
                    if s1.button("Applied", key=f"st_app_{job.id}"): 
                        job.status = JobStatus.APPLIED
                        session.commit()
                        st.rerun()
                    if s2.button("Interview", key=f"st_int_{job.id}"): 
                        job.status = JobStatus.INTERVIEW
                        session.commit()
                        st.rerun()
                    if s3.button("Offer", key=f"st_off_{job.id}"): 
                        job.status = JobStatus.OFFER
                        session.commit()
                        st.rerun()
                    if s4.button("Reject", key=f"st_rej_{job.id}"): 
                        job.status = JobStatus.REJECTED
                        session.commit()
                        st.rerun()
    else:
        st.info("No active applications yet. Go to Inbox and 'Mark Applied'!")

with tab3:
    st.subheader("Job Market Insights")
    
    # Analytics Queries
    df_all = pd.read_sql(session.query(Job).statement, session.bind)
    
    if not df_all.empty:
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### Jobs by Source")
            source_counts = df_all['source'].value_counts()
            st.bar_chart(source_counts)
            
        with c2:
            st.markdown("#### Jobs by Status")
            status_counts = df_all['status'].value_counts()
            # Convert Enum to string for chart
            st.bar_chart(status_counts.astype(str))
            
        st.markdown("#### Top Companies Hiring (Top 20)")
        company_counts = df_all['company'].value_counts().head(20)
        st.bar_chart(company_counts)
    else:
        st.warning("No data for analytics.")

with tab4:
    st.subheader("Notification History")
    history = session.query(Job).filter(Job.status == JobStatus.NOTIFIED).order_by(Job.posted_date.desc()).all()
    
    fdata = []
    for j in history:
        fdata.append({
            "Title": j.title,
            "Company": j.company,
            "Source": j.source,
            "Posted Date": j.posted_date,
            "URL": j.url
        })
    if fdata:
        st.dataframe(fdata, column_config={"URL": st.column_config.LinkColumn("Link")}, hide_index=True)
    else:
        st.info("No history.")

with tab5:
    st.subheader("Archived Jobs")
    archived = session.query(Job).filter(Job.status == JobStatus.ARCHIVED).order_by(Job.posted_date.desc()).limit(100).all()
    
    adata = []
    for j in archived:
        adata.append({
            "Title": j.title,
            "Company": j.company,
            "Source": j.source,
            "URL": j.url
        })
    if adata:
        st.dataframe(adata, column_config={"URL": st.column_config.LinkColumn("Link")}, hide_index=True)
    else:
        st.info("Trash is empty.")

with tab6:
    st.header("🤖 AI Career Coach")
    
    if not AI_AVAILABLE:
        st.warning("AI features require additional libraries. Please install: `pip install sentence-transformers transformers torch pdfplumber`")
    else:
        coach = st.session_state.get('ai_coach')
        
        col_ai_1, col_ai_2 = st.columns([1, 1])
        
        with col_ai_1:
            st.subheader("📄 Resume Analysis")
            uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
            
            if uploaded_file is not None:
                if 'resume_text' not in st.session_state:
                    with st.spinner("Parsing Resume..."):
                        text = extract_text_from_pdf(uploaded_file)
                        st.session_state['resume_text'] = text
                        st.success("Resume Parsed!")
                
                st.text_area("Extracted Resume (Preview)", st.session_state['resume_text'][:500] + "...", height=150)
                
                if st.button("🔍 Find Best Job Matches"):
                    if coach:
                        with st.spinner("Analyzing DB against Resume..."):
                            # Get all open jobs
                            open_jobs = session.query(Job).filter(Job.status.in_([JobStatus.NEW, JobStatus.QUEUED, JobStatus.APPLIED])).all()
                            
                            scored_jobs = []
                            try:
                                scored_jobs = coach.batch_rank_jobs(st.session_state['resume_text'], open_jobs)
                                st.session_state['ai_matches'] = scored_jobs[:10] # Top 10
                            except Exception as e:
                                st.error(f"Error ranking jobs: {e}")

                            # Remove progress bar as batch is fast

                            
            if 'ai_matches' in st.session_state:
                st.write("### 🎯 Top 10 Matches")
                for job, score in st.session_state['ai_matches']:
                    with st.expander(f"{int(score*100)}% Match: {job.title} @ {job.company}"):
                        st.write(f"**Source**: {job.source}")
                        st.write(f"**Location**: {job.location}")
                        st.markdown(f"[Job Link]({job.url})")
                        if st.button("💡 Get Advice", key=f"advise_{job.id}"):
                            st.session_state['target_job_for_advice'] = job

        with col_ai_2:
            st.subheader("💬 AI Career Advisor")
            
            if 'target_job_for_advice' in st.session_state:
                target = st.session_state['target_job_for_advice']
                st.info(f"Analyzing: **{target.title}** at **{target.company}**")
                
                if st.button("📝 Analyze Missing Skills"):
                    if coach and 'resume_text' in st.session_state:
                        with st.spinner("Generating Advice (LLM)..."):
                            # Mock description for now since we don't scrape it
                            # In real world, we would fetch URL here
                            job_desc_proxy = f"{target.title} role at {target.company} involving {target.source} technologies in {target.location}."
                            advice = coach.get_advice(st.session_state['resume_text'], job_desc_proxy)
                            st.markdown(advice)
            
            st.divider()
            user_q = st.text_input("Ask your AI Career Companion:")
            if user_q and st.button("Ask Companion"):
                if coach:
                    # Context Building
                    context = ""
                    if 'resume_text' in st.session_state:
                         context += f"User's Resume:\n{st.session_state['resume_text']}\n"
                    if 'target_job_for_advice' in st.session_state:
                         tgt = st.session_state['target_job_for_advice']
                         context += f"Target Job: {tgt.title} at {tgt.company}\nLocation: {tgt.location}\nSource: {tgt.source}"

                    with st.spinner("Companion is thinking..."):
                        ans = coach.ask_coach(user_q, context=context)
                        st.markdown(f"**Companion:**\n\n{ans}")

# Close session
session.close()

# --- LOG VIEWER (Bottom Expander) ---
with st.expander("🛠️ System Logs & Debugging"):
    # Simple hack to show file activity if we were logging to file, 
    # for now we show connectivity status
    st.write("Database: Connected (jobs_v4.db)")
    st.write(f"Scraper Workers: 15 Threads")
    st.write(f"Total Jobs in DB: {new_count + notified_count + archived_count}")


session.close()
