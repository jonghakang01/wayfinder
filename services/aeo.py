import html as _html
import json
import re

from services.llm_check import (
    PageParser,
    fetch_page,
    detect_page_type,
    get_cached_sitemap_urls,
    get_cached_gnb_products,
    RESULTS_FILE,
)

META = {
    "name": "AEO Analysis",
    "path": "/aeo",
    "icon": "🔍",
    "description": "AI search optimization score for samsung.com/us",
}

PAGE_TYPE_SKIP_EN = {
    "home":         {"Structured Data", "Spec Clarity", "Price & Availability", "Review Schema"},
    "product_line": {"Review Schema"},
    "product":      set(),
    "buy_flow":     {"FAQ Structure", "Spec Clarity"},
    "category":     {"Spec Clarity", "Review Schema", "Price & Availability"},
    "app":          {"Spec Clarity", "Price & Availability", "Review Schema"},
    "support":      {"Structured Data", "Spec Clarity", "Price & Availability", "Review Schema"},
    "other":        set(),
}

PAGE_TYPES_EN = {
    "home":         "Home",
    "product_line": "Product Line",
    "product":      "Product (PDP)",
    "buy_flow":     "Buy Flow",
    "category":     "Category",
    "app":          "App / Service",
    "support":      "Support",
    "other":        "Other",
}


# ── Independent English analysis functions ────────────────────────────────────

_SPEC_PATTERNS = [r'\d+\s*(GB|TB|MP|GHz|mAh|inch|″|mm|g\b|W\b|Hz|ch\b|dB)', r'\d+x\d+']

def _analyze_structured_data(parser):
    score = 0
    issues = []
    tips = []
    found_types = []
    for ld in parser.json_lds:
        t = ld.get("@type", "")
        found_types.append(t)
        if t == "Product":
            score += 15
            if "name" in ld:            score += 2
            if "description" in ld:     score += 2
            if "offers" in ld:          score += 3
            if "aggregateRating" in ld: score += 3
        elif t in ("FAQPage", "QAPage"):
            score += 10
        elif t == "BreadcrumbList":
            score += 3
        elif t:
            score += 2
    if not parser.json_lds:
        issues.append("No JSON-LD structured data found")
        tips.append("Add Product and FAQPage Schema.org markup")
    elif "Product" not in found_types:
        issues.append("No Product schema")
        tips.append("Product schema is required for product detail pages")
    score = min(score, 20)
    return {"score": score, "max": 20, "label": "Structured Data", "issues": issues, "tips": tips,
            "detail": f"Types found: {found_types or ['none']}"}


def _analyze_meta(parser):
    score = 0
    issues = []
    tips = []
    if parser.title:
        score += 3
    else:
        issues.append("No title tag")
    desc = parser.metas.get("description", "")
    if desc:
        score += 3
        if len(desc) < 50:
            issues.append(f"Meta description too short ({len(desc)} chars)")
            tips.append("Meta description should be 120–160 characters")
    else:
        issues.append("No meta description")
        tips.append("AI references the description when summarizing pages")
    if parser.metas.get("og:title"):       score += 2
    if parser.metas.get("og:description"): score += 1
    if parser.metas.get("og:image"):       score += 1
    if not parser.metas.get("og:title"):
        tips.append("Add Open Graph tags (optimizes social and AI sharing)")
    score = min(score, 10)
    return {"score": score, "max": 10, "label": "Meta Information", "issues": issues, "tips": tips,
            "detail": f"title: {parser.title[:50] or '-'}"}


def _analyze_content_structure(parser):
    score = 0
    issues = []
    tips = []
    h1s = parser.headings.count("h1")
    h2s = parser.headings.count("h2")
    h3s = parser.headings.count("h3")
    if h1s == 1:
        score += 6
    elif h1s == 0:
        issues.append("No H1 tag")
        tips.append("One H1 per page is required — AI uses it to identify the page topic")
    else:
        issues.append(f"{h1s} H1 tags found (1 recommended)")
    if h2s >= 2:
        score += 5
    elif h2s == 1:
        score += 2
        tips.append("Adding more H2 subheadings improves AI comprehension")
    else:
        issues.append("Insufficient H2 subheadings")
    if h3s >= 1:   score += 2
    if parser.tables >= 1:
        score += 2
    else:
        tips.append("Serving specs in table format improves AI parsing accuracy")
    score = min(score, 15)
    return {"score": score, "max": 15, "label": "Content Structure", "issues": issues, "tips": tips,
            "detail": f"H1:{h1s} H2:{h2s} H3:{h3s} Tables:{parser.tables}"}


def _analyze_spec_clarity(parser):
    score = 0
    issues = []
    tips = []
    if parser.tables >= 1:
        score += 6
        if parser.tables >= 3: score += 3
    if parser.lists >= 2:  score += 3
    elif parser.lists == 1: score += 1
    text = " ".join(parser.text_chunks)
    spec_hits = sum(len(re.findall(p, text, re.I)) for p in _SPEC_PATTERNS)
    if spec_hits >= 5:   score += 3
    elif spec_hits >= 2: score += 1
    dynamic_spec = False
    if parser.next_data_spec_tab:
        dynamic_spec = True
        if parser.tables == 0:
            score += 3
    kf_text = parser.next_data_key_feature
    if kf_text:
        kf_hits = sum(len(re.findall(p, kf_text, re.I)) for p in _SPEC_PATTERNS)
        if kf_hits >= 2 and spec_hits < 2:
            score += 1
    if parser.tables >= 1:
        pass
    elif dynamic_spec:
        issues.append("Spec data loaded via JavaScript — not crawlable by AI")
        tips.append("Include the spec table in static HTML so AI crawlers can read it without JavaScript")
    else:
        issues.append("No spec table found — content not parseable by AI")
        tips.append("Serving specs in a static HTML <table> allows AI crawlers to extract them directly")
    if spec_hits < 2 and (not kf_text or sum(len(re.findall(p, kf_text, re.I)) for p in _SPEC_PATTERNS) < 2):
        tips.append("Use consistent spec notation (GB, GHz, etc.) for reliable AI extraction")
    score = min(score, 15)
    detail_parts = [f"Lists:{parser.lists}", f"Spec values:{spec_hits}"]
    if dynamic_spec:
        detail_parts.append("Dynamic spec tab: detected")
    if parser.next_data_key_summary:
        detail_parts.append(f"Key features:{len(parser.next_data_key_summary)}")
    return {"score": score, "max": 15, "label": "Spec Clarity", "issues": issues, "tips": tips,
            "detail": " ".join(detail_parts)}


def _analyze_faq(parser):
    score = 0
    issues = []
    tips = []
    faq_ld = any(ld.get("@type") in ("FAQPage", "QAPage") for ld in parser.json_lds)
    if faq_ld:
        score += 10
    elif parser.faq_hints >= 3:
        score += 5
        tips.append("FAQ content detected — add FAQPage schema markup")
    else:
        issues.append("No FAQ structure found")
        tips.append("Adding a FAQ section improves AI answer accuracy")
    score = min(score, 10)
    return {"score": score, "max": 10, "label": "FAQ Structure", "issues": issues, "tips": tips,
            "detail": f"FAQ schema: {'yes' if faq_ld else 'no'}"}


def _analyze_text_clarity(parser):
    score = 0
    issues = []
    tips = []
    chunks = [t for t in parser.text_chunks if len(t) > 30]
    if len(chunks) >= 10: score += 3
    avg_len = sum(len(t) for t in chunks) / max(len(chunks), 1)
    if avg_len < 200:
        score += 2
    else:
        tips.append("Keep sentences short and clear — easier for AI to extract key facts")
    score = min(score, 5)
    return {"score": score, "max": 5, "label": "Text Clarity", "issues": issues, "tips": tips,
            "detail": f"{len(chunks)} text blocks, avg {int(avg_len)} chars"}


