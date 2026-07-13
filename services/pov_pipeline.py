#!/usr/bin/env python3
"""POV News batch pipeline: collect → cluster → analyze.

Stores data in ~/.appdata/pov/:
  raw_articles.json  (collector)
  clusters.json      (cluster)
  pov_results.json   (analyze — consumed by the /pov feed)

Run a single stage:
    python3 -m services.pov_pipeline collect
    python3 -m services.pov_pipeline cluster
    python3 -m services.pov_pipeline analyze
Or all in order:
    python3 -m services.pov_pipeline all

Metadata + snippets only — no full-text redistribution.
"""

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

DATA_DIR = pathlib.Path.home() / ".appdata" / "pov"
RAW_FILE = DATA_DIR / "raw_articles.json"
CLUSTERS_FILE = DATA_DIR / "clusters.json"
RESULTS_FILE = DATA_DIR / "pov_results.json"

CLUSTER_MODEL = "claude-haiku-4-5-20251001"

# ─── Collector config ────────────────────────────────────────────────────────

RSS_FEEDS = [
    {"source": "BBC Technology", "url": "http://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"source": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"source": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"source": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"source": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
]
MAX_PER_FEED = 10
MAX_SNIPPET = 400

# ─── Cluster config ──────────────────────────────────────────────────────────

MAX_ARTICLES_PER_CLUSTER = 5  # prevents fact-check contamination across events
MAX_CLUSTERS = 20
BATCH_SIZE = 40

# ─── Analyze config ──────────────────────────────────────────────────────────

DEFAULT_PROFILE = {
    "location": "Seoul, Korea",
    "occupation": "tech professional",
    "wealth_stage": "salaried professional",
    "interests": ["AI industry", "technology", "global business", "startups"],
}
OUTPUT_LANGUAGE = "ko"


def _client():
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set", file=sys.stderr)
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


# ─── Collector ───────────────────────────────────────────────────────────────

def _ns_strip(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find_text(elem, *tags) -> str:
    for tag in tags:
        found = elem.find(tag)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def _clean_snippet(raw: str, max_len: int) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", raw or "")
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_len]


def _normalize_date(raw: str) -> str:
    if not raw:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if len(raw) >= 10 and raw[4] == "-":
        return raw[:10]
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_feed(source: str, xml_bytes: bytes) -> list:
    articles = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return articles

    tag = _ns_strip(root.tag)

    if tag == "rss":
        for item in root.findall(".//item")[:MAX_PER_FEED]:
            title = _find_text(item, "title")
            link = _find_text(item, "link")
            desc = _find_text(item, "description")
            pub = _find_text(item, "pubDate")
            if not title or not link:
                continue
            articles.append({
                "source": source,
                "headline": title[:200],
                "snippet": _clean_snippet(desc, MAX_SNIPPET),
                "url": link,
                "published_date": _normalize_date(pub),
            })
    elif tag == "feed":
        ns = {"a": "http://www.w3.org/2005/Atom"}

        # NB: childless elements are falsy in ElementTree, so `find(x) or find(y)`
        # silently discards found elements — must compare against None.
        def _first(elem, *paths):
            for p in paths:
                found = elem.find(p, ns)
                if found is not None:
                    return found
            return None

        entries = root.findall("a:entry", ns) or root.findall("entry")
        for entry in entries[:MAX_PER_FEED]:
            title_el = _first(entry, "a:title", "title")
            title = title_el.text.strip() if (title_el is not None and title_el.text) else ""
            link_el = _first(entry, "a:link", "link")
            link = ""
            if link_el is not None:
                link = link_el.get("href", "") or link_el.text or ""
            summary_el = _first(entry, "a:summary", "summary")
            desc = summary_el.text.strip() if (summary_el is not None and summary_el.text) else ""
            pub_el = _first(entry, "a:updated", "a:published", "updated", "published")
            pub = pub_el.text.strip() if (pub_el is not None and pub_el.text) else ""
            if not title or not link:
                continue
            articles.append({
                "source": source,
                "headline": title[:200],
                "snippet": _clean_snippet(desc, MAX_SNIPPET),
                "url": link,
                "published_date": _normalize_date(pub),
            })
    return articles


def fetch_feed(source: str, url: str) -> list:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; POVNewsBot/1.0; +https://pov.news)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read(512 * 1024)
        articles = parse_feed(source, raw)
        print(f"  ✓ {source}: {len(articles)} articles")
        return articles
    except Exception as e:
        print(f"  ✗ {source}: {e}", file=sys.stderr)
        return []


def collect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_articles, seen = [], set()
    print("Collecting RSS feeds...")
    for feed in RSS_FEEDS:
        for a in fetch_feed(feed["source"], feed["url"]):
            if a["url"] not in seen:
                seen.add(a["url"])
                all_articles.append(a)
    RAW_FILE.write_text(json.dumps({
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_articles),
        "articles": all_articles,
    }, ensure_ascii=False, indent=2))
    print(f"\nSaved {len(all_articles)} articles → {RAW_FILE}")
    return all_articles


