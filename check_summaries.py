import json
data = json.load(open('./backend/data/session_data.json', 'r', encoding='utf-8'))
for sid, summaries in data.get('summaries', {}).items():
    print(f"Session: {sid}")
    print(f"  Total summaries: {len(summaries)}")
    for i, s in enumerate(summaries):
        print(f"  {i+1}. {s.get('title', 'N/A')} ({s.get('year', 'N/A')}) [id: {s.get('paper_id', 'N/A')}]")
