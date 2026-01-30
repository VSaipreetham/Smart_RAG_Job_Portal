import requests
from .base import BaseScraper
import datetime

class GreenhouseScraper(BaseScraper):
    def __init__(self, session, company_token):
        super().__init__(session)
        self.company_token = company_token
        self.api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs"

    def scrape(self):
        print(f"Scraping Greenhouse: {self.company_token}...")
        try:
            resp = requests.get(f"{self.api_url}?content=true")
            if resp.status_code != 200:
                print(f"  [-] Failed to fetch {self.company_token}")
                return

            data = resp.json()
            jobs = data.get('jobs', [])
            
            for j in jobs:
                title = j.get('title')
                url = j.get('absolute_url')
                company = self.company_token.capitalize()
                
                # Extract Location
                loc = j.get('location', {}).get('name')
                
                # Check updated_at
                posted_date = datetime.datetime.utcnow()
                
                # Pay is usually hidden in metadata or description, very unstructured in GH API free tier
                # Metadata might have it
                pay = "N/A"
                if j.get('metadata'):
                    for m in j.get('metadata'):
                        if 'salary' in m.get('name', '').lower() or 'pay' in m.get('name', '').lower():
                            pay = m.get('value')
                            break

                self.save_job(title, company, url, f"Greenhouse-{self.company_token}", location=loc, pay=pay, posted_date=posted_date)
            
            self.session.commit()
            
        except Exception as e:
            print(f"Error scraping greenhouse {self.company_token}: {e}")

class LeverScraper(BaseScraper):
    def __init__(self, session, company_name):
        super().__init__(session)
        self.company_name = company_name
        self.api_url = f"https://api.lever.co/v0/postings/{company_name}?mode=json"

    def scrape(self):
        print(f"Scraping Lever: {self.company_name}...")
        try:
            resp = requests.get(self.api_url)
            if resp.status_code != 200:
                print(f"  [-] Failed to fetch {self.company_name}")
                return

            jobs = resp.json()
            
            for j in jobs:
                title = j.get('text')
                url = j.get('hostedUrl')
                company = self.company_name.capitalize()
                created_at = j.get('createdAt')
                
                posted_date = datetime.datetime.utcnow()
                if created_at:
                    posted_date = datetime.datetime.fromtimestamp(created_at / 1000.0)

                # Location
                loc = j.get('categories', {}).get('location')
                
                # Pay - Lever puts it in "salaryRange" sometimes
                pay = "N/A"
                salary = j.get('salaryRange')
                if salary:
                    min_s = salary.get('min')
                    max_s = salary.get('max')
                    currency = salary.get('currency', '')
                    if min_s and max_s:
                        pay = f"{min_s}-{max_s} {currency}"
                
                self.save_job(title, company, url, f"Lever-{self.company_name}", location=loc, pay=pay, posted_date=posted_date)

            self.session.commit()

        except Exception as e:
            print(f"Error scraping lever {self.company_name}: {e}")