# ─── Cluster ─────────────────────────────────────────────────────────────────

CLUSTER_PROMPT = """You are given a list of news article headlines with their indices.
Group them by REAL-WORLD EVENT — articles that are about the exact same event/story should be in the same cluster.

Rules:
- Only group if articles are clearly about the SAME specific event (same company + same action, same person + same incident, etc.)
- Do NOT group thematically similar but distinct events
- Each cluster should have at most {max_per_cluster} articles
- Unclustered articles (unique events) each become their own single-article cluster
- Return ONLY valid JSON, no markdown, no preamble

Input format: list of {{"idx": <int>, "source": "<str>", "headline": "<str>"}}

Output format:
{{
  "clusters": [
    {{"event_label": "<1-sentence neutral description>", "article_indices": [<idx>, ...]}}
  ]
}}"""


def cluster_batch(client, articles: list, max_per_cluster: int) -> list:
    items = [{"idx": a["_idx"], "source": a["source"], "headline": a["headline"]} for a in articles]
    response = client.messages.create(
        model=CLUSTER_MODEL,
        max_tokens=4000,
        system=CLUSTER_PROMPT.format(max_per_cluster=max_per_cluster),
        messages=[{"role": "user", "content": json.dumps(items, ensure_ascii=False)}],
    )
    text = response.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text).get("clusters", [])


def _solo_cluster(a: dict) -> dict:
    return {
        "event_label": a["headline"],
        "articles": [{
            "index": 0, "source": a["source"], "headline": a["headline"],
            "snippet": a.get("snippet", ""), "url": a.get("url", ""),
            "published": a.get("published_date", ""),
        }],
    }


def cluster():
    if not RAW_FILE.exists():
        print(f"ERROR: {RAW_FILE} not found. Run collect first.", file=sys.stderr)
        sys.exit(1)
    raw = json.loads(RAW_FILE.read_text())
    articles = raw.get("articles", [])
    collected_at = raw.get("collected_at", "")
    if not articles:
        print("No articles to cluster.", file=sys.stderr)
        sys.exit(1)

    print(f"Clustering {len(articles)} articles...")
    for i, a in enumerate(articles):
        a["_idx"] = i

    client = _client()
    all_raw = []
    for start in range(0, len(articles), BATCH_SIZE):
        batch = articles[start: start + BATCH_SIZE]
        print(f"  Batch {start}–{start + len(batch) - 1}...")
        try:
            all_raw.extend(cluster_batch(client, batch, MAX_ARTICLES_PER_CLUSTER))
        except Exception as e:
            print(f"  ✗ Batch failed: {e}", file=sys.stderr)

    idx_to_article = {a["_idx"]: a for a in articles}
    final, used = [], set()
    for c in all_raw[:MAX_CLUSTERS]:
        valid = [i for i in c.get("article_indices", []) if i in idx_to_article and i not in used]
        if not valid:
            continue
        used.update(valid)
        cluster_articles = []
        for pos, idx in enumerate(valid[:MAX_ARTICLES_PER_CLUSTER]):
            a = idx_to_article[idx]
            cluster_articles.append({
                "index": pos, "source": a["source"], "headline": a["headline"],
                "snippet": a.get("snippet", ""), "url": a.get("url", ""),
                "published": a.get("published_date", ""),
            })
        final.append({"event_label": c.get("event_label", ""), "articles": cluster_articles})

    for a in articles:
        if a["_idx"] not in used and len(final) < MAX_CLUSTERS:
            final.append(_solo_cluster(a))

    CLUSTERS_FILE.write_text(json.dumps({
        "collected_at": collected_at,
        "clustered_at": datetime.now(timezone.utc).isoformat(),
        "total_clusters": len(final),
        "clusters": final,
    }, ensure_ascii=False, indent=2))
    print(f"\nSaved {len(final)} clusters → {CLUSTERS_FILE}")
    return final