def _analyze_connectivity(parser, html=""):
    score = 0
    issues = []
    tips = []
    internal = len(re.findall(r'href=["\'](?:https?://www\.samsung\.com)?/us/[^"\']+["\']', html))
    eco_keywords = ["SmartThings", "Galaxy ecosystem", "compatible with", "works with", "pairs with"]
    eco_hits = sum(1 for kw in eco_keywords if re.search(re.escape(kw), html, re.I))
    if internal >= 10:  score += 5
    elif internal >= 4: score += 3
    elif internal >= 1: score += 1
    else:
        issues.append("No internal links — ecosystem connections invisible to AI")
    if eco_hits >= 2:   score += 5
    elif eco_hits == 1: score += 2
    else:
        issues.append("No ecosystem integration keywords found")
        tips.append("Adding SmartThings/Galaxy ecosystem info helps AI recognize Samsung's USP")
    score = min(score, 10)
    return {"score": score, "max": 10, "label": "Product Connectivity", "issues": issues, "tips": tips,
            "detail": f"Internal links:{internal} Ecosystem keywords:{eco_hits}"}


def _analyze_commerce(parser):
    score = 0
    issues = []
    tips = []
    has_offer = any(
        ld.get("@type") in ("Offer", "AggregateOffer") or
        (isinstance(ld.get("offers"), dict) and ld["offers"].get("@type") == "Offer")
        for ld in parser.json_lds
    )
    if has_offer:
        score += 5
    else:
        issues.append("No Offer schema — direct channel loses to Amazon/Best Buy in AI shopping results")
        tips.append("Add price, availability, and url fields to Offer schema")
    text = " ".join(parser.text_chunks)
    price_hits = len(re.findall(r'\$\s*[\d,]+(?:\.\d{2})?', text))
    if price_hits >= 1:
        score += 3
    else:
        tips.append("Include price as visible text — required for AI shopping result exposure")
    avail_kw = ["add to cart", "buy now", "in stock", "out of stock", "available"]
    avail_hits = sum(1 for kw in avail_kw if re.search(kw, text, re.I))
    if avail_hits >= 1:
        score += 2
    else:
        tips.append("Provide availability info (stock status, Add to Cart) as readable text")
    score = min(score, 10)
    return {"score": score, "max": 10, "label": "Price & Availability", "issues": issues, "tips": tips,
            "detail": f"Offer schema:{'yes' if has_offer else 'no'} Price mentions:{price_hits}"}


def _analyze_reviews(parser):
    score = 0
    issues = []
    tips = []
    rating_ld = None
    for ld in parser.json_lds:
        if "aggregateRating" in ld:
            rating_ld = ld["aggregateRating"]
            break
        if ld.get("@type") == "AggregateRating":
            rating_ld = ld
            break
    if rating_ld:
        score += 3
        if rating_ld.get("reviewCount") or rating_ld.get("ratingCount"): score += 1
        if rating_ld.get("ratingValue"):                                  score += 1
    else:
        issues.append("No AggregateRating schema found")
        tips.append("Mark up Samsung.com reviews with AggregateRating schema — official ratings will be cited in AI purchase queries")
    score = min(score, 5)
    rating_val    = rating_ld.get("ratingValue", "-")    if rating_ld else "-"
    review_count  = rating_ld.get("reviewCount", "-")    if rating_ld else "-"
    return {"score": score, "max": 5, "label": "Review Schema", "issues": issues, "tips": tips,
            "detail": f"Rating:{rating_val} Reviews:{review_count}"}


def analyze_url(url):
    if not url.startswith("http"):
        url = "https://" + url
    try:
        html = fetch_page(url)
    except Exception as e:
        return {"error": str(e)}

    parser = PageParser()
    parser.feed(html)

    page_type = detect_page_type(parser, url)
    skip = PAGE_TYPE_SKIP_EN.get(page_type, set())

    all_cats = [
        _analyze_structured_data(parser),
        _analyze_meta(parser),
        _analyze_content_structure(parser),
        _analyze_spec_clarity(parser),
        _analyze_faq(parser),
        _analyze_text_clarity(parser),
        _analyze_connectivity(parser, html),
        _analyze_commerce(parser),
        _analyze_reviews(parser),
    ]

    categories = []
    for c in all_cats:
        if c["label"] in skip:
            categories.append({**c, "skipped": True, "skip_reason": f"Not applicable for {PAGE_TYPES_EN.get(page_type, page_type)} pages"})
        else:
            categories.append(c)

    scored = [c for c in categories if not c.get("skipped")]
    total     = sum(c["score"] for c in scored)
    max_total = sum(c["max"]   for c in scored)
    all_tips  = [t for c in scored for t in c["tips"]]
    pct_score = int(total / max_total * 100) if max_total > 0 else 0
    grade = "A" if pct_score >= 80 else "B" if pct_score >= 60 else "C" if pct_score >= 40 else "D"

    return {
        "url": url, "total": total, "max": max_total, "grade": grade,
        "page_type": page_type, "page_track": parser.page_track,
        "categories": categories, "tips": all_tips,
    }


# ── English content definitions ───────────────────────────────────────────────

GRADE_GUIDE = {
    "A": ("AI Search Priority Source",    "samsung.com consistently appears as a primary cited source in ChatGPT, Perplexity, and Google AI Overview. Minimal misinformation risk after new product launches."),
    "B": ("Partial AI Visibility",         "Flagship products are well-exposed to AI, but secondary categories lose to third parties. Focus improvement on priority categories."),
    "C": ("AI Search Opportunity Loss",    "samsung.com is rarely used as an AI response source. High risk of misinformation spreading. Immediate improvement investment needed."),
    "D": ("Absent from AI Search",         "Effectively non-existent in the AI search ecosystem. Beyond a simple SEO issue — a brand trust risk. Platform architecture-level intervention required."),
}

