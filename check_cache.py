import json

data = json.load(open('./backend/data/search_cache.json', 'r', encoding='utf-8'))
# Find the most recent housing/welfare related cache entry
for k, v in data.items():
    if 'housing' in k.lower() or 'welfare' in k.lower():
        print(f'Cache key: {k}')
        print(f'  Papers: {len(v)}')
        for p in v:
            abstract_status = "HAS_ABSTRACT" if p.get("abstract") else "NO_ABSTRACT"
            title = p.get("title", "N/A")[:70]
            yr = p.get("year", "N/A")
            print(f'    [{abstract_status}] {title} ({yr})')
        print()
