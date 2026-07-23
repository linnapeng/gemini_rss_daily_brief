import json, os, re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo
import feedparser
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'briefs.json'
TZ = ZoneInfo('Asia/Shanghai')
TODAY = datetime.now(TZ).date().isoformat()
MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
SEARCHES = [
    '("coffee chain" OR cafe OR Starbucks OR "coffee shop") innovation when:1d',
    '(bakery OR pastry OR bread OR dessert) launch innovation retail when:1d',
    '("food beverage" OR FMCG) new product consumer trend when:1d',
    '(retail OR restaurant OR brand) earnings expansion acquisition strategy when:1d',
]

class Source(BaseModel):
    name: str
    url: str
class BriefItem(BaseModel):
    zh_head: str; en_head: str; zh_fact: str; en_fact: str
    zh_why: str; en_why: str; insight_zh: str = ''; insight_en: str = ''
    zh_watch: str; en_watch: str; sources: list[Source]
class Brief(BaseModel):
    date: str; zh_summary: str; en_summary: str
    items: list[BriefItem] = Field(min_length=3, max_length=4)

def clean_html(text):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text or '')).strip()

def fetch_candidates():
    candidates, seen = [], set(); now = datetime.now(timezone.utc)
    for query in SEARCHES:
        url = 'https://news.google.com/rss/search?q=' + quote_plus(query) + '&hl=en-US&gl=US&ceid=US:en'
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title, link = clean_html(entry.get('title','')), entry.get('link','')
            if not title or not link: continue
            key = re.sub(r'\W+', '', title.lower())[:120]
            if key in seen: continue
            seen.add(key)
            published = entry.get('published',''); age_hours = None
            try:
                dt = parsedate_to_datetime(published)
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                age_hours = round((now-dt.astimezone(timezone.utc)).total_seconds()/3600,1)
            except Exception: pass
            source = entry.get('source'); publisher = source.get('title','') if isinstance(source,dict) else ''
            candidates.append({'title':title,'url':link,'publisher':publisher,'published':published,'age_hours':age_hours,'snippet':clean_html(entry.get('summary',''))[:500]})
    candidates.sort(key=lambda x: x['age_hours'] if x['age_hours'] is not None else 9999)
    return candidates[:40]

candidates = fetch_candidates()
if len(candidates) < 6: raise RuntimeError('Too few RSS candidates; aborting rather than inventing content.')
candidate_text = '\n'.join(
    f"[{i+1}] {x['title']}\nPublisher: {x['publisher'] or 'Unknown'}\nPublished: {x['published'] or 'Unknown'} | Age hours: {x['age_hours']}\nURL: {x['url']}\nSnippet: {x['snippet']}\n"
    for i,x in enumerate(candidates)
)
prompt = f'''Today is {TODAY} in Asia/Shanghai.
Using ONLY the RSS candidates below, produce an objective bilingual daily brief covering coffee chains and bakery innovation, food and beverage launches and consumer trends, and retail and brand operations.
Choose 3 or 4 important non-duplicate items. Prioritize the past 24 hours and use up to 7 days only when needed. Never add facts not present in the supplied metadata or snippet. When details are limited, state only what is supported. The brief must stand alone, distinguish facts from interpretation, and avoid personalized recommendations. A short general business insight is optional. Cite one or more supplied URLs for every item. Keep Chinese and English concise and equivalent. Set date to {TODAY}.
RSS CANDIDATES:\n{candidate_text}'''
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
response = client.models.generate_content(
    model=MODEL,
    contents=prompt,
    config=types.GenerateContentConfig(response_mime_type='application/json', response_schema=Brief, temperature=0.2, max_output_tokens=3200),
)
brief = Brief.model_validate_json(response.text); brief.date = TODAY
allowed_urls = {x['url'] for x in candidates}
for item in brief.items:
    if not item.sources: raise ValueError('Every item requires a source.')
    for source in item.sources:
        if source.url not in allowed_urls: raise ValueError(f'Unapproved source URL: {source.url}')
archive = json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else []
archive = [x for x in archive if x.get('date') != TODAY]; archive.append(brief.model_dump())
archive.sort(key=lambda x:x.get('date',''), reverse=True)
DATA.write_text(json.dumps(archive,ensure_ascii=False,indent=2),encoding='utf-8')
u = getattr(response,'usage_metadata',None)
print(f"Updated {TODAY} | model={MODEL} | candidates={len(candidates)} | prompt_tokens={getattr(u,'prompt_token_count','n/a')} | output_tokens={getattr(u,'candidates_token_count','n/a')} | total_tokens={getattr(u,'total_token_count','n/a')}")

