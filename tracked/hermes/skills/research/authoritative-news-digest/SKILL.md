---
name: authoritative-news-digest
description: Compile a current-events digest from authoritative sources when full web browsing is unreliable or partially blocked, using RSS feeds and article metadata extraction as fallbacks.
version: 1.0.0
author: Hermes
license: CC0-1.0
metadata:
  hermes:
    tags: [news, digest, rss, ap, npr, cbs, cron]
---

# Authoritative News Digest

Use this skill when you need a time-bounded news summary (for example, "top 10 stories from the last 24 hours") and normal browser/web access is unavailable, flaky, or blocked for many major outlets.

## When to use
- Scheduled news briefings
- "Top stories in the last 24 hours" tasks
- Situations where Reuters/BBC/FT/NYT browser access times out or returns connection errors
- You must avoid fabrication and only use verifiable, recent, authoritative reporting

## Core principle
Prefer authoritative outlets, but **do not hallucinate around access failures**. If some outlets are unreachable, build the digest from the best reachable high-quality sources and skip anything you cannot verify.

## Proven fallback stack
In constrained environments, these worked reliably:
1. **AP hub pages** via `curl`
   - `https://apnews.com/hub/ap-top-news`
   - `https://apnews.com/hub/world-news`
   - `https://apnews.com/hub/business`
2. **NPR RSS**
   - `https://feeds.npr.org/1004/rss.xml` (World)
3. **CBS RSS**
   - `https://www.cbsnews.com/latest/rss/world`
   - `https://www.cbsnews.com/latest/rss/moneywatch`
   - `https://www.cbsnews.com/latest/rss/technology`
   - `https://www.cbsnews.com/latest/rss/politics`
   - `https://www.cbsnews.com/latest/rss/us`
4. **The Verge Atom feed**
   - `https://www.theverge.com/rss/index.xml`
   - Note: this is Atom, not RSS; parse `<entry>`, `<published>`, and alternate `<link href=...>`.

