"""
=============================================================================
HACKER NEWS ETL PIPELINE — Extract, Transform, Load (Production Grade)
=============================================================================
Author: Ankush Kumar Jaiswal
Description: 
An automated ETL pipeline that scrapes the front pages of YCombinator's 
Hacker News, transforms unstructured HTML into cleaned data via Pandas 
and Regex, and loads it into a SQLite database for analytical querying.
=============================================================================
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import re
import datetime
import time
import os

class HackerNewsETL:
    def __init__(self, db_path='../data/hacker_news.db'):
        self.base_url = "https://news.ycombinator.com/news"
        self.db_path = db_path
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database with proper schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create fact_posts table with constraints (production standard)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fact_posts (
                post_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                domain TEXT,
                points INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print(f"[SYSTEM] Connected to SQLite database: {self.db_path}")

    def extract(self, num_pages=3):
        """
        EXTRACT: Scrapes multiple pages using requests and BeautifulSoup.
        Returns a list of raw dictionaries.
        """
        print(f"\n[1/3] EXTRACTING data from {num_pages} pages of Hacker News...")
        raw_data = []
        
        for page in range(1, num_pages + 1):
            response = requests.get(f"{self.base_url}?p={page}", headers=self.headers)
            if response.status_code != 200:
                print(f"[Error] Failed to fetch page {page}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # hn uses a table structure: tr.athing for title/link, next tr for subtext (points/comments)
            items = soup.find_all('tr', class_='athing')
            
            for item in items:
                post_id = item.get('id')
                
                titleline = item.find('span', class_='titleline')
                if not titleline: continue
                
                title_a = titleline.find('a')
                title = title_a.text.strip() if title_a else "Unknown"
                
                site_span = titleline.find('span', class_='sitebit')
                domain = site_span.text.strip().replace('(', '').replace(')', '') if site_span else "news.ycombinator.com"
                
                # The subtext contains points and comments. It's in the NEXT <tr> sibling
                subtext_tr = item.find_next_sibling('tr')
                subtext = subtext_tr.find('td', class_='subtext') if subtext_tr else None
                
                if subtext:
                    score_span = subtext.find('span', class_='score')
                    points_text = score_span.text if score_span else "0 points"
                    
                    # Comments are tricky: usually the last <a> tag containing 'comment'
                    links = subtext.find_all('a')
                    comments_text = "0 comments"
                    for link in links:
                        if 'comment' in link.text:
                            comments_text = link.text
                            break
                            
                    raw_data.append({
                        'post_id': post_id,
                        'title': title,
                        'domain': domain,
                        'points_raw': points_text,
                        'comments_raw': comments_text
                    })
            
            # Anti-bot delay
            time.sleep(1)
            
        print(f"      Successfully extracted {len(raw_data)} raw records.")
        return raw_data

    def transform(self, raw_data):
        """
        TRANSFORM: Cleans text strings, normalizes data types using Pandas.
        """
        print("[2/3] TRANSFORMING unstructured data into cleaned analytical format...")
        df = pd.DataFrame(raw_data)
        
        if df.empty:
            print("[Warning] No data to transform.")
            return df
        
        # 1. Clean Points using Regex (extract digits)
        df['points'] = df['points_raw'].apply(
            lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0
        )
        
        # 2. Clean Comments using Regex
        df['comments'] = df['comments_raw'].apply(
            lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0
        )
        
        # 3. Add timestamp
        df['scraped_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 4. Filter columns & drop duplicates
        cleaned_df = df[['post_id', 'title', 'domain', 'points', 'comments', 'scraped_at']]
        cleaned_df = cleaned_df.drop_duplicates(subset=['post_id'])
        
        print(f"      Transformed {len(cleaned_df)} records successfully. (Regex applied, Dtypes normalized)")
        return cleaned_df

    def load(self, df):
        """
        LOAD: Upsert data into SQLite database.
        """
        print("[3/3] LOADING data into SQLite database...")
        if df.empty:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Implementing robust "UPSERT" logic (update if exists, insert if new)
        records_inserted = 0
        records_updated = 0
        
        for _, row in df.iterrows():
            # Check if post exists
            cursor.execute('SELECT post_id FROM fact_posts WHERE post_id = ?', (row['post_id'],))
            exists = cursor.fetchone()
            
            if exists:
                # Update points and comments for existing posts
                cursor.execute('''
                    UPDATE fact_posts 
                    SET points = ?, comments = ?, scraped_at = ?
                    WHERE post_id = ?
                ''', (row['points'], row['comments'], row['scraped_at'], row['post_id']))
                records_updated += 1
            else:
                # Insert new post
                cursor.execute('''
                    INSERT INTO fact_posts (post_id, title, domain, points, comments, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (row['post_id'], row['title'], row['domain'], row['points'], row['comments'], row['scraped_at']))
                records_inserted += 1
                
        conn.commit()
        
        # Verify db count
        cursor.execute('SELECT COUNT(*) FROM fact_posts')
        total_db_records = cursor.fetchone()[0]
        conn.close()
        
        print(f"      Loaded successfully! Inserted: {records_inserted} | Updated: {records_updated}")
        print(f"      Total records currently residing in Data Warehouse (SQLite): {total_db_records}")

    def run_pipeline(self, pages=5):
        """Executes the full ETL cycle."""
        print("\n" + "="*50)
        print("          STARTING E-T-L PIPELINE PIPELINE")
        print("="*50)
        
        raw_data = self.extract(num_pages=pages)
        cleaned_df = self.transform(raw_data)
        self.load(cleaned_df)
        
        print("="*50)
        print("      PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
        print("="*50 + "\n")

if __name__ == "__main__":
    pipeline = HackerNewsETL()
    pipeline.run_pipeline(pages=4)
