# -*- coding: utf-8 -*-
"""
TopJobs Web Scraper with Selenium - IMPROVED VERSION
This script scrapes job listings from TopJobs website using Selenium and saves them to a CSV file.
Enhanced with better debugging and content loading detection.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime
import time

class TopJobsScraper:
    def __init__(self, url):
        """
        Initialize the scraper with the target URL
        
        Args:
            url (str): The URL to scrape from TopJobs.txt
        """
        self.url = url
        self.jobs_data = []
        self.driver = None
    
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
            print("You can install ChromeDriver using: pip install webdriver-manager")
            return False
    
    def fetch_page(self):
        """
        Fetch the webpage content using Selenium with improved waiting
        
        Returns:
            str: HTML content of the page or None if failed
        """
        try:
            print(f"Fetching data from: {self.url}")
            self.driver.get(self.url)
            
            # Wait for the job list container to load
            print("Waiting for page to load...")
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for the jb-list div to be present
            wait.until(EC.presence_of_element_located((By.ID, "jb-list")))
            print("[OK] Page structure loaded")
            
            # Wait for the table to be present
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.tbldata_2")))
                print("[OK] Table with class 'tbldata_2' found")
            except:
                print("[WARN] Table with class 'tbldata_2' not found, trying generic table")
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#jb-list table")))
                print("[OK] Generic table found")
            
            # Wait for table body and rows to be present
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.tbldata_2 tbody")))
                print("[OK] Table body detected")
                
                # Wait for at least one row
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.tbldata_2 tbody tr")))
                print("[OK] Table rows detected")
            except Exception as e:
                print(f"[WARN] Warning detecting table rows: {e}")
            
            # Additional wait for dynamic content to fully render
            print("Waiting for dynamic content to load...")
            time.sleep(5)
            
            # Scroll to ensure all content is rendered (some sites lazy-load)
            print("Scrolling page to trigger lazy-loading...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Debug: Count rows in the actual DOM before returning
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table.tbldata_2 tbody tr")
                print(f"[OK] Detected {len(rows)} rows in DOM")
                
                # Also check for thead
                thead = self.driver.find_elements(By.CSS_SELECTOR, "table.tbldata_2 thead")
                print(f"[OK] Detected {len(thead)} thead elements")
                
            except Exception as e:
                print(f"[WARN] Could not count rows: {e}")
            
            # Get the page source after JavaScript execution
            html_content = self.driver.page_source
            print("[OK] Page HTML fetched successfully")
            print(f"[OK] HTML content size: {len(html_content)} bytes")
            
            return html_content
            
        except Exception as e:
            print(f"[ERR] Error fetching page: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_jobs(self, html_content):
        """
        Parse job listings from HTML content with enhanced debugging
        
        Args:
            html_content (str): HTML content to parse
        
        Returns:
            list: List of job dictionaries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Debug: Save HTML to file for inspection
        debug_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug_selenium_page.html')
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\n[OK] Saved FULL HTML to {debug_file} for inspection")
        print(f"  File size: {os.path.getsize(debug_file)} bytes")
        
        # Strategy 1: Try finding by id 'jb-list'
        container = soup.find('div', id='jb-list')
        
        if not container:
            print("[ERR] Could not find 'jb-list' div")
            # Debug: Show what divs are available
            all_divs = soup.find_all('div', limit=20)
            print(f"\n--- Found {len(all_divs)} divs in HTML ---")
            for div in all_divs[:10]:
                div_id = div.get('id', 'no-id')
                div_class = ' '.join(div.get('class', []))
                print(f"  <div id='{div_id}' class='{div_class}'>")
            return []
        else:
            print("[OK] Found 'jb-list' container")
        
        # Save just the jb-list container for inspection
        jblist_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug_jblist_only.html')
        with open(jblist_file, 'w', encoding='utf-8') as f:
            f.write(str(container.prettify()))
        print(f"[OK] Saved jb-list container to {jblist_file}")
        
        # Find the table within the container
        table = container.find('table', class_='tbldata_2')
        
        if not table:
            # Try without class
            table = container.find('table')
            if table:
                print("[OK] Found table (without specific class)")
                table_classes = ' '.join(table.get('class', []))
                print(f"  Table classes: '{table_classes}'")
        else:
            print("[OK] Found table with class 'tbldata_2'")
        
        if not table:
            print("[ERR] Could not find the job table")
            # Debug: Print available tables
            print("\n--- Available tables in jb-list ---")
            all_tables = container.find_all('table')
            print(f"Total tables found: {len(all_tables)}")
            for idx, tbl in enumerate(all_tables, 1):
                tbl_class = ' '.join(tbl.get('class', []))
                tbl_id = tbl.get('id', '')
                print(f"  Table {idx}: <table class='{tbl_class}' id='{tbl_id}'>")
            return []
        
        # Save just the table for inspection
        table_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug_table_only.html')
        with open(table_file, 'w', encoding='utf-8') as f:
            f.write(str(table.prettify()))
        print(f"[OK] Saved table to {table_file}")
        
        # Check for thead
        thead = table.find('thead')
        if thead:
            print("[OK] Found thead")
            header_rows = thead.find_all('tr')
            print(f"  Header rows: {len(header_rows)}")
            if header_rows:
                header_cells = header_rows[0].find_all(['th', 'td'])
                print(f"  Header columns: {len(header_cells)}")
                headers = [cell.get_text(strip=True) for cell in header_cells]
                print(f"  Headers: {headers}")
        
        # Find tbody containing all job rows
        tbody = table.find('tbody')
        
        if not tbody:
            print("[WARN] No tbody found, trying to get rows directly from table")
            rows = table.find_all('tr')
            # Filter out thead rows if they exist
            if thead:
                rows = [row for row in rows if row.parent.name != 'thead']
        else:
            print("[OK] Found tbody")
            rows = tbody.find_all('tr')
        
        print(f"[OK] Found {len(rows)} data rows to process")
        
        jobs = []
        for index, row in enumerate(rows, 1):
            try:
                cols = row.find_all('td')
                
                # Debug first few rows
                if index <= 3:
                    print(f"\n--- Row {index} Debug ---")
                    print(f"  Columns found: {len(cols)}")
                    if cols:
                        for i, col in enumerate(cols):
                            text = col.get_text(strip=True)[:50]  # First 50 chars
                            print(f"    Col {i}: '{text}'")
                
                # Skip header rows or rows with insufficient columns
                if len(cols) < 7:
                    print(f"  [WARN] Row {index} has only {len(cols)} columns, skipping")
                    continue
                
                # Extract position and employer separately from column 2
                position_col = cols[2]
                position = ''
                employer = ''
                job_code = ''
                
                # Try to extract hidden job code (hdnJC0, hdnJC1, etc.)
                hidden_jc = position_col.find('span', id=lambda x: x and x.startswith('hdnJC'))
                if hidden_jc:
                    job_code = hidden_jc.get_text(strip=True)
                
                # Try to extract position from h2 > span
                h2_tag = position_col.find('h2')
                if h2_tag:
                    span_tag = h2_tag.find('span')
                    if span_tag:
                        position = span_tag.get_text(strip=True)
                    else:
                        position = h2_tag.get_text(strip=True)
                
                # Try to extract employer from h1
                h1_tag = position_col.find('h1')
                if h1_tag:
                    employer = h1_tag.get_text(strip=True)
                
                # Fallback: if no structured data found, use all text
                if not position and not employer:
                    all_text = position_col.get_text(strip=True)
                    position = all_text
                
                # Debug for first few rows
                if index <= 3:
                    print(f"  Position: '{position}'")
                    print(f"  Employer: '{employer}'")
                    if job_code:
                        print(f"  Job Code: '{job_code}'")
                
                # Extract data from each column
                job_data = {
                    'Number': cols[0].get_text(strip=True),
                    'Job_Ref_No': cols[1].get_text(strip=True),
                    'Job_Code': job_code,
                    'Position': position,
                    'Employer': employer,
                    'Job_Description': cols[3].get_text(strip=True),
                    'Opening_Date': cols[4].get_text(strip=True),
                    'Closing_Date': cols[5].get_text(strip=True),
                    'Town': cols[6].get_text(strip=True)
                }
                
                # Skip if it's a header row (check if first column contains '#')
                if job_data['Number'] == '#':
                    print(f"  [WARN] Row {index} is header row, skipping")
                    continue
                
                # Skip empty rows
                if not job_data['Job_Ref_No']:
                    print(f"  [WARN] Row {index} has no Job Ref No, skipping")
                    continue
                
                jobs.append(job_data)
                print(f"  [OK] Parsed job #{job_data['Number']}: {job_data['Position']} at {job_data['Employer']}")
                
            except Exception as e:
                print(f"  [ERR] Error parsing row {index}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n{'='*60}")
        print(f"[OK] Successfully parsed {len(jobs)} jobs")
        print(f"{'='*60}")
        return jobs
    
    def save_to_csv(self, filename='topjobs_data.csv'):
        """
        Save scraped jobs data to CSV file
        
        Args:
            filename (str): Output CSV filename
        """
        if not self.jobs_data:
            print("[ERR] No data to save")
            return
        
        try:
            # Get the directory of the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(script_dir, filename)
            
            # Define CSV headers
            headers = [
                'Number',
                'Job_Ref_No',
                'Job_Code',
                'Position',
                'Employer',
                'Job_Description',
                'Opening_Date',
                'Closing_Date',
                'Town'
            ]
            
            # Write to CSV
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(self.jobs_data)
            
            print(f"\n[OK] Data saved successfully to: {filepath}")
            print(f"[OK] Total jobs saved: {len(self.jobs_data)}")
            
        except Exception as e:
            print(f"[ERR] Error saving to CSV: {e}")
            import traceback
            traceback.print_exc()
    
    def scrape(self):
        """
        Main scraping method
        """
        print("=" * 60)
        print("TopJobs Web Scraper Started (Selenium - IMPROVED)")
        print("=" * 60)
        
        # Setup WebDriver
        if not self.setup_driver():
            return
        
        try:
            # Fetch the page
            html_content = self.fetch_page()
            
            if not html_content:
                print("[ERR] Failed to fetch page content")
                return
            
            # Parse jobs
            self.jobs_data = self.parse_jobs(html_content)
            
            # Save to CSV
            if self.jobs_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"topjobs_data_{timestamp}.csv"
                self.save_to_csv(filename)
            else:
                print("\n[ERR] No jobs data found to save")
                print("   Check the debug HTML files for inspection:")
                print("   - debug_selenium_page.html")
                print("   - debug_jblist_only.html")
                print("   - debug_table_only.html")
            
        finally:
            # Always close the browser
            if self.driver:
                self.driver.quit()
                print("\n[OK] Browser closed")
        
        print("=" * 60)
        print("Scraping Completed")
        print("=" * 60)


def read_url_from_file(filepath):
    """
    Read URL from TopJobs.txt file
    
    Args:
        filepath (str): Path to TopJobs.txt file
    
    Returns:
        str: URL or None if file is empty/invalid
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            url = f.read().strip()
            if url:
                return url
            else:
                print("[ERR] TopJobs.txt is empty")
                return None
    except FileNotFoundError:
        print(f"[ERR] File not found: {filepath}")
        return None
    except Exception as e:
        print(f"[ERR] Error reading file: {e}")
        return None


if __name__ == "__main__":
    # Path to TopJobs.txt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    topjobs_file = os.path.join(script_dir, 'TopJobs.txt')
    
    # Read URL from TopJobs.txt
    url = read_url_from_file(topjobs_file)
    
    if url:
        # Create scraper instance and run
        scraper = TopJobsScraper(url)
        scraper.scrape()
    else:
        print("\n" + "=" * 60)
        print("Please add the TopJobs URL to TopJobs.txt file")
        print("Example: https://www.topjobs.lk/jobs")
        print("=" * 60)