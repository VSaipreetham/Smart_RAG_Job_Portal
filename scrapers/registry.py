from .ats_scrapers import GreenhouseScraper, LeverScraper
from .base import BaseScraper
from .extra_scrapers import RemoteOKScraper, GoogleJobsScraper
from .linkedin_scraper import LinkedInScraper
from .naukri_scraper import NaukriScraper
from .api_scrapers import RemotiveScraper, HackerNewsScraper
import requests
from bs4 import BeautifulSoup
import datetime
from models import Job, JobStatus

# Configuration for Multi-Portal Scraping
TARGETS = [
    # --- GREENHOUSE ---
    {"type": "greenhouse", "id": "github"},
    {"type": "greenhouse", "id": "gitlab"},
    {"type": "greenhouse", "id": "twitch"},
    {"type": "greenhouse", "id": "pinterest"},
    {"type": "greenhouse", "id": "stripe"},
    {"type": "greenhouse", "id": "airbnb"},
    {"type": "greenhouse", "id": "dropbox"},
    {"type": "greenhouse", "id": "discord"},
    {"type": "greenhouse", "id": "canonical"},
    {"type": "greenhouse", "id": "doordash"}, # New
    {"type": "greenhouse", "id": "uber"},     # New
    {"type": "greenhouse", "id": "lyft"},     # New
    {"type": "greenhouse", "id": "instacart"},# New
    {"type": "greenhouse", "id": "reddit"},   # New
    {"type": "greenhouse", "id": "grammarly"},# New
    {"type": "greenhouse", "id": "rubrik"},   # New
    {"type": "greenhouse", "id": "cruise"},   # New
    {"type": "greenhouse", "id": "block"},    # New (Square)
    {"type": "greenhouse", "id": "affirm"},   # New

    # --- LEVER ---
    {"type": "lever", "id": "netflix"},
    {"type": "lever", "id": "spotify"},
    {"type": "lever", "id": "atlassian"},
    {"type": "lever", "id": "palantir"},
    {"type": "lever", "id": "udemy"},
    {"type": "lever", "id": "figma"},
    {"type": "lever", "id": "plaid"},       # New
    {"type": "lever", "id": "notion"},      # New
    {"type": "lever", "id": "linear"},      # New
    {"type": "lever", "id": "chanzuckerberg"}, # New
    {"type": "lever", "id": "scale"},       # New
]

class WWRScraper(BaseScraper):
    def scrape(self):
        print("Scraping We Work Remotely...")
        try:
            url = "https://weworkremotely.com/categories/remote-back-end-programming-jobs"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            nodes = soup.select('section.jobs li a')
            for node in nodes:
                if 'view-all' in node.get('class', []): continue
                
                title_tag = node.find(class_='title')
                company_tag = node.find(class_='company')
                region_tag = node.find(class_='region')
                
                if not title_tag or not company_tag: continue
                
                title = title_tag.get_text(strip=True)
                company = company_tag.get_text(strip=True)
                # Region is usually location
                location = region_tag.get_text(strip=True) if region_tag else "Remote"
                
                href = node['href']
                full_url = f"https://weworkremotely.com{href}"
                
                self.save_job(title, company, full_url, "WeWorkRemotely", location=location)
            
            self.session.commit()
        except Exception as e:
            print(f"Error scraping WWR: {e}")

from models import Session # Import Session factory
import concurrent.futures

def scrape_wrapper(scraper_class, *args):
    """Helper to run a scraper in its own DB session"""
    session = Session()
    try:
        scraper = scraper_class(session, *args)
        scraper.scrape()
        # Safety commit: In case the scraper forgot to commit, we do it here.
        # If it already committed, this is a no-op or harmless.
        session.commit()
    except Exception as e:
        print(f"Error in {scraper_class.__name__}: {e}")
        session.rollback()
    finally:
        session.close()

def run_all_scrapers(legacy_session_ignored=None):
    """
    Runs all scrapers in parallel. 
    Ignores the passed session (if any) to enforce thread-safety with new sessions.
    """
    print(f"Starting parallel scrape with ~{len(TARGETS)+7} workers...")
    
    # We use a large thread pool to run almost everything at once
    # Since these are IO-bound net requests, more threads is fine
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = []
        
        # 1. Standard Boards
        futures.append(executor.submit(scrape_wrapper, LinkedInScraper))
        futures.append(executor.submit(scrape_wrapper, NaukriScraper))
        futures.append(executor.submit(scrape_wrapper, RemotiveScraper))
        futures.append(executor.submit(scrape_wrapper, HackerNewsScraper))
        futures.append(executor.submit(scrape_wrapper, WWRScraper))
        futures.append(executor.submit(scrape_wrapper, RemoteOKScraper))
        futures.append(executor.submit(scrape_wrapper, GoogleJobsScraper))
        
        # 2. ATS Targets
        for t in TARGETS:
            if t['type'] == 'greenhouse':
                futures.append(executor.submit(scrape_wrapper, GreenhouseScraper, t['id']))
            elif t['type'] == 'lever':
                futures.append(executor.submit(scrape_wrapper, LeverScraper, t['id']))
        
        # Wait for all
        concurrent.futures.wait(futures)
        print("All parallel scrapers finished.")