Observed failure modes:
- Browser navigation to Reuters may fail with `ERR_CONNECTION_REFUSED`.
- Browser navigation to AP section pages can also time out even when `curl` to the same URL succeeds; do not abandon AP just because browser automation is flaky.
- Direct `curl`/browser access to BBC, Reuters, FT, NYT, Guardian, Al Jazeera may time out.
- Python `urllib` may fail with `Network is unreachable` even when `curl` succeeds.
- Some RSS feeds (example: CNN) can fail with TLS EOF errors.
- AP hub pages may redirect or be less useful than section pages; in practice `https://apnews.com/world-news`, `https://apnews.com/business`, `https://apnews.com/politics`, and `https://apnews.com/science` were more reliable for discovering fresh article links.
- Some NPR feed IDs return `403 MissingAuthenticationTokenException`; do not assume a guessed feed ID exists just because another NPR feed works.
- The Verge feed is Atom, so RSS-only parsing will incorrectly return zero items.
- CBS feeds can contain many video-only items and the same story can appear in multiple section feeds; filter duplicates by URL/title and prefer text articles over video clips when building a top-news digest.
- The Verge feed is useful for tech developments, but it also contains reviews, deals, and features; for a "most important news" digest, include only hard-news items with clear public-interest significance.
- AP section and hub pages can yield many very fresh but low-salience items (sports, celebrity, quirky features, domestic procedural stories). Freshness alone is not enough: for a global top-news digest, do an explicit significance pass before promoting AP items, and do not let AP volume crowd out more globally consequential RSS stories.
- Piping `curl` output directly into a parser can trigger noisy `curl: (23) Failure writing output to destination` / broken-pipe behavior when the consumer exits early; in practice it is more reliable to download AP section HTML to a temp file first, then parse the saved file.
- AP article pages may expose `article:published_time` without an explicit timezone offset (for example `2026-04-17T04:08:14`); treat naive timestamps carefully and compare conservatively against the 24-hour window rather than assuming UTC.
- AP section and hub pages can surface prominently linked stories that are much older than the current window (for example, month-old explainer or feature links mixed into fresh coverage). Do not infer recency from page position or section placement — always fetch each article page and verify `article:published_time` before including it.
- AP availability can vary by path and by request timing. In one run, `https://apnews.com/politics` returned full HTML while `world-news`, `business`, and `science` returned Cloudflare `error code: 1015`, and a previously usable hub page later exposed zero extractable article URLs. Treat AP as opportunistic, not guaranteed: probe multiple AP paths, expect inconsistent rate limiting, and keep RSS sources ready as the primary fallback.
- CBS RSS `pubDate` can reflect feed/update timing rather than the article's original publication time. A story may appear to be within the last 24 hours in RSS but have an on-page `article:published_time` older than the requested window. For any CBS item you plan to include, fetch the article page and verify the page-level publication timestamp before finalizing.
- CBS article pages may not expose `article:published_time` meta tags at all. In practice, the reliable fallback is JSON-LD / structured-data fields such as `"datePublished":"..."` and `"dateModified":"..."`. Prefer `datePublished` for the 24-hour filter; use `dateModified` only as supplemental context for live-update pages.
- Some NPR and CBS article pages expose little or no easy-to-scrape OG/description metadata even when the RSS item is valid and current. If the feed item itself is from a trusted source, within the requested window, and page fetch succeeds but yields poor metadata, it is acceptable to use the RSS title/description/pubDate as the canonical summary source rather than dropping the story.
- NPR article pages may expose only a coarse publication date (for example `2026-04-23`) without a time-of-day even when the RSS feed has an exact `pubDate`. For strict last-24-hours filtering, prefer the RSS `pubDate` as the canonical timestamp and use the page only to confirm reachability / headline / description.
- CBS RSS items can sometimes point to article URLs that currently return a CBS 404 error page even though the feed entry itself is fresh. Do not treat the feed timestamp alone as enough verification in that case: if the linked page is actually a 404/unreachable error page, skip the item rather than summarizing it from RSS.
- AP article fetches can be inconsistent at the individual URL level: some article URLs extracted from section pages return full HTML while others return only `error code: 1015` from Cloudflare. Treat per-article AP availability as opportunistic, skip blocked URLs quickly, and keep enough candidate URLs from RSS/CBS/AP sections so one blocked article does not stall the digest.
- AP section pages can occasionally behave like generic shells and expose nearly identical article-link sets across multiple sections (`world-news`, `business`, `science`, etc.). Do not assume section-specific topical diversity just because the path differs; compare extracted link sets and rely on RSS/CBS/NPR for breadth when AP sections collapse to the same candidate pool.

## Workflow

### 1) Check current date/time first
Use a tool, never guess.

Example:
```bash
date '+%Y-%m-%d %H:%M:%S %Z (%z)'
```

### 2) Probe which sources are reachable
Use `curl -I -L --max-time 12-20` against candidate outlets.
Do not assume browser reachability means shell reachability, or vice versa.

### 3) Pull RSS where possible
If feeds are reachable, parse with `python3` stdlib XML tools via `execute_code` or shell.
Do **not** rely on `feedparser` being installed.

### 4) Use AP section pages as a strong fallback
AP section pages and hub pages can both work, but section pages were often better for fresh stories in browser-constrained runs:
- `https://apnews.com/world-news`
- `https://apnews.com/business`
- `https://apnews.com/politics`
- `https://apnews.com/science`

They expose article links in page HTML and, in browser snapshots, often show relative freshness labels like "27 mins ago" that help prioritize what to fetch next.

Extract article URLs with regex, normalize to full URLs, then fetch article pages individually.

Useful regex:
```python
rels = re.findall(r'/article/[a-z0-9\\-]+', html)
abs_urls = re.findall(r'https://apnews.com/article/[a-z0-9\\-]+', html)
urls = ['https://apnews.com' + r for r in rels] + abs_urls
```

Support both relative and absolute AP article URLs. In some runs the page exposes relative `/article/...` links; in others, full `https://apnews.com/article/...` links are also present. Deduplicate after extraction rather than assuming only one form will appear.

### 5) Extract AP article metadata from meta tags
For each AP article page, pull:
- `og:title`
- `og:description`
- `article:published_time`

