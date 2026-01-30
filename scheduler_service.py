from apscheduler.schedulers.background import BackgroundScheduler
from models import Session, Job, DailyLog, JobStatus
from scraper import scrape_jobs
from notifications import send_email_notification
from calendar_integration import create_calendar_note
from data_export import export_jobs_to_excel
import datetime
import atexit

def drip_feed_process():
    print("Running Drip Feed Process...")
    session = Session()
    try:
        today = datetime.date.today()
        log = session.query(DailyLog).filter_by(date=today).first()
        
        if not log:
            log = DailyLog(date=today, count=0)
            session.add(log)
            session.commit()
            # refetch to be safe
            log = session.query(DailyLog).filter_by(date=today).first()

        if log.count >= 2:
            print("Daily limit reached. No notifications sent.")
            return

        # Get top 1 NEW job
        # Prioritize by score then date
        job = session.query(Job).filter(Job.status == JobStatus.NEW)\
            .order_by(Job.match_score.desc(), Job.posted_date.desc()).first()

        if job:
            print(f"Processing job: {job.title}")
            
            # Send Email
            email_sent = send_email_notification(job.title, job.company, job.url)
            
            # Add to Calendar
            cal_added = create_calendar_note(job.title, job.url)
            
            if email_sent or cal_added:
                job.status = JobStatus.NOTIFIED
                log.count += 1
                session.commit()
                print("Job notified and status updated.")
            else:
                print("Falied to notify, keeping status as NEW.")
        else:
            print("No NEW jobs to process.")

    except Exception as e:
        print(f"Error in drip_feed: {e}")
    finally:
        session.close()

def scheduled_job_sequence():
    """Runs scrape then export"""
    scrape_jobs()
    export_jobs_to_excel()

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Scrape AND Export every 30 minutes
    scheduler.add_job(func=scheduled_job_sequence, trigger="interval", minutes=30)
    # Check for drip feed every 60 minutes
    scheduler.add_job(func=drip_feed_process, trigger="interval", minutes=60)
    
    scheduler.start()
    print("Scheduler started...")
    atexit.register(lambda: scheduler.shutdown())
    return scheduler
