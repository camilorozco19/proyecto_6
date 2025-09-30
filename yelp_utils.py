import json
import pandas as pd
from pathlib import Path

def extract_business_table(business_json_path, nrows=None):
    rows = []
    p = Path(business_json_path)
    with p.open('r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if nrows and i >= nrows:
                break
            j = json.loads(line)
            coords = j.get('coordinates') or {}
            cats = j.get('categories')
            if isinstance(cats, list):
                cats = ", ".join(cats)
            rows.append({
                'business_id': j.get('business_id'),
                'name': j.get('name'),
                'categories': cats,
                'review_count': j.get('review_count', 0),
                'city': j.get('city', ''),
                'latitude': coords.get('latitude'),
                'longitude': coords.get('longitude')
            })
    return pd.DataFrame(rows)

def extract_reviews_table(review_json_path, nrows=None):
    rows = []
    p = Path(review_json_path)
    with p.open('r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if nrows and i >= nrows:
                break
            j = json.loads(line)
            rows.append({
                'review_id': j.get('review_id'),
                'business_id': j.get('business_id'),
                'user_id': j.get('user_id'),
                'stars': j.get('stars'),
                'date': j.get('date'),
                'text': j.get('text')
            })
    return pd.DataFrame(rows)
