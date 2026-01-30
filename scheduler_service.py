from apscheduler.schedulers.background import BackgroundScheduler
from models import Session, Job, DailyLog, JobStatus
from scraper import scrape_jobs
from notifications import send_email_notification
from calendar_integration import create_calendar_note
from data_export import export_jobs_to_excel
import datetime
import atexit
import time

def flush_database():
    """Flushes the entire job database for the new day."""
    print(f"[{datetime.datetime.now()}] Flushing database for the new day...")
    session = Session()
    try:
        # Delete all jobs
        num_jobs = session.query(Job).delete()
        
        # Reset daily logs for a fresh start (optional, but requested "start new")
        session.query(DailyLog).delete()
        
        session.commit()
        print(f"[{datetime.datetime.now()}] Database flushed. {num_jobs} jobs deleted. Log cleaned.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error flushing database: {e}")
        session.rollback()
    finally:
        session.close()

def drip_feed_process():
    print(f"[{datetime.datetime.now()}] Running Drip Feed Process...")
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
    print(f"[{datetime.datetime.now()}] Starting scheduled sequence...")
    try:
        scrape_jobs()
        export_jobs_to_excel()
        print(f"[{datetime.datetime.now()}] Scheduled sequence completed.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error in scheduled_job_sequence: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Scrape AND Export every 30 minutes.
    # Removed next_run_time to prevent double-execution on restarts, since app.py handles initial load.
    scheduler.add_job(
        func=scheduled_job_sequence, 
        trigger="interval", 
        minutes=10
    )
    # Check for drip feed every 60 minutes
    scheduler.add_job(func=drip_feed_process, trigger="interval", minutes=60)
    
    # Flush database every day at midnight (00:00)
    scheduler.add_job(func=flush_database, trigger="cron", hour=0, minute=0)
    
    scheduler.start()
    print(f"[{datetime.datetime.now()}] Scheduler started...")
    atexit.register(lambda: scheduler.shutdown())
    return scheduler

