"""Check crawl results in PostgreSQL"""
from src.storage.database import get_db
from src.storage.models import CrawlResult
from collections import Counter

db = next(get_db())
try:
    results = db.query(CrawlResult).filter_by(site_name='yonhap').all()
    print(f'Total articles: {len(results)}')

    cats = Counter([r.category_kr for r in results])
    print('\nBy category:')
    for k, v in sorted(cats.items()):
        print(f'  {k}: {v}')

    print(f'\nQuality scores:')
    scores = [r.quality_score for r in results]
    print(f'  Average: {sum(scores)/len(scores):.1f}')
    print(f'  Min: {min(scores)}, Max: {max(scores)}')

finally:
    db.close()