CATEGORY_GUIDE = [
    {
        "label": "Structured Data",
        "max": 20,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 1.1.9 2 2 2h12a2 2 0 002-2V7M4 7l8-4 8 4M4 7h16"/>',
        "definition": "AI parses JSON-LD and Schema.org to extract product information.",
        "reason": "Without structured data, AI guesses specs and generates incorrect answers. After new product launches, misinformation spikes — and ChatGPT/Perplexity cites GSMArena and third parties instead of samsung.com.",
        "action": "Insert Product + Offer + AggregateRating schema as a standard block in product page templates.",
        "references": [
            ("Google: Structured Data for AI Overviews", "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data"),
            ("Google: How AI Overviews Work", "https://support.google.com/websearch/answer/14901683"),
            ("Schema.org Product / Offer / AggregateRating", "https://schema.org/Product"),
        ],
        "criteria": [
            (0, 5,  "No structured data — AI guesses specs, high misinformation risk"),
            (6, 12, "Basic schema exists but Product schema incomplete — partial spec errors"),
            (13, 20,"Product + Offer + Rating complete — qualifies as AI search primary source"),
        ],
    },
    {
        "label": "Meta Information",
        "max": 10,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>',
        "definition": "Title, Description, and OG tags are the first signals AI uses to identify a page.",
        "reason": "Generic titles cause AI to misclassify category pages as product pages. This leads to exclusion from Google AI Overview source panels and samsung.com links losing out to review sites in Perplexity.",
        "action": "Standardize meta titles to: [Model Name] | [Key Feature] | Samsung US",
        "references": [
            ("Google: AI Overviews Source Selection", "https://support.google.com/websearch/answer/14901683"),
            ("Google: Title & Meta Description Guidelines", "https://developers.google.com/search/docs/appearance/title-link"),
            ("Google: E-E-A-T & AI Source Trust", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"),
        ],
        "criteria": [
            (0, 3,  "Weak Title/Description — frequent AI page classification errors, dropped from Overview source panel"),
            (4, 7,  "Basic meta present but OG tags incomplete — suboptimal social/AI sharing"),
            (8, 10, "All meta complete — eligible for AI Overview source panel, clear page identity"),
        ],
    },
    {
        "label": "Content Structure",
        "max": 15,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"/>',
        "definition": "Proper heading hierarchy (H1–H3) enables AI to extract information by section.",
        "reason": "Without heading structure, AI cannot distinguish marketing copy from specs, causing section extraction failures. This is directly why samsung.com loses out in specific product queries.",
        "action": "Apply structured headings to all product pages: H1 (model name) → H2 (feature sections) → H3 (spec details)",
        "references": [
            ("Google: Crawlable Page Structure", "https://developers.google.com/search/docs/crawling-indexing/links-crawlable"),
            ("Google: Helpful Content System", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"),
            ("Google: Page Experience & Content Structure", "https://developers.google.com/search/docs/appearance/page-experience"),
        ],
        "criteria": [
            (0, 5,  "No heading structure — AI cannot separate marketing copy from specs, section extraction fails"),
            (6, 10, "Basic structure present but insufficient H2/H3 — partial section recognition errors"),
            (11, 15,"Clear hierarchy complete — AI can accurately extract information by section"),
        ],
    },
    {
        "label": "Spec Clarity",
        "max": 15,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 6h18M3 14h18M3 18h18"/>',
        "definition": "When spec data is provided as &lt;table&gt; or list elements, AI extracts it accurately.",
        "reason": "JS-rendered spec components cannot be read by AI crawlers. In comparison queries, Samsung's column appears blank, and AI shopping results favor Amazon and Best Buy over the official channel.",
        "action": "Provide static HTML &lt;table&gt; alongside JS components for crawler access (no design changes required).",
        "references": [
            ("Google: JavaScript & AI Crawler Accessibility", "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics"),
            ("Google: Product Structured Data — Spec Markup Guide", "https://developers.google.com/search/docs/appearance/structured-data/product"),
            ("Google: AI Overviews Factual Accuracy Standards", "https://support.google.com/websearch/answer/14901683"),
        ],
        "criteria": [
            (0, 5,  "No spec table — third-party sites gain authority, Samsung missing from AI comparisons"),
            (6, 10, "Partial spec structure, inconsistent units — partial AI recognition"),
            (11, 15,"Complete structured specs — Samsung data directly cited in AI comparison queries"),
        ],
    },
    {
        "label": "FAQ Structure",
        "max": 10,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>',
        "definition": "FAQPage schema is a direct declaration to AI that 'this question has this official answer.'",
        "reason": "Without FAQ, AI cites outdated Reddit/Quora information. Incorrect answers about warranty periods, water resistance ratings, and compatibility directly increase customer service costs, and competitor FAQs may appear in Samsung brand searches.",
        "action": "Extract top 20 CS ticket questions and add FAQPage schema Q&A sections at the bottom of product category pages.",
        "references": [
            ("Google: FAQPage Structured Data — AI Overview Q&A Citation", "https://developers.google.com/search/docs/appearance/structured-data/faqpage"),
            ("Google: How AI Overviews Utilize Q&A Content", "https://support.google.com/websearch/answer/14901683"),
            ("Schema.org FAQPage Specification", "https://schema.org/FAQPage"),
        ],
        "criteria": [
            (0, 2,  "No FAQ — AI cites outdated/unofficial Reddit & forum info as official answers"),
            (3, 7,  "FAQ content exists but no schema — AI cannot recognize Q&A structure"),
            (8, 10, "FAQPage schema complete — AI uses official Q&A in direct answers, CS costs reduced"),
        ],
    },
    {
        "label": "Text Clarity",
        "max": 5,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
        "definition": "AI extracts information more accurately from short, fact-focused sentences.",
        "reason": "With marketing language like 'Experience the ultimate innovation…', AI determines there are no extractable facts and selects CNET/Engadget reviews as primary sources. The official channel loses authority to unofficial channels.",
        "action": "Add a dedicated 'Key Specs' section to each product page with 5–7 fact-only bullet points in short sentences.",
        "references": [
            ("Google: Helpful Content System — Key Criteria for AI Overview Source Selection", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"),
            ("Google: E-E-A-T Evaluation Guide", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content#e-e-a-t"),
            ("Google: Writing Helpful Content Best Practices", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"),
        ],
        "criteria": [
            (0, 1, "Excessive marketing language — AI fact extraction fails, review sites become primary source"),
            (2, 3, "Partial fact sections present — AI can extract some information"),
            (4, 5, "Fact-focused short sentence structure — AI extraction optimized, official channel authority secured"),
        ],
    },
    {
        "label": "Product Connectivity",
        "max": 10,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>',
        "definition": "Internal links and ecosystem keywords help AI recognize relationships between Samsung products.",
        "reason": "Samsung's SmartThings/Galaxy ecosystem integration is a core USP, but poor inter-page connectivity means AI fails to recognize this strength. This is a direct cause of losing to competitors in queries like 'recommend devices that work with Galaxy phones.'",
        "action": "Add a 'Compatible Devices' section + internal links to each product page, and explicitly mention SmartThings integration in text.",
        "references": [
            ("Google: Crawlable Link Structure — AI Crawler Site Navigation", "https://developers.google.com/search/docs/crawling-indexing/links-crawlable"),
            ("Google: Knowledge Graph Entity Recognition — Product Relationship Understanding", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"),
            ("Google: AI Overviews Source Diversity & Related Page Connections", "https://support.google.com/websearch/answer/14901683"),
        ],
        "criteria": [
            (0, 3, "No connectivity — Samsung ecosystem strengths completely invisible to AI, ecosystem query opportunity lost"),
            (4, 7, "Some internal links — partial ecosystem recognition, systematic connectivity reinforcement needed"),
            (8, 10,"Full ecosystem connectivity — SmartThings/Galaxy integration fully recognized by AI, ecosystem queries captured"),
        ],
    },
    {
        "label": "Price & Availability",
        "max": 10,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/>',
        "definition": "Offer schema with price and inventory data determines AI shopping result visibility.",
        "reason": "ChatGPT Shopping and Google AI Overview shopping tabs are growing rapidly. Without Offer schema, samsung.com's direct sales channel loses to Amazon and Best Buy in AI shopping results, directly cutting direct channel margins.",
        "action": "Complete Offer schema with price, availability, and url fields. Consider real-time inventory integration.",
        "references": [
            ("Google: Product Structured Data (Offer/Price/Inventory) — AI Shopping Result Requirements", "https://developers.google.com/search/docs/appearance/structured-data/product"),
            ("Google: AI Overviews Shopping Feature — Offer Schema Requirements", "https://support.google.com/websearch/answer/14901683"),
            ("Google Merchant Center: Product Data Quality Guide", "https://support.google.com/merchants/answer/7052112"),
        ],
        "criteria": [
            (0, 3, "No Offer schema — direct channel completely displaced by Amazon/Best Buy in AI shopping"),
            (4, 7, "Basic price info but missing inventory/promotions — partial AI shopping exposure"),
            (8, 10,"Complete commerce signals — direct AI shopping tab exposure, direct channel competitiveness secured"),
        ],
    },
    {
        "label": "Review Schema",
        "max": 5,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>',
        "definition": "AggregateRating schema ensures Samsung's official ratings are reflected in AI purchase recommendations.",
        "reason": "AI heavily references review data when answering purchase consideration queries. Without schema, amazon.com and Best Buy reviews are prioritized over samsung.com's own ratings, degrading the trust of the official channel.",
        "action": "Complete AggregateRating schema with ratingValue, reviewCount, and bestRating fields.",
        "references": [
            ("Google: Review Snippet Structured Data — AI Purchase Recommendation Citation", "https://developers.google.com/search/docs/appearance/structured-data/review-snippet"),
            ("Google: How AI Overviews Use Rating Data", "https://support.google.com/websearch/answer/14901683"),
            ("Schema.org AggregateRating Specification", "https://schema.org/AggregateRating"),
        ],
        "criteria": [
            (0, 1, "No review schema — Amazon reviews prioritized over official ratings in purchase queries"),
            (2, 3, "AggregateRating present but missing reviewCount — AI judges rating as low confidence"),
            (4, 5, "Complete review schema — official samsung.com rating directly cited in AI purchase recommendations"),
        ],
    },
]

GUIDE_MAP = {c["label"]: c for c in CATEGORY_GUIDE}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get(body, key):
    v = body.get(key, "")
    return v[0] if isinstance(v, list) else (v or "")


# ── Render: Category Panel ────────────────────────────────────────────────────

def render_category_panel(current_page_type="other"):
    label_abbr = {
        "Structured Data": "Schema", "Meta Information": "Meta",
        "Content Structure": "Content", "Spec Clarity": "Specs",
        "FAQ Structure": "FAQ", "Text Clarity": "Text",
        "Product Connectivity": "Connectivity", "Price & Availability": "Price/Buy",
        "Review Schema": "Reviews",
    }
    all_labels = [c["label"] for c in CATEGORY_GUIDE]
    col_headers = "".join(
        f'<th style="padding:8px 6px;font-size:0.72rem;color:#475569;font-weight:600;'
        f'text-align:center;white-space:nowrap;border-bottom:2px solid #e2e8f0" title="{lb}">'
        f'{label_abbr.get(lb, lb[:6])}</th>'
        for lb in all_labels
    )
    example_urls = {
        "home": "/us/",
        "product_line": "/us/smartphones/galaxy-s26/",
        "product": "/us/smartphones/.../buy/galaxy-s26-256gb",
        "buy_flow": "/us/smartphones/galaxy-s26/buy/",
        "category": "/us/monitors/gaming/",
        "app": "/us/apps/samsung-health/",
        "support": "/us/support/",
        "other": "(other pages)",
    }
    type_rows = ""
    for i, (pt_key, pt_name) in enumerate(PAGE_TYPES_EN.items()):
        skip_set = PAGE_TYPE_SKIP_EN.get(pt_key, set())
        is_current = (pt_key == current_page_type)
        bg = "#faf5ff" if is_current else ("#ffffff" if i % 2 == 0 else "#fafafa")
        left_border = "border-left:3px solid #6d28d9;" if is_current else "border-left:3px solid transparent;"
        name_color = "#6d28d9" if is_current else "#1e293b"
        badge = ' <span style="font-size:0.65rem;background:#6d28d9;color:white;padding:1px 6px;border-radius:8px;margin-left:4px;font-weight:700">current</span>' if is_current else ""
        cells = "".join(
            f'<td style="text-align:center;padding:8px 4px;background:{bg}">'
            f'<span style="font-size:0.85rem;color:{"#10b981" if lb not in skip_set else "#d1d5db"};'
            f'font-weight:{"700" if lb not in skip_set else "400"}">{"✓" if lb not in skip_set else "—"}</span></td>'
            for lb in all_labels
        )
        ex = example_urls.get(pt_key, "")
        type_rows += (
            f'<tr>'
            f'<td style="padding:8px 14px;font-size:0.8rem;font-weight:{"700" if is_current else "600"};color:{name_color};'
            f'white-space:nowrap;background:{bg};{left_border}border-right:1px solid #f1f5f9">{pt_name}{badge}</td>'
            f'<td style="padding:8px 14px;font-size:0.72rem;color:#94a3b8;font-family:monospace;'
            f'white-space:nowrap;background:{bg};border-right:1px solid #e2e8f0">{ex}</td>'
            f'{cells}</tr>'
        )

    page_type_table = (
        '<div style="border-top:1px solid #e2e8f0;padding-top:20px;margin-top:8px">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
        '<span style="font-weight:700;color:#1e293b;font-size:0.88rem">🗂 Evaluation Scope by Page Type</span>'
        '<span style="font-size:0.72rem;color:#94a3b8">'
        '<span style="color:#10b981;font-weight:700">✓</span> Evaluated &nbsp;·&nbsp; '
        '<span style="color:#d1d5db;font-weight:700">—</span> Not applicable for this page type</span></div>'
        '<div style="overflow-x:auto;border-radius:10px;border:1px solid #e2e8f0;overflow:hidden">'
        '<table style="border-collapse:collapse;width:100%"><thead>'
        f'<tr style="background:#f8fafc">'
        f'<th style="padding:8px 14px;text-align:left;font-size:0.72rem;color:#64748b;font-weight:600;white-space:nowrap;border-bottom:2px solid #e2e8f0;border-right:1px solid #f1f5f9">Page Type</th>'
        f'<th style="padding:8px 14px;text-align:left;font-size:0.72rem;color:#64748b;font-weight:600;border-bottom:2px solid #e2e8f0;border-right:1px solid #e2e8f0">URL Example</th>'
        f'{col_headers}</tr></thead><tbody>{type_rows}</tbody></table></div></div>'
    )

    cards = ""
    for cat in CATEGORY_GUIDE:
        cards += f'''
        <div style="background:white;border:1px solid #e2e8f0;border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:8px">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <div style="width:36px;height:36px;background:#ede9fe;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <svg style="width:18px;height:18px" fill="none" stroke="#6d28d9" viewBox="0 0 24 24">{cat["icon"]}</svg>
            </div>
            <span style="font-weight:700;color:#1e293b;font-size:0.88rem">{cat["label"]}</span>
          </div>
          <p style="font-size:0.8rem;color:#475569;margin:0;line-height:1.5">{cat["definition"]}</p>
          <p style="font-size:0.75rem;color:#64748b;margin:0;line-height:1.5">{cat["reason"]}</p>
          <div style="margin-top:4px;padding:8px 10px;background:#f8fafc;border-radius:6px;font-size:0.75rem;color:#6d28d9">
            💡 {cat["action"]}
          </div>
        </div>'''

    grade_cards = ""
    grade_colors = {"A": "#10b981", "B": "#0ea5e9", "C": "#f59e0b", "D": "#ef4444"}
    for g, (title, desc) in GRADE_GUIDE.items():
        grade_cards += f'''
        <div style="display:flex;gap:10px;align-items:flex-start;padding:10px;border-radius:8px;background:white;border:1px solid #e2e8f0">
          <span style="font-weight:900;font-size:1.2rem;color:{grade_colors[g]};width:24px;flex-shrink:0">{g}</span>
          <div>
            <div style="font-weight:600;font-size:0.82rem;color:#1e293b">{title}</div>
            <div style="font-size:0.75rem;color:#64748b;margin-top:2px;line-height:1.4">{desc}</div>
          </div>
        </div>'''

    return f'''
<div style="margin-bottom:24px;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
  <div id="guide-header" onclick="toggleGuide()"
    style="display:flex;align-items:center;justify-content:space-between;padding:14px 20px;background:#f8fafc;border-left:4px solid #6d28d9;cursor:pointer;user-select:none">
    <div>
      <span style="font-weight:700;color:#1e293b;font-size:0.95rem">📋 Evaluation Criteria</span>
      <span style="margin-left:10px;font-size:0.78rem;color:#94a3b8">Samsung.com/us operator perspective — how each category impacts AI search</span>
    </div>
    <svg id="guide-chevron" style="width:18px;height:18px;transition:transform 0.3s;flex-shrink:0" fill="none" stroke="#6d28d9" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
    </svg>
  </div>
  <div id="guide-body" style="max-height:0;overflow:hidden;transition:max-height 0.4s ease;background:#f8fafc">
    <div style="padding:20px">
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">
        {cards}
      </div>
      <div style="border-top:1px solid #e2e8f0;padding-top:16px">
        <div style="font-weight:700;color:#1e293b;font-size:0.85rem;margin-bottom:10px">Overall Grade Thresholds</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">
          {grade_cards}
        </div>
      </div>
      {page_type_table}
    </div>
  </div>
</div>
<script>
function toggleGuide(){{
  const body = document.getElementById('guide-body');
  const chev = document.getElementById('guide-chevron');
  if(body.style.maxHeight==='0px'||!body.style.maxHeight){{
    body.style.maxHeight='2000px';
    chev.style.transform='rotate(180deg)';
  }}else{{
    body.style.maxHeight='0px';
    chev.style.transform='';
  }}
}}
</script>'''


# ── Render: Result ────────────────────────────────────────────────────────────

def render_result(r):
    pct = int(r["total"] / r["max"] * 100) if r.get("max") else 0
    grade_colors = {"A": "#10b981", "B": "#0ea5e9", "C": "#f59e0b", "D": "#ef4444"}
    g_color = grade_colors.get(r["grade"], "#64748b")

    # Summary
    non_skipped = [c for c in r["categories"] if not c.get("skipped") and c.get("max", 0) > 0]
    strengths = [c for c in non_skipped if int(c["score"] / c["max"] * 100) >= 70]
    weaknesses = sorted([c for c in non_skipped if int(c["score"] / c["max"] * 100) < 70], key=lambda c: c["score"] / c["max"])[:3]
    next_grades = {"D": ("C", 40), "C": ("B", 60), "B": ("A", 80), "A": (None, 100)}
    next_g, next_pct_thresh = next_grades[r["grade"]]
    if next_g:
        needed = max(0, (next_pct_thresh * r["max"] + 99) // 100 - r["total"])
        gap_text = f"+{needed} pts to reach {next_g}"
    else:
        gap_text = "Top grade achieved ✓"

    strength_items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;padding:3px 0">'
        f'<span style="width:6px;height:6px;background:#10b981;border-radius:50%;flex-shrink:0"></span>'
        f'<span style="font-size:0.8rem;color:#374151">{_html.escape(c["label"])}</span>'
        f'<span style="font-size:0.75rem;color:#10b981;margin-left:auto;font-weight:600">{int(c["score"]/c["max"]*100)}%</span>'
        f'</div>'
        for c in strengths
    ) or '<span style="font-size:0.8rem;color:#94a3b8">None</span>'

    weakness_items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;padding:3px 0">'
        f'<span style="width:6px;height:6px;background:#ef4444;border-radius:50%;flex-shrink:0"></span>'
        f'<span style="font-size:0.8rem;color:#374151">{_html.escape(c["label"])}</span>'
        f'<span style="font-size:0.75rem;color:#ef4444;margin-left:auto;font-weight:600">{int(c["score"]/c["max"]*100)}%</span>'
        f'</div>'
        for c in weaknesses
    ) or '<span style="font-size:0.8rem;color:#94a3b8">No issues found</span>'

    summary_html = f'''
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px">
      <div style="background:white;border-radius:12px;padding:16px;border:1px solid #e2e8f0">
        <div style="font-size:0.7rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">Overview</div>
        <div style="font-size:2.2rem;font-weight:900;color:{g_color};line-height:1">{r["grade"]}</div>
        <div style="font-size:0.82rem;color:#374151;margin-top:4px">{pct}% &middot; {r["total"]}/{r["max"]} pts</div>
        <div style="font-size:0.76rem;color:#64748b;margin-top:3px">{PAGE_TYPES_EN.get(r.get("page_type","other"), "Other")}</div>
        <div style="margin-top:10px;padding:6px 8px;background:#f5f3ff;border-radius:6px;font-size:0.75rem;color:#6d28d9;font-weight:600">{gap_text}</div>
      </div>
      <div style="background:white;border-radius:12px;padding:16px;border:1px solid #e2e8f0">
        <div style="font-size:0.7rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">Strengths (70%+)</div>
        {strength_items}
      </div>
      <div style="background:white;border-radius:12px;padding:16px;border:1px solid #e2e8f0">
        <div style="font-size:0.7rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">Needs Improvement</div>
        {weakness_items}
      </div>
    </div>'''

    # Grade legend
    grade_thresholds = {"A": "80%+", "B": "60–79%", "C": "40–59%", "D": "<40%"}
    grade_bgs = {"A": "#f0fdf4", "B": "#eff6ff", "C": "#fffbeb", "D": "#fef2f2"}
    grade_legend_html = ""
    for g, (title, _) in GRADE_GUIDE.items():
        gc = grade_colors[g]
        is_current = (g == r["grade"])
        border = f"2px solid {gc}" if is_current else f"1px solid {gc}33"
        shadow = f"box-shadow:0 0 0 3px {gc}22;" if is_current else ""
        grade_legend_html += f'''
        <div style="background:{grade_bgs[g]};border:{border};border-radius:10px;padding:12px 8px;text-align:center;{shadow}position:relative">
          {"<div style='position:absolute;top:-8px;right:-8px;background:#1e293b;color:white;font-size:0.65rem;padding:2px 6px;border-radius:10px'>current</div>" if is_current else ""}
          <div style="font-weight:900;font-size:1.3rem;color:{gc}">{g}</div>
          <div style="font-size:0.7rem;color:{gc};font-weight:600;margin-bottom:2px">{grade_thresholds[g]}</div>
          <div style="font-size:0.72rem;font-weight:600;color:#374151;line-height:1.3">{title}</div>
        </div>'''

    # Category rows
    cat_rows = ""
    for idx, c in enumerate(r["categories"]):
        c_pct = int(c["score"] / c["max"] * 100) if c.get("max") else 0
        bar_color = "#10b981" if c_pct >= 70 else "#f59e0b" if c_pct >= 40 else "#ef4444"
        issues_html = "".join(f'<li style="color:#ef4444">⚠ {_html.escape(i)}</li>' for i in c.get("issues", []))
        tips_html_inner = "".join(f'<li style="color:#0ea5e9">💡 {_html.escape(t)}</li>' for t in c.get("tips", []))

        guide = GUIDE_MAP.get(c["label"])
        toggle_id = f"cat-guide-{idx}"

        if c.get("skipped"):
            toggle_html = ""
        elif guide:
            tier_colors = ["#ef4444", "#f59e0b", "#10b981"]
            criteria_html = "".join(
                f'<div style="padding:4px 0;font-size:0.78rem;color:{tier_colors[min(i, 2)]}">'
                f'<span style="font-weight:600">{lo}–{hi} pts</span> — {_html.escape(desc)}</div>'
                for i, (lo, hi, desc) in enumerate(guide["criteria"])
            )
            refs_html = "".join(
                f'<a href="{url}" target="_blank" rel="noopener" style="display:block;font-size:0.75rem;color:#6d28d9;text-decoration:none;padding:2px 0">↗ {_html.escape(label)}</a>'
                for label, url in guide.get("references", [])
            )
            toggle_html = f'''
          <div style="margin-bottom:10px">
            <button onclick="var el=document.getElementById('{toggle_id}');el.style.display=el.style.display==='none'?'block':'none'"
              style="background:none;border:1px solid #e2e8f0;border-radius:6px;padding:4px 10px;font-size:0.75rem;color:#6d28d9;cursor:pointer">
              📐 View Scoring Rubric
            </button>
            <div id="{toggle_id}" style="display:none;margin-top:8px;background:#f8f7ff;border-radius:8px;padding:12px;border-left:3px solid #6d28d9">
              <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:8px;font-style:italic">This rubric explains what the category measures and why. For specific issues found on this page, see the improvement suggestions below.</div>
              <div style="font-size:0.8rem;color:#475569;margin-bottom:6px"><strong>Definition:</strong> {guide["definition"]}</div>
              <div style="font-size:0.8rem;color:#475569;margin-bottom:8px"><strong>AI Search Impact:</strong> {guide["reason"]}</div>
              <div style="border-top:1px solid #e2e8f0;padding-top:8px;margin-bottom:8px"><strong style="font-size:0.75rem;color:#64748b">Score Ranges</strong>{criteria_html}</div>
              {f'<div style="border-top:1px solid #e2e8f0;padding-top:8px"><strong style="font-size:0.75rem;color:#64748b">📚 References</strong><div style="margin-top:4px">{refs_html}</div></div>' if refs_html else ""}
            </div>
          </div>'''
        else:
            toggle_html = ""

        if c.get("skipped"):
            cat_rows += f'''
        <div style="background:#f8fafc;border-radius:12px;padding:14px 20px;margin-bottom:8px;border:1px dashed #e2e8f0;display:flex;align-items:center;gap:10px">
          <span style="font-size:0.85rem;color:#94a3b8">{_html.escape(c["label"])}</span>
          <span style="font-size:0.75rem;color:#cbd5e1;background:#f1f5f9;padding:2px 8px;border-radius:10px">Not applicable for this page type</span>
        </div>'''
        else:
            cat_rows += f'''
        <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:12px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
            <span style="font-weight:600;color:#1e293b">{c["label"]}</span>
            <span style="font-weight:700;color:{bar_color}">{c["score"]}/{c["max"]}</span>
          </div>
          <div style="background:#f1f5f9;border-radius:6px;height:8px;overflow:hidden;margin-bottom:10px">
            <div style="background:{bar_color};height:100%;width:{c_pct}%;transition:width 1s"></div>
          </div>
          <div style="font-size:0.78rem;color:#94a3b8;margin-bottom:8px">{_html.escape(c["detail"])}</div>
          {toggle_html}
          {"<ul style='font-size:0.82rem;padding-left:16px'>" + issues_html + tips_html_inner + "</ul>" if issues_html or tips_html_inner else ""}
        </div>'''

    # Improvement suggestions
    tips_blocks = ""
    has_any_tip = False
    for c in r["categories"]:
        if c.get("skipped") or (not c.get("issues") and not c.get("tips")):
            continue
        has_any_tip = True
        c_pct = int(c["score"] / c["max"] * 100) if c.get("max") else 0
        bar_color = "#10b981" if c_pct >= 70 else "#f59e0b" if c_pct >= 40 else "#ef4444"
        guide = GUIDE_MAP.get(c["label"])
        items_html = ""
        for issue in c.get("issues", []):
            items_html += f'<div style="display:flex;gap:8px;padding:6px 0;border-bottom:1px solid #fef2f2"><span style="color:#ef4444;flex-shrink:0">⚠</span><span style="font-size:0.85rem;color:#374151">{_html.escape(issue)}</span></div>'
        for tip in c.get("tips", []):
            items_html += f'<div style="display:flex;gap:8px;padding:6px 0;border-bottom:1px solid #f0fdf4"><span style="color:#6d28d9;flex-shrink:0">→</span><span style="font-size:0.85rem;color:#374151">{_html.escape(tip)}</span></div>'
        if guide:
            items_html += f'<div style="margin-top:8px;padding:8px 10px;background:#f5f3ff;border-radius:6px;font-size:0.82rem;color:#6d28d9"><strong>💡 Recommended Action:</strong> {_html.escape(guide["action"])}</div>'
        tips_blocks += f'''
        <div style="background:white;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);margin-bottom:10px">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
            <span style="font-weight:700;font-size:0.88rem;color:#1e293b">{_html.escape(c["label"])}</span>
            <span style="font-size:0.78rem;font-weight:600;color:{bar_color}">{c["score"]}/{c["max"]} pts</span>
          </div>
          {items_html}
        </div>'''

    if not has_any_tip:
        tips_blocks = "<div style='color:#94a3b8;font-size:0.88rem;padding:16px'>All categories look good — no improvements needed.</div>"

    recent_data = json.dumps({"url": r["url"], "grade": r["grade"], "pct": pct}, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AEO Result</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.score-card{{background:linear-gradient(135deg,#6d28d9,#4f46e5);color:white;border-radius:20px;padding:36px;text-align:center;margin-bottom:24px}}
.grade{{font-size:4rem;font-weight:900;line-height:1}}
.total-score{{font-size:1.2rem;opacity:0.9;margin-top:8px}}
.url-badge{{background:rgba(255,255,255,0.15);border-radius:8px;padding:6px 12px;font-size:0.8rem;word-break:break-all;margin-top:12px;display:inline-block;color:white;text-decoration:none}}
.url-badge:hover{{background:rgba(255,255,255,0.25)}}
.section-title{{font-size:1.1rem;font-weight:700;color:#1e293b;margin:24px 0 12px}}
.result-layout{{display:flex;gap:24px;max-width:1400px;margin:0 auto;padding:32px 40px}}
.result-main{{flex:1;min-width:0}}
.recent-sidebar{{width:210px;flex-shrink:0}}
.recent-panel{{position:sticky;top:20px;background:white;border-radius:12px;border:1px solid #e2e8f0;padding:14px}}
.recent-item{{display:block;padding:8px 0;border-bottom:1px solid #f1f5f9;text-decoration:none;color:inherit}}
.recent-item:last-child{{border-bottom:none}}
.recent-item:hover .recent-path{{color:#6d28d9}}
@media(max-width:900px){{.recent-sidebar{{display:none}}}}
</style></head><body>
<nav>
  <a href="/" style="color:white;font-weight:600;text-decoration:none">🧭 Wayfinder</a>
  <div style="display:flex;gap:16px">
    <a href="/aeo">← Analyze Again</a>
    <a href="/aeo/results">Batch Results</a>
  </div>
</nav>
<div class="result-layout">
  <div class="result-main">
    <div class="score-card">
      <div class="grade" style="color:{g_color}">{r["grade"]}</div>
      <div class="total-score">{r["total"]} / {r["max"]} pts ({pct}%)</div>
      <a class="url-badge" href="{_html.escape(r['url'])}" target="_blank" rel="noopener">{_html.escape(r["url"])} ↗</a>
      <div style="margin-top:10px;font-size:0.78rem;opacity:0.8">
        Page type: <strong>{PAGE_TYPES_EN.get(r.get("page_type","other"), "Other")}</strong>
        {f'<span style="margin-left:10px;background:rgba(255,255,255,0.15);padding:2px 8px;border-radius:4px">AA pageTrack: &quot;{_html.escape(r["page_track"])}&quot;</span>' if r.get("page_track") else ""}
      </div>
    </div>

    {summary_html}

    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:28px">
      {grade_legend_html}
    </div>

    {render_category_panel(r.get("page_type", "other"))}

    <div class="section-title">📊 Category Breakdown</div>
    <p style="font-size:0.8rem;color:#94a3b8;margin:-8px 0 12px">Click <strong style="color:#6d28d9">📐 View Scoring Rubric</strong> on any category to see its definition, AI search impact, and score range criteria.</p>
    {cat_rows}

    <div class="section-title">💡 Improvement Suggestions</div>
    <p style="font-size:0.8rem;color:#94a3b8;margin:-8px 0 12px">Specific issues found on this page and recommended actions. For category definitions and scoring criteria, refer to the rubrics above.</p>
    <div style="margin-bottom:32px">{tips_blocks}</div>
  </div>

  <div class="recent-sidebar">
    <div class="recent-panel">
      <div style="font-size:0.75rem;font-weight:700;color:#1e293b;margin-bottom:10px">🕐 Recent</div>
      <div id="recent-list"><div style="color:#cbd5e1;font-size:0.75rem">No history</div></div>
    </div>
  </div>
</div>
<script>
(function(){{
  var KEY='llm_recent_urls';
  var cur={recent_data};
  var gc={{A:'#10b981',B:'#0ea5e9',C:'#f59e0b',D:'#ef4444'}};
  var recent=[];
  try{{recent=JSON.parse(localStorage.getItem(KEY)||'[]');}}catch(e){{}}
  recent=recent.filter(function(x){{return x.url!==cur.url;}});
  cur.ts=new Date().toISOString();
  recent.unshift(cur);
  if(recent.length>10)recent=recent.slice(0,10);
  try{{localStorage.setItem(KEY,JSON.stringify(recent));}}catch(e){{}}
  var list=document.getElementById('recent-list');
  if(!recent.length)return;
  list.innerHTML=recent.map(function(item){{
    var color=gc[item.grade]||'#64748b';
    var raw=item.url.replace(/^https?:\/\/(www\.)?samsung\.com\/us/,'');
    var short=raw.length>26?raw.slice(0,23)+'...':raw||'/';
    var active=item.url===cur.url;
    return '<a class="recent-item" href="/aeo?url='+encodeURIComponent(item.url)+'">'
      +'<div style="display:flex;align-items:flex-start;gap:6px">'
      +'<span style="font-weight:900;font-size:0.78rem;color:'+color+';flex-shrink:0;margin-top:1px">'+item.grade+'</span>'
      +'<span class="recent-path" style="font-size:0.72rem;color:'+(active?'#6d28d9':'#374151')+';word-break:break-all;line-height:1.35;'+(active?'font-weight:600':'')+'">'+short+'</span>'
      +'</div>'
      +'<div style="font-size:0.68rem;color:#cbd5e1;margin-top:2px;margin-left:20px">'+item.pct+'%</div>'
      +'</a>';
  }}).join('');
}})();
</script>
</body></html>'''


# ── Render: Form (Landing Page) ───────────────────────────────────────────────

def render_form(error=""):
    err_html = f'<div class="error">{error}</div>' if error else ""
    gnb_groups = get_cached_gnb_products()
    if gnb_groups:
        preset_html = ""
        for cat, products in gnb_groups.items():
            if cat == "기타":
                continue
            cat_en = {
                "스마트폰": "Smartphones", "태블릿": "Tablets", "워치": "Watch",
                "오디오": "Audio", "컴퓨터": "Computers", "TV": "TV",
                "라이프스타일 TV": "Lifestyle TV", "모바일 스크린": "Mobile Screens",
                "모니터": "Monitors", "가전": "Appliances",
            }.get(cat, cat)
            btns = "".join(
                f'<button type="button" class="preset-btn" '
                f'onclick="document.getElementById(\'url\').value=\'{u}\';onUrlInput(\'{u}\')">'
                f'{n}</button>'
                for n, u in products
            )
            preset_html += (
                f'<div style="margin-bottom:10px">'
                f'<span style="font-size:0.72rem;font-weight:700;color:#94a3b8;'
                f'text-transform:uppercase;letter-spacing:0.04em;display:block;margin-bottom:4px">'
                f'{cat_en}</span>{btns}</div>'
            )
    else:
        preset_html = '<div style="color:#94a3b8;font-size:0.82rem">Loading...</div>'

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AEO Analysis · samsung.com/us</title>
<link rel="stylesheet" href="/static/style.css">
<style>
*{{box-sizing:border-box}}
.hero{{background:linear-gradient(150deg,#1e1148 0%,#3730a3 50%,#6d28d9 100%);color:white;padding:64px 0 80px;text-align:center;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 70% 50%,rgba(139,92,246,0.3) 0%,transparent 60%);pointer-events:none}}
.hero-eyebrow{{font-size:0.75rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:rgba(196,181,253,0.9);margin-bottom:16px}}
.hero-title{{font-size:2.4rem;font-weight:800;line-height:1.15;margin-bottom:16px;letter-spacing:-0.02em}}
.hero-title em{{font-style:normal;color:#a78bfa}}
.hero-sub{{font-size:1rem;color:rgba(255,255,255,0.75);max-width:480px;margin:0 auto 28px;line-height:1.6}}

.section{{max-width:760px;margin:0 auto;padding:0 16px}}
.how-strip{{background:white;border-radius:20px;padding:32px;box-shadow:0 4px 32px rgba(0,0,0,0.07);margin:-36px auto 0;position:relative;z-index:10;max-width:760px}}
.steps{{display:grid;grid-template-columns:repeat(3,1fr);gap:0}}
.step{{text-align:center;padding:0 16px;position:relative}}
.step+.step::before{{content:'→';position:absolute;left:-4px;top:20px;color:#cbd5e1;font-size:1.2rem}}
.step-num{{width:40px;height:40px;border-radius:50%;background:#f5f3ff;color:#6d28d9;font-weight:800;font-size:0.9rem;display:flex;align-items:center;justify-content:center;margin:0 auto 12px}}
.step-title{{font-weight:700;color:#1e293b;font-size:0.9rem;margin-bottom:4px}}
.step-desc{{font-size:0.78rem;color:#64748b;line-height:1.4}}
.feat-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:32px auto;max-width:760px;padding:0 16px}}
.feat-card{{background:white;border-radius:14px;padding:20px;border:1px solid #e2e8f0}}
.feat-icon{{font-size:1.6rem;margin-bottom:10px}}
.feat-title{{font-weight:700;color:#1e293b;font-size:0.9rem;margin-bottom:6px}}
.feat-desc{{font-size:0.78rem;color:#64748b;line-height:1.5}}
.grade-row{{display:flex;gap:6px;margin-top:10px}}
.g-badge{{flex:1;text-align:center;border-radius:6px;padding:4px 0;font-weight:800;font-size:0.85rem}}
.form-wrap{{max-width:760px;margin:0 auto 48px;padding:0 16px}}
.form-card{{background:white;border-radius:16px;padding:28px 32px;box-shadow:0 2px 16px rgba(0,0,0,0.06);border:1px solid #e2e8f0}}
.form-label{{font-weight:700;color:#1e293b;font-size:0.9rem;margin-bottom:10px;display:block}}
.url-input{{width:100%;padding:14px 16px;border:2px solid #e2e8f0;border-radius:10px;font-size:1rem;outline:none;transition:border 0.2s}}
.url-input:focus{{border-color:#6d28d9;box-shadow:0 0 0 3px rgba(109,40,217,0.08)}}
.analyze-btn{{width:100%;padding:14px;background:#6d28d9;color:white;border:none;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer;margin-top:10px;transition:background 0.2s}}
.analyze-btn:hover{{background:#5b21b6}}
.preset-btn{{padding:5px 11px;border:1px solid #e2e8f0;border-radius:16px;background:white;font-size:0.78rem;cursor:pointer;margin:3px;color:#64748b;transition:all 0.15s}}
.preset-btn:hover{{border-color:#6d28d9;color:#6d28d9;background:#faf5ff}}
.error{{background:#fee2e2;color:#dc2626;padding:12px;border-radius:8px;margin-bottom:12px;font-size:0.9rem}}
#suggest-box{{display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;background:white;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,0.12);z-index:200;max-height:280px;overflow-y:auto}}
.suggest-item{{padding:10px 14px;font-size:0.85rem;color:#374151;cursor:pointer;border-bottom:1px solid #f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:background 0.1s}}
.suggest-item:last-child{{border-bottom:none}}
.suggest-item:hover,.suggest-item.active{{background:#f5f3ff;color:#6d28d9}}
.suggest-status{{padding:8px 14px;font-size:0.78rem;color:#94a3b8;text-align:center}}
.recent-url-item{{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f1f5f9;text-decoration:none;color:inherit}}
.recent-url-item:last-child{{border-bottom:none}}
.recent-url-item:hover .rupath{{color:#6d28d9}}
</style></head><body>
<nav>
  <a href="/" style="color:white;font-weight:600;text-decoration:none">🧭 Wayfinder</a>
  <a href="/">← Home</a>
</nav>

<div class="hero">
  <div class="section">
    <div class="hero-eyebrow">AI Engine Optimization Audit</div>
    <h1 class="hero-title">samsung.com/us<br><em>AEO Page Diagnostic</em></h1>
    <p class="hero-sub">Measure how accurately AI search engines understand and cite a given page. Evaluates 9 criteria — including structured data, content structure, and spec readability — and surfaces prioritized improvement actions.</p>
  </div>
</div>

<div style="max-width:760px;margin:0 auto;padding:0 16px">
  <div class="how-strip">
    <div class="steps">
      <div class="step">
        <div class="step-num">1</div>
        <div class="step-title">Enter URL</div>
        <div class="step-desc">Paste any samsung.com/us page URL to analyze</div>
      </div>
      <div class="step">
        <div class="step-num">2</div>
        <div class="step-title">Auto Analysis</div>
        <div class="step-desc">9 categories checked automatically — structured data, meta, content, and more</div>
      </div>
      <div class="step">
        <div class="step-num">3</div>
        <div class="step-title">Grade + Actions</div>
        <div class="step-desc">Get an A–D score with actionable improvement steps per category</div>
      </div>
    </div>
  </div>
</div>

<div class="feat-grid">
  <div class="feat-card">
    <div class="feat-icon">📊</div>
    <div class="feat-title">9-Category Diagnosis</div>
    <div class="feat-desc">Structured data, meta tags, content structure, spec clarity, FAQ schema, price &amp; availability — all the signals that determine AI search visibility.</div>
  </div>
  <div class="feat-card">
    <div class="feat-icon">🎯</div>
    <div class="feat-title">Page-Type Aware Scoring</div>
    <div class="feat-desc">Automatically detects page type (Home, PDP, Category, Support…) and evaluates only the categories relevant to that type.</div>
    <div class="grade-row">
      <div class="g-badge" style="background:#f0fdf4;color:#10b981">A</div>
      <div class="g-badge" style="background:#eff6ff;color:#0ea5e9">B</div>
      <div class="g-badge" style="background:#fffbeb;color:#f59e0b">C</div>
      <div class="g-badge" style="background:#fef2f2;color:#ef4444">D</div>
    </div>
  </div>
  <div class="feat-card">
    <div class="feat-icon">💡</div>
    <div class="feat-title">Actionable Suggestions</div>
    <div class="feat-desc">Not just scores — every category includes specific issues found on the page and concrete next steps you can act on immediately.</div>
  </div>
</div>

<div style="max-width:760px;margin:-8px auto 24px;padding:0 16px">
  <div style="background:#fafafa;border:1px solid #e2e8f0;border-left:4px solid #94a3b8;border-radius:10px;padding:16px 20px">
    <div style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">Honest Disclaimer</div>
    <div style="font-size:0.82rem;color:#475569;line-height:1.7">
      <p style="margin-bottom:6px">✅ <strong>What you can trust:</strong> Structured data (JSON-LD), FAQ schema, and meta information are categories where Google's official documentation explicitly confirms influence on AI Overview exposure. Perplexity and similar real-time crawling AIs also directly read page structure.</p>
      <p style="margin-bottom:6px">⚠️ <strong>Limitations:</strong> The scoring weights (e.g., Structured Data = 20 pts) are set based on published guidelines — not empirically validated against actual AI citation rates. An A-grade page does not guarantee it will be cited by ChatGPT.</p>
      <p style="margin:0">📌 <strong>Best use:</strong> Treat this as a diagnostic reference tool for "how AI-friendly is this page structurally?" Use it to prioritize improvements, not as an absolute measure of AI search performance.</p>
    </div>
  </div>
</div>

<div class="form-wrap">
  <div class="form-card">
    {err_html}
    <label class="form-label" for="url">URL to Analyze</label>
    <form method="POST" action="/aeo" id="analyze-form" onsubmit="return submitForm()">
      <div style="position:relative">
        <input id="url" class="url-input" type="text" name="url"
          placeholder="https://www.samsung.com/us/... or type a path to search"
          autocomplete="off"
          oninput="onUrlInput(this.value)"
          onkeydown="onUrlKeydown(event)"
          onfocus="onUrlInput(this.value)"
          onblur="setTimeout(hideSuggest,200)">
        <div id="suggest-box"></div>
      </div>
      <button class="analyze-btn" type="submit">Analyze →</button>
    </form>

    <div style="margin-top:20px;padding-top:20px;border-top:1px solid #f1f5f9">
      <p style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">
        Quick Select <span style="font-weight:400;letter-spacing:0">— Latest products from samsung.com/us GNB</span>
      </p>
      {preset_html}
    </div>

    <div id="recent-section" style="display:none;margin-top:20px;padding-top:20px;border-top:1px solid #f1f5f9">
      <p style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">🕐 Recent</p>
      <div id="recent-url-list"></div>
    </div>
  </div>
</div>
<script>
let _suggestData = [];
let _activeIdx = -1;
let _fetchTimer = null;

(function loadRecent() {{
  var KEY = 'llm_recent_urls';
  var gc = {{A:'#10b981',B:'#0ea5e9',C:'#f59e0b',D:'#ef4444'}};
  var recent = [];
  try {{ recent = JSON.parse(localStorage.getItem(KEY) || '[]'); }} catch(e) {{}}
  if (!recent.length) return;
  var section = document.getElementById('recent-section');
  var list = document.getElementById('recent-url-list');
  section.style.display = 'block';
  list.innerHTML = recent.map(function(item) {{
    var color = gc[item.grade] || '#64748b';
    var path = item.url.replace(/^https?:\/\/(www\.)?samsung\.com\/us/, '') || '/';
    return '<a class="recent-url-item" href="/aeo?url=' + encodeURIComponent(item.url) + '">'
      + '<span style="font-weight:900;font-size:0.82rem;color:' + color + ';min-width:20px">' + item.grade + '</span>'
      + '<span style="font-size:0.75rem;font-weight:600;color:' + color + ';min-width:36px">' + item.pct + '%</span>'
      + '<span class="rupath" style="font-size:0.82rem;color:#374151;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + path + '</span>'
      + '</a>';
  }}).join('');
}})();

function onUrlInput(val) {{
  clearTimeout(_fetchTimer);
  _fetchTimer = setTimeout(() => fetchSuggest(val), 160);
}}
function fetchSuggest(val) {{
  const q = val.trim();
  fetch('/aeo/suggest?q=' + encodeURIComponent(q))
    .then(r => r.json())
    .then(d => showSuggest(d.urls, d.total, q))
    .catch(() => {{}});
}}
function showSuggest(urls, total, q) {{
  const box = document.getElementById('suggest-box');
  _suggestData = urls;
  _activeIdx = -1;
  if (!urls.length) {{ box.style.display = 'none'; return; }}
  const highlight = (url) => {{
    const lq = q.toLowerCase();
    const li = url.toLowerCase().indexOf(lq);
    if (!lq || li < 0) return escHtml(url);
    return escHtml(url.slice(0,li)) + '<strong style="color:#6d28d9">' + escHtml(url.slice(li,li+lq.length)) + '</strong>' + escHtml(url.slice(li+lq.length));
  }};
  box.innerHTML = urls.map((u) => {{
    const path = u.replace('https://www.samsung.com/us','') || '/';
    return `<div class="suggest-item" onmousedown="pickSuggest('${{escHtml(u)}}')">${{highlight(path)}}</div>`;
  }}).join('') + (total > urls.length
    ? `<div class="suggest-status">Showing top ${{urls.length}} of ${{total}} sitemap URLs</div>`
    : `<div class="suggest-status">${{total}} sitemap URLs loaded</div>`);
  box.style.display = 'block';
}}
function hideSuggest() {{
  document.getElementById('suggest-box').style.display = 'none';
  _activeIdx = -1;
}}
function pickSuggest(url) {{
  document.getElementById('url').value = url;
  hideSuggest();
}}
function onUrlKeydown(e) {{
  const box = document.getElementById('suggest-box');
  const items = box.querySelectorAll('.suggest-item');
  if (box.style.display === 'none' || !items.length) return;
  if (e.key === 'ArrowDown') {{
    e.preventDefault();
    _activeIdx = Math.min(_activeIdx + 1, items.length - 1);
  }} else if (e.key === 'ArrowUp') {{
    e.preventDefault();
    _activeIdx = Math.max(_activeIdx - 1, -1);
  }} else if (e.key === 'Enter' && _activeIdx >= 0) {{
    e.preventDefault();
    pickSuggest(_suggestData[_activeIdx]);
    return;
  }} else if (e.key === 'Escape') {{
    hideSuggest(); return;
  }} else {{ return; }}
  items.forEach((el, i) => el.classList.toggle('active', i === _activeIdx));
  if (_activeIdx >= 0) document.getElementById('url').value = _suggestData[_activeIdx];
}}
function submitForm() {{ hideSuggest(); return true; }}
function escHtml(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
</script>
</body></html>'''


# ── Route Handler ─────────────────────────────────────────────────────────────

def handle(method, path, body, ctx):
    # Sitemap autocomplete
    if path == "/aeo/suggest":
        q = _get(body, "q").strip().lower()
        urls = get_cached_sitemap_urls()
        if q:
            matched = [u for u in urls if q in u.lower()]
        else:
            matched = urls[:20]
        return ("json", {"urls": matched[:15], "total": len(urls)})

    # Single URL analysis — GET
    if method == "GET" and path == "/aeo":
        url = _get(body, "url").strip()
        if url:
            result = analyze_url(url)
            if "error" in result:
                return ("html", render_form(error=f"Failed to load page: {result['error']}"))
            return ("html", render_result(result))
        return ("html", render_form())

    # Single URL analysis — POST
    if method == "POST" and path == "/aeo":
        url = _get(body, "url").strip()
        if not url:
            return ("html", render_form(error="Please enter a URL"))
        result = analyze_url(url)
        if "error" in result:
            return ("html", render_form(error=f"Failed to load page: {result['error']}"))
        return ("html", render_result(result))

    return ("html", render_form())