Important: use a **non-greedy DOTALL regex** because AP meta tag content can span lines.

Example:
```python
m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([\\s\\S]*?)"', html, re.S)
```

This is more reliable than expecting compact one-line HTML.

### 6) Build candidate pool, then deduplicate by topic
Common duplicate cluster in crisis news:
- military action
- market/oil reaction
- mediation/diplomacy
- humanitarian impact

Do not include 3-4 items that are effectively the same story unless they represent clearly different angles of global significance.

### 7) Keep only stories clearly within the requested time window
Use the article/feed publication timestamp. If unsure, skip it.

### 8) Mark fast-moving stories
If the report concerns ongoing war, markets, storms, live investigations, diplomacy, or unfolding disasters, append:
- `事件持续发展中`

## Practical extraction snippets

### AP article metadata via shell
```bash
curl -L --max-time 20 -sS "$URL" | perl -0ne '
  if(/property="og:title" content="([\s\S]*?)"/){$t=$1;$t=~s/\n/ /g;print "TITLE:$t\n"}
  if(/property="og:description" content="([\s\S]*?)"/){$d=$1;$d=~s/\n/ /g;print "DESC:$d\n"}
  if(/property="article:published_time" content="([\s\S]*?)"/){print "PUB:$1\n"}
'
```

### RSS parsing with stdlib only
```python
import xml.etree.ElementTree as ET
root = ET.fromstring(xml_text)
for item in root.findall('.//item'):
    title = (item.findtext('title') or '').strip()
    pub = (item.findtext('pubDate') or '').strip()
    desc = re.sub('<[^>]+>', '', (item.findtext('description') or '').strip())
    link = (item.findtext('link') or '').strip()
```

### Atom parsing with stdlib only
```python
import xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom'}
root = ET.fromstring(xml_text)
for entry in root.findall('a:entry', ns):
    title = (entry.findtext('a:title', default='', namespaces=ns) or '').strip()
    pub = (entry.findtext('a:published', default='', namespaces=ns)
           or entry.findtext('a:updated', default='', namespaces=ns) or '').strip()
    link = ''
    for l in entry.findall('a:link', ns):
        if l.attrib.get('rel') == 'alternate':
            link = l.attrib.get('href', '')
            break
```

## Output checklist
For a Chinese digest with strict formatting requirements:
- Start with date + one-sentence overview
- Number stories `1）` to `10）`
- For each story: one-sentence headline + 2-4 sentences summary
- Include source outlet and publication time
- Avoid invented details; if unverifiable, omit
- Keep topic spread across politics, economy, technology, society, disaster, conflict

## Pitfalls
- Do not use mental memory for current events.
- Do not trust only one outlet if a story seems sensational; cross-check when possible.
- AP article pages may include huge HTML blobs; extract only meta tags instead of full-body parsing.
- `python3 urllib` network failures do not imply `curl` failure.
- RSS category feeds can be sparse; mix AP hubs + NPR/CBS feeds to reach enough distinct topics.
- In cron runs, avoid one giant `execute_code` script that fetches many URLs serially with `curl`; this can consume the full 300s sandbox limit and prevent any final response from being produced.
- Even when total runtime is acceptable, nested `terminal()` calls inside `execute_code` can be less reliable for AP bulk extraction than a single `terminal` call running a short Python script with `subprocess` + `curl`. If AP extraction behaves oddly or returns unexpectedly empty results, switch to `terminal` with one self-contained Python snippet.
- Prefer small `terminal` fetches per source, or at most tiny `execute_code` parsing snippets over already-fetched content.
- When verifying candidate article pages, batch the work aggressively: fetching metadata for 8-12 full article URLs in one Python/`curl` loop can still hit sandbox time limits even with modest per-request timeouts. In practice, verify only the top-priority 4-6 candidates at a time, eliminate stale/duplicate stories, then fetch another small batch if you still need more items.

## Verification
Before finalizing:
1. Confirm every included story has a reachable source URL and visible publication time.
2. Confirm all items are within the requested time window.
3. Confirm no obvious duplicate topics crowd out other major domains.
4. Confirm summaries are paraphrases of source metadata/feed descriptions, not inventions.