# ─── Analyze ─────────────────────────────────────────────────────────────────

def cluster_hash(cluster: dict) -> str:
    urls = sorted(a.get("url", a.get("headline", "")) for a in cluster.get("articles", []))
    return hashlib.md5(json.dumps(urls).encode()).hexdigest()[:12]


def load_existing_results() -> dict:
    if not RESULTS_FILE.exists():
        return {}
    try:
        data = json.loads(RESULTS_FILE.read_text())
        return {r["_cluster_hash"]: r for r in data.get("results", []) if "_cluster_hash" in r}
    except Exception:
        return {}


def analyze():
    from services.pov import analyze_pov

    if not CLUSTERS_FILE.exists():
        print(f"ERROR: {CLUSTERS_FILE} not found. Run cluster first.", file=sys.stderr)
        sys.exit(1)
    raw = json.loads(CLUSTERS_FILE.read_text())
    clusters = raw.get("clusters", [])
    collected_at = raw.get("collected_at", "")
    if not clusters:
        print("No clusters to analyze.", file=sys.stderr)
        sys.exit(1)

    existing = load_existing_results()
    results, analyzed, skipped, failed = [], 0, 0, 0
    print(f"Analyzing {len(clusters)} clusters (profile: {DEFAULT_PROFILE['location']})...")

    for i, cluster in enumerate(clusters):
        ch = cluster_hash(cluster)
        if ch in existing:
            print(f"  [{i+1}/{len(clusters)}] skip (cached): {cluster['event_label'][:60]}")
            results.append(existing[ch])
            skipped += 1
            continue
        label = cluster.get("event_label", f"cluster-{i}")
        print(f"  [{i+1}/{len(clusters)}] analyzing: {label[:60]}...")
        try:
            user_input = {
                "event_id": f"feed-{ch}",
                "user_profile": DEFAULT_PROFILE,
                "articles": cluster["articles"],
                "output_language": OUTPUT_LANGUAGE,
            }
            pov = analyze_pov(user_input, OUTPUT_LANGUAGE)
            pov["_cluster_hash"] = ch
            pov["_event_label"] = label
            pov["_collected_at"] = collected_at
            results.append(pov)
            analyzed += 1
        except Exception as e:
            print(f"    ✗ Failed: {e}", file=sys.stderr)
            failed += 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "collected_at": collected_at,
        "profile": DEFAULT_PROFILE,
        "total": len(results),
        "analyzed": analyzed,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }, ensure_ascii=False, indent=2))
    print(f"\nDone: {analyzed} analyzed, {skipped} cached, {failed} failed → {RESULTS_FILE}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage == "collect":
        collect()
    elif stage == "cluster":
        cluster()
    elif stage == "analyze":
        analyze()
    elif stage == "all":
        collect()
        cluster()
        analyze()
    else:
        print(f"Unknown stage: {stage} (collect|cluster|analyze|all)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
