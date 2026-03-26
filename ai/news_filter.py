# ai/news_filter.py
import requests
from datetime import datetime, timedelta

NEWS_API_KEY = "YOUR_NEWS_API_KEY"
HIGH_IMPACT_KEYWORDS = ["FOMC", "Nonfarm Payrolls", "CPI", "PPI", "Fed", "Interest Rate"]

def is_news_blocked(block_minutes_before=30, block_minutes_after=30):
    # Placeholder – implement if you have a news API
    return False
