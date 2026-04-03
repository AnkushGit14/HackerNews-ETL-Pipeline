import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import os

os.makedirs('../images', exist_ok=True)
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams.update({'figure.figsize': (14, 7), 'font.size': 11})

# Connect to the loaded database
conn = sqlite3.connect('../data/hacker_news.db')
df = pd.read_sql_query("SELECT * FROM fact_posts", conn)

C = ['#FF6600', '#2E86AB', '#A23B72', '#F18F01', '#3B1F2B']  # HN orange is primary

print(f"Generating analytics for {len(df)} database records...")

# =========================================================
# CHART 1: Engagement Distribution
# =========================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('Hacker News Engagement Analysis — Points vs Comments', fontsize=18, fontweight='bold', y=1.03)

axes[0].hist(df['points'], bins=30, color=C[0], edgecolor='white', alpha=0.85)
axes[0].set_title('Distribution of Upvotes (Points)')
axes[0].set_xlabel('Points'); axes[0].set_ylabel('Number of Posts')

axes[1].scatter(df['points'], df['comments'], color=C[1], alpha=0.6, s=50, edgecolor='white')
axes[1].set_title('Correlation: Points vs Comments')
axes[1].set_xlabel('Points'); axes[1].set_ylabel('Comments')

plt.tight_layout()
plt.savefig('../images/01_engagement_metrics.png', dpi=150, bbox_inches='tight')
plt.close()

# =========================================================
# CHART 2: Top Domains
# =========================================================
fig, ax = plt.subplots(figsize=(14, 8))

top_domains = df[df['domain'] != 'news.ycombinator.com']['domain'].value_counts().head(15)
bars = ax.barh(top_domains.index[::-1], top_domains.values[::-1], color=C[2], edgecolor='white')
ax.set_title('Top 15 Most Popular Domains on Hacker News Front Page', fontsize=16, fontweight='bold')
ax.set_xlabel('Number of Posts')

for bar, val in zip(bars, top_domains.values[::-1]):
    ax.text(val + 0.1, bar.get_y() + bar.get_height()/2, f'{val}', va='center', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('../images/02_top_domains.png', dpi=150, bbox_inches='tight')
plt.close()

# =========================================================
# CHART 3: Content Categories (Regex keyword extraction)
# =========================================================
fig, ax = plt.subplots(figsize=(12, 6))

keywords = {
    'AI/ML': r'(?i)\b(ai|ml|chatgpt|openai|llm)\b',
    'Rust/Go/C': r'(?i)\b(rust|golang|c\+\+|linux)\b',
    'Startup/VC': r'(?i)\b(startup|funding|vc|founder)\b',
    'Show HN': r'Show HN:',
    'Security': r'(?i)\b(hack|security|breach|vulnerability)\b'
}

cat_counts = {cat: df['title'].str.contains(regex).sum() for cat, regex in keywords.items()}
cat_df = pd.Series(cat_counts).sort_values()

bars = ax.barh(cat_df.index, cat_df.values, color=C[3])
ax.set_title('Tech Trends: Mentions in Post Titles', fontsize=16, fontweight='bold')
ax.set_xlabel('Number of Mentions')

plt.tight_layout()
plt.savefig('../images/03_tech_trends.png', dpi=150, bbox_inches='tight')
plt.close()
conn.close()

print("[COMPLETE] Successfully generated 3 analytical charts derived directly from the loaded SQLite Database.")
