# -*- coding: utf-8 -*-
"""
Rooster.jobs Web Scraper - CSV + JSON Export
This script scrapes job listings from Rooster.jobs using XPath selectors for precise data extraction
Features:
- XPath-based extraction for Job Type, Location, and Salary
- FIXED: Company name extraction now correctly handles nested elements
- Incremental CSV saving (saves each job immediately)
- JSON export (saves all jobs at the end)
- Smart URL modification to load all jobs at once
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import csv
import json
import os
from datetime import datetime
import time
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class RoosterJobsScraperXPath:
    def __init__(self, url):
        """
        Initialize the scraper with the target URL
        
        Args:
            url (str): The URL to scrape from RoosterJob.txt
        """
        self.base_url = "https://rooster.jobs"
        self.url = url
        self.driver = None
        self.csv_filepath = None
        self.json_filepath = None
        self.csv_file = None
        self.csv_writer = None
        self.jobs_scraped_count = 0
        self.jobs_data = []  # Store all jobs for JSON export
    
    @staticmethod
    def clean_text(text):
        """
        Clean text by removing extra spaces, newlines, and trimming
        
        Args:
            text (str): Text to clean
        
        Returns:
            str: Cleaned text
        """
        if not text:
            return ''
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def clean_description(text):
        """
        Clean job description while preserving intentional line breaks
        
        Args:
            text (str): Description text to clean
        
        Returns:
            str: Cleaned description
        """
        if not text:
            return ''
        
        # Split by newlines
        lines = text.split('\n')
        
        # Clean each line individually
        cleaned_lines = []
        for line in lines:
            # Remove extra spaces within the line
            cleaned_line = re.sub(r'\s+', ' ', line).strip()
            if cleaned_line:  # Only keep non-empty lines
                cleaned_lines.append(cleaned_line)
        
        # Join with newlines
        return '\n'.join(cleaned_lines)
    
    def setup_driver(self):
        """
        Setup Chrome WebDriver with appropriate options
        """
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("[OK] Chrome WebDriver initialized successfully")
            return True
        except Exception as e:
            print(f"[ERR] Error initializing Chrome WebDriver: {e}")
            print("\nPlease ensure Chrome and ChromeDriver are installed.")
            return False
    
    def setup_csv_file(self, filename):
        """
        Setup CSV file for incremental writing
        
        Args:
            filename (str): CSV filename
        """
        try:
            # Get the directory of the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.csv_filepath = os.path.join(script_dir, filename)
            
            # Setup JSON filepath (same name but .json extension)
            json_filename = filename.replace('.csv', '.json')
            self.json_filepath = os.path.join(script_dir, json_filename)
            
            # Define CSV headers
            headers = [
                'Job_Title',
                'Company',
                'Job_Type',
                'Location',
                'Salary',
                'Posted_Date',
                'Job_URL',
                'Job_Description'
            ]
            
            # Open CSV file in write mode
            self.csv_file = open(self.csv_filepath, 'w', newline='', encoding='utf-8-sig')
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=headers)
            self.csv_writer.writeheader()
            
            print(f"[OK] CSV file created: {self.csv_filepath}")
            print(f"[OK] JSON file will be created: {self.json_filepath}")
            print("[OK] Jobs will be saved incrementally (one by one)\n")
            
            return True
            
        except Exception as e:
            print(f"[ERR] Error setting up CSV file: {e}")
            return False
    
    def save_job_to_csv(self, job_data):
        """
        Save a single job to the CSV file immediately and store for JSON
        
        Args:
            job_data (dict): Job data dictionary
        """
        try:
            # Clean the data before saving
            cleaned_job = {}
            
            # Clean all text fields except URL
            for key in ['Job_Title', 'Company', 'Job_Type', 'Location', 'Salary', 'Posted_Date']:
                if key in job_data:
                    cleaned_job[key] = self.clean_text(job_data.get(key, ''))
            
            # Clean description separately (preserve line breaks)
            if 'Job_Description' in job_data:
                cleaned_job['Job_Description'] = self.clean_description(job_data.get('Job_Description', ''))
            
            # Keep URL as is
            cleaned_job['Job_URL'] = job_data.get('Job_URL', '')
            
            # Write to CSV
            self.csv_writer.writerow(cleaned_job)
            
            # Flush to ensure data is written immediately
            self.csv_file.flush()
            
            # Store for JSON export
            self.jobs_data.append(cleaned_job)
            
            self.jobs_scraped_count += 1
            
            return True
            
        except Exception as e:
            print(f"  [ERR] Error saving job to CSV: {e}")
            return False
    
    def close_csv_file(self):
        """
        Close the CSV file
        """
        if self.csv_file:
            self.csv_file.close()
            print(f"\n[OK] CSV file closed: {self.csv_filepath}")
    
    def save_to_json(self):
        """
        Save all collected job data to a JSON file
        """
        try:
            with open(self.json_filepath, 'w', encoding='utf-8') as json_file:
                json.dump(self.jobs_data, json_file, indent=2, ensure_ascii=False)
            
            print(f"[OK] JSON file saved: {self.json_filepath}")
            print(f"[OK] Total jobs in JSON: {len(self.jobs_data)}")
            return True
            
        except Exception as e:
            print(f"[ERR] Error saving JSON file: {e}")
            return False
    
    def get_total_job_count(self):
        """
        Extract the total number of jobs from the page
        
        Returns:
            int: Total number of jobs or None if not found
        """
        try:
            # Give extra time for the element to appear
            time.sleep(2)
            
            # Strategy 1: Try XPath with "total jobs" text
            try:
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'total jobs')]")))
                total_jobs_elements = self.driver.find_elements(By.XPATH, "//h2[contains(text(), 'total jobs')]")
                
                if total_jobs_elements:
                    total_text = total_jobs_elements[0].text
                    match = re.search(r'(\d+)\s+total jobs', total_text)
                    if match:
                        total_count = int(match.group(1))
                        print(f"[OK] Found total jobs: {total_count}")
                        return total_count
            except Exception as e:
                print(f"  Could not find total job count: {e}")
            
            # Strategy 2: Parse from page source directly
            try:
                page_source = self.driver.page_source
                match = re.search(r'(\d+)\s+total jobs', page_source, re.IGNORECASE)
                if match:
                    total_count = int(match.group(1))
                    print(f"[OK] Found total jobs from HTML: {total_count}")
                    return total_count
            except Exception as e:
                pass
            
            print("[WARN] Could not find total job count")
            return None
            
        except Exception as e:
            print(f"[WARN] Error in get_total_job_count: {e}")
            return None
    
    def modify_url_with_limit(self, total_jobs):
        """
        Modify the URL to include limit parameter for all jobs
        
        Args:
            total_jobs (int): Total number of jobs to fetch
        
        Returns:
            str: Modified URL with limit parameter
        """
        # Parse the URL
        parsed = urlparse(self.url)
        query_params = parse_qs(parsed.query)
        
        # Update or add the limit parameter
        query_params['limit'] = [str(total_jobs)]
        
        # Rebuild the query string
        new_query = urlencode(query_params, doseq=True)
        
        # Rebuild the URL
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        print(f"[OK] Modified URL: {new_url}")
        return new_url
    
    def fetch_job_listings_page(self):
        """
        Fetch the main job listings page - smart loading with URL modification
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"\nFetching job listings from: {self.url}")
            self.driver.get(self.url)
            
            # Wait for the job list container to load
            print("Waiting for page to load...")
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for the scrollable job list
            wait.until(EC.presence_of_element_located((By.ID, "scrollable-job-list")))
            print("[OK] Job list container loaded")
            
            # Wait for job items to appear
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.job-item")))
            print("[OK] Initial job items detected")
            
            # Additional wait for dynamic content
            time.sleep(5)
            
            # Get the total job count from the page
            total_jobs = self.get_total_job_count()
            
            if total_jobs and total_jobs > 20:
                print(f"\n{'='*60}")
                print(f"Smart Loading: Found {total_jobs} total jobs")
                print(f"Modifying URL to load all jobs at once...")
                print(f"{'='*60}\n")
                
                # Modify URL to include all jobs
                new_url = self.modify_url_with_limit(total_jobs)
                
                # Load the new URL with all jobs
                print(f"Loading URL with limit={total_jobs}...")
                self.driver.get(new_url)
                
                # Wait for page to reload
                wait.until(EC.presence_of_element_located((By.ID, "scrollable-job-list")))
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.job-item")))
                print("[OK] Page reloaded with new limit")
                
                # Wait for all jobs to load
                time.sleep(5)
                
                # Scroll to load all content
                print("Scrolling to ensure all jobs are loaded...")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
            else:
                print("\n[OK] Total jobs <= 20 or not found, using current page")
            
            # Count final job items
            job_items = self.driver.find_elements(By.CSS_SELECTOR, "div.job-item")
            final_count = len(job_items)
            print(f"\n{'='*60}")
            print(f"[OK] TOTAL JOBS LOADED: {final_count}")
            print(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            print(f"[ERR] Error fetching job listings page: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_job_data_with_xpath(self, job_element, index):
        """
        Extract job data using XPath from a job-item element
        
        Args:
            job_element: Selenium WebElement for a job-item
            index: Job index (1-based)
        
        Returns:
            dict: Job data dictionary
        """
        job_data = {}
        
        try:
            # Base XPath for this specific job item
            base_xpath = f'//*[@id="scrollable-job-list"]/div[{index}]'
            
            # Extract Job Title
            try:
                title_element = self.driver.find_element(By.XPATH, f'{base_xpath}//a[@class="job-title"]//h5[@class="job-title-h5"]')
                job_data['Job_Title'] = self.clean_text(title_element.text)
            except:
                try:
                    title_element = self.driver.find_element(By.XPATH, f'{base_xpath}//a[@class="job-title"]')
                    job_data['Job_Title'] = self.clean_text(title_element.text)
                except:
                    job_data['Job_Title'] = ''
            
            # Extract Job URL
            try:
                url_element = self.driver.find_element(By.XPATH, f'{base_xpath}//a[@class="job-title"]')
                href = url_element.get_attribute('href')
                job_data['Job_URL'] = href if href else ''
            except:
                job_data['Job_URL'] = ''
            
            # Extract Company Name - FIXED VERSION
            try:
                # First, try to get the anchor element inside the button
                company_element = self.driver.find_element(By.XPATH, f'{base_xpath}//button[contains(@class, "company")]//a')
                
                # Use JavaScript to extract only the text nodes (excluding img tags)
                company_text = self.driver.execute_script("""
                    var element = arguments[0];
                    var text = '';
                    for (var i = 0; i < element.childNodes.length; i++) {
                        var node = element.childNodes[i];
                        if (node.nodeType === Node.TEXT_NODE) {
                            text += node.textContent;
                        }
                    }
                    return text.trim();
                """, company_element)
                
                # If JavaScript extraction fails, try regular text extraction
                if not company_text or len(company_text.strip()) == 0:
                    company_text = company_element.text
                
                job_data['Company'] = self.clean_text(company_text)
                
            except:
                try:
                    # Fallback: try getting text from button directly
                    company_element = self.driver.find_element(By.XPATH, f'{base_xpath}//button[contains(@class, "company")]')
                    company_text = company_element.text
                    job_data['Company'] = self.clean_text(company_text)
                except:
                    job_data['Company'] = ''
            
            # Extract Job Type using XPath (1st span in data-row)
            try:
                job_type_element = self.driver.find_element(By.XPATH, f'{base_xpath}//div[@class="data-row"]/span[1]/span[last()]')
                job_data['Job_Type'] = self.clean_text(job_type_element.text)
            except:
                job_data['Job_Type'] = ''
            
            # Extract Location using XPath (2nd span in data-row)
            try:
                location_element = self.driver.find_element(By.XPATH, f'{base_xpath}//div[@class="data-row"]/span[2]/span[last()]')
                job_data['Location'] = self.clean_text(location_element.text)
            except:
                job_data['Location'] = ''
            
            # Extract Salary using XPath (3rd span in data-row, 2nd nested span)
            try:
                salary_element = self.driver.find_element(By.XPATH, f'{base_xpath}//div[@class="data-row"]/span[3]/span[2]')
                job_data['Salary'] = self.clean_text(salary_element.text)
            except:
                job_data['Salary'] = ''
            
            # Extract Posted Date
            try:
                posted_element = self.driver.find_element(By.XPATH, f'{base_xpath}//div[@class="posted-on-label"]')
                posted_text = posted_element.text
                # Extract just the date part
                date_match = re.search(r'\d{2}/\d{2}/\d{2}', posted_text)
                if date_match:
                    job_data['Posted_Date'] = date_match.group(0)
                else:
                    job_data['Posted_Date'] = self.clean_text(posted_text)
            except:
                job_data['Posted_Date'] = ''
            
            # Initially set description as empty (will be filled later)
            job_data['Job_Description'] = ''
            
        except Exception as e:
            print(f"    [ERR] Error extracting job data: {e}")
        
        return job_data
    
    def fetch_job_description(self, job_url):
        """
        Navigate to a job detail page and extract the description
        
        Args:
            job_url (str): URL of the job detail page
        
        Returns:
            str: Job description text or empty string if failed
        """
        try:
            self.driver.get(job_url)
            
            # Wait for the description container to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.container div.reader")))
            
            # Additional wait
            time.sleep(2)
            
            # Get page source
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the description container
            reader_div = soup.find('div', class_='reader')
            
            if reader_div:
                # Extract all text from paragraphs, lists, etc.
                paragraphs = reader_div.find_all('p')
                lists = reader_div.find_all(['ul', 'ol'])
                
                description_parts = []
                
                # Add paragraph text
                for p in paragraphs:
                    text = self.clean_text(p.get_text(strip=True))
                    if text:
                        description_parts.append(text)
                
                # Add list items
                for lst in lists:
                    items = lst.find_all('li')
                    for item in items:
                        text = self.clean_text(item.get_text(strip=True))
                        if text:
                            description_parts.append('- ' + text)
                
                # Join all parts with newlines and clean
                description = '\n'.join(description_parts)
                return self.clean_description(description)
            else:
                return ''
                
        except Exception as e:
            print(f"    [ERR] Error fetching description: {e}")
            return ''
    
    def collect_all_job_data_from_listings(self):
        """
        PHASE 1: Collect all job metadata + URLs from the listings page
        WITHOUT navigating away. Returns a list of job_data dicts.
        This avoids the stale element problem caused by driver.back().
        """
        job_items = self.driver.find_elements(By.CSS_SELECTOR, "div.job-item")
        total_jobs = len(job_items)

        print(f"\n{'='*60}")
        print(f"PHASE 1: Collecting metadata for {total_jobs} jobs from listings page...")
        print(f"{'='*60}\n")

        all_jobs = []
        for index in range(1, total_jobs + 1):
            try:
                # Re-find elements each iteration to avoid stale refs
                job_items_fresh = self.driver.find_elements(By.CSS_SELECTOR, "div.job-item")
                if index - 1 >= len(job_items_fresh):
                    print(f"  [WARN] Job item {index} no longer in DOM, skipping")
                    continue

                job_data = self.extract_job_data_with_xpath(job_items_fresh[index - 1], index)
                all_jobs.append(job_data)
                print(f"  [{index}/{total_jobs}] Collected: {job_data.get('Job_Title','?')} @ {job_data.get('Company','?')}")
            except Exception as e:
                print(f"  [ERR] Failed to collect job {index}: {e}")
                continue

        print(f"\n[OK] Phase 1 complete — collected {len(all_jobs)} job records")
        return all_jobs

    def scrape_and_save_incrementally(self):
        """
        FIX: Two-phase scraping to avoid stale element errors from driver.back().
        Phase 1 — collect all metadata + URLs from the listings page (no navigation).
        Phase 2 — visit each job URL directly and fetch description, then save.
        """
        # ── PHASE 1: collect all metadata without leaving the listings page ──
        all_jobs = self.collect_all_job_data_from_listings()
        total_jobs = len(all_jobs)

        print(f"\n{'='*60}")
        print(f"PHASE 2: Fetching descriptions for {total_jobs} jobs...")
        print(f"{'='*60}\n")

        # ── PHASE 2: visit each URL directly, no driver.back() needed ──
        for index, job_data in enumerate(all_jobs, start=1):
            try:
                print(f"[{index}/{total_jobs}] {job_data.get('Job_Title','?')} at {job_data.get('Company','?')}")
                print(f"              Type: {job_data.get('Job_Type','')}, Location: {job_data.get('Location','')}")
                print(f"              Salary: {job_data.get('Salary','')}")

                job_url = job_data.get('Job_URL', '')
                if job_url:
                    print(f"              Fetching description from: {job_url}")
                    description = self.fetch_job_description(job_url)
                    job_data['Job_Description'] = description

                    if description:
                        print(f"              [OK] Description fetched ({len(description)} chars)")
                    else:
                        print(f"              [WARN] No description found")
                else:
                    print(f"              [WARN] No URL — skipping description fetch")

                # Save immediately to CSV
                if self.save_job_to_csv(job_data):
                    print(f"              [OK] SAVED TO CSV ({self.jobs_scraped_count}/{total_jobs})")
                else:
                    print(f"              [ERR] Failed to save to CSV")

                print()
                time.sleep(1)  # polite delay

            except Exception as e:
                print(f"  [ERR] Error processing job {index}: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"\n{'='*60}")
        print(f"[OK] Scraping completed")
        print(f"[OK] Total jobs saved: {self.jobs_scraped_count}/{total_jobs}")
        print(f"{'='*60}\n")
    
    def scrape(self):
        """
        Main scraping method with incremental saving using XPath (CSV + JSON)
        """
        print("=" * 60)
        print("Rooster.jobs Web Scraper - CSV + JSON Export")
        print("=" * 60)
        
        # Setup WebDriver
        if not self.setup_driver():
            return
        
        # Setup CSV file for incremental writing
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rooster_jobs_{timestamp}.csv"
        if not self.setup_csv_file(filename):
            if self.driver:
                self.driver.quit()
            return
        
        try:
            # Step 1: Fetch the job listings page (with smart URL modification)
            if not self.fetch_job_listings_page():
                print("[ERR] Failed to fetch job listings page")
                return
            
            # Step 2: Parse and save jobs incrementally using XPath
            self.scrape_and_save_incrementally()
            
        finally:
            # Always close the CSV file and browser
            self.close_csv_file()
            
            # Save all data to JSON
            if self.jobs_data:
                self.save_to_json()
            
            if self.driver:
                self.driver.quit()
                print("[OK] Browser closed")
        
        print("\n" + "=" * 60)
        print("Scraping Completed")
        print(f"CSV File: {self.csv_filepath}")
        print(f"JSON File: {self.json_filepath}")
        print(f"Jobs Saved: {self.jobs_scraped_count}")
        print("=" * 60)


def read_url_from_file(filepath):
    """
    Read URL from RoosterJob.txt file
    
    Args:
        filepath (str): Path to RoosterJob.txt file
    
    Returns:
        str: URL or None if file is empty/invalid
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            url = f.read().strip()
            if url:
                return url
            else:
                print("[ERR] RoosterJob.txt is empty")
                return None
    except FileNotFoundError:
        print(f"[ERR] File not found: {filepath}")
        return None
    except Exception as e:
        print(f"[ERR] Error reading file: {e}")
        return None


if __name__ == "__main__":
    # Path to RoosterJob.txt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rooster_file = os.path.join(script_dir, 'RoosterJob.txt')
    
    # Read URL from RoosterJob.txt
    url = read_url_from_file(rooster_file)
    
    if url:
        # Create scraper instance and run
        scraper = RoosterJobsScraperXPath(url)
        scraper.scrape()
    else:
        print("\n" + "=" * 60)
        print("Please add the Rooster.jobs URL to RoosterJob.txt file")
        print("Example: https://rooster.jobs/?query=&limit=20&page=1&filters.jobTypes=internship")
        print("=" * 60)