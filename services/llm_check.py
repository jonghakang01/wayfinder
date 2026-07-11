import html as _html
import json, os, re, urllib.request, urllib.error, threading, time
from html.parser import HTMLParser
from pathlib import Path

RESULTS_DIR = Path.home() / "projects" / "llm-compat"
RESULTS_FILE = RESULTS_DIR / "batch_results.json"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 배치 작업 상태 (메모리)
_batch_state = {"running": False, "done": 0, "total": 0, "results": [], "started": 0}

# 사이트맵 URL 캐시
_sitemap_cache: dict = {"urls": [], "loaded_at": 0}
_gnb_cache: dict = {"groups": {}, "loaded_at": 0}
_SITEMAP_TTL = 3600
_GNB_TTL = 604800  # 1주일

_GNB_CAT_MAP = [
    ("smartphones",                   "스마트폰"),
    ("audio-sound",                   "오디오"),
    ("audio-devices",                 "오디오"),
    ("tablets",                       "태블릿"),
    ("watches",                       "워치"),
    ("computers",                     "컴퓨터"),
    ("lifestyle-tvs",                 "라이프스타일 TV"),
    ("televisions-home-theater/tvs",  "TV"),
    ("movable-screens",               "모바일 스크린"),
    ("monitors",                      "모니터"),
    ("home-appliances",               "가전"),
]


def fetch_gnb_products():
    req = urllib.request.Request(
        "https://www.samsung.com/us/",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
    )
    html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
    nav_m = re.search(r'<nav[^>]*class="[^"]*gnb[^"]*"[^>]*>.*?</nav>', html, re.DOTALL)
    if not nav_m:
        return {}
    nav = nav_m.group(0)
    items = re.findall(
        r'<a class="nv00-gnb-v4__l1-menu-link"[^>]+an-la="([^"]+)"[^>]+href="([^"]+)"[^>]*>.*?'
        r'<span class="nv00-gnb-v4__l1-menu-text">([^<]+)</span>',
        nav, re.DOTALL
    )
    groups: dict = {}
    for an_la, href, name in items:
        if not re.match(r'L0_\d+_shop:', an_la):
            continue
        name = re.sub(r'&amp;', '&', name.strip())
        url = href if href.startswith('http') else f"https://www.samsung.com{href}"
        cat = "기타"
        for key, label in _GNB_CAT_MAP:
            if f"/us/{key}/" in url:
                cat = label
                break
        groups.setdefault(cat, []).append((name, url))
    return groups


def get_cached_gnb_products():
    now = time.time()
    if now - _gnb_cache["loaded_at"] < _GNB_TTL and _gnb_cache["groups"]:
        return _gnb_cache["groups"]
    try:
        groups = fetch_gnb_products()
        _gnb_cache["groups"] = groups
        _gnb_cache["loaded_at"] = now
    except Exception:
        pass
    return _gnb_cache["groups"]


def get_cached_sitemap_urls():
    now = time.time()
    if now - _sitemap_cache["loaded_at"] < _SITEMAP_TTL and _sitemap_cache["urls"]:
        return _sitemap_cache["urls"]
    try:
        urls = fetch_sitemap_urls(500)
        _sitemap_cache["urls"] = urls
        _sitemap_cache["loaded_at"] = now
    except Exception:
        pass
    return _sitemap_cache["urls"]


def _preload():
    try:
        get_cached_sitemap_urls()
    except Exception:
        pass
    try:
        get_cached_gnb_products()
    except Exception:
        pass


threading.Thread(target=_preload, daemon=True).start()

META = {
    "name": "AEO 페이지 진단",
    "path": "/llm-check",
    "icon": "🤖",
    "description": "AI 검색 최적화(AEO) 점수 분석",
    "bucket": True,
}

UA = "Mozilla/5.0 (compatible; LLMCompatChecker/1.0)"


# ── HTML Parser ──────────────────────────────────────────────────────────────

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.metas = {}
        self.headings = []
        self.json_lds = []
        self.scripts = []
        self.tables = 0
        self.lists = 0
        self.faq_hints = 0
        self.text_chunks = []
        self.page_track = ""   # Adobe Analytics digitalData.pageTrack
        # Samsung Next.js __NEXT_DATA__ derived signals
        self.next_data_spec_tab = False    # "Specs" tab exists in product navigation
        self.next_data_key_feature = ""    # keyFeature text from product data
        self.next_data_key_summary = []    # keySummary items (feature badges)
        self._in_title = False
        self._in_script = False
        self._script_type = ""
        self._script_id = ""
        self._script_buf = ""
        self._in_body = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs.get("name") or attrs.get("property") or ""
            content = attrs.get("content") or ""
            if name:
                self.metas[name.lower()] = content
        elif tag == "input":
            # <input id/name="pageTrack" value="...">
            if not self.page_track:
                field = attrs.get("id") or attrs.get("name") or ""
                if field.lower() == "pagetrack" and attrs.get("value"):
                    self.page_track = attrs["value"].strip()
        elif tag in ("h1","h2","h3","h4"):
            self.headings.append(tag)
        elif tag == "script":
            self._in_script = True
            self._script_type = attrs.get("type","")
            self._script_id = attrs.get("id","")
            self._script_buf = ""
        elif tag in ("table",):
            self.tables += 1
        elif tag in ("ul","ol"):
            self.lists += 1
        elif tag == "body":
            self._in_body = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_script = False
            if "application/ld+json" in self._script_type:
                try:
                    self.json_lds.append(json.loads(self._script_buf))
                except Exception:
                    pass
            elif self._script_id == "__NEXT_DATA__":
                self._parse_next_data(self._script_buf)
            else:
                # Adobe Analytics digitalData.pageTrack 캡처 (JSON 또는 JS assignment)
                if not self.page_track:
                    m = re.search(r'"pageTrack"\s*:\s*"([^"]+)"', self._script_buf)
                    if not m:
                        m = re.search(r'\.pageTrack\s*=\s*["\']([^"\']+)["\']', self._script_buf)
                    if m:
                        self.page_track = m.group(1).strip()
            self._script_buf = ""
            self._script_id = ""

    def _parse_next_data(self, buf):
        try:
            data = json.loads(buf)
            pp = data.get("props", {}).get("pageProps", {})
            static_data = pp.get("staticData", {})
            product_data = pp.get("productData", {})

            # Check for Specs tab in product navigation
            for nav_key in ("productNavigationV2", "productNavigationV3", "productNavigation"):
                nav = static_data.get(nav_key, {})
                nav_list = nav.get(nav_key, nav) if isinstance(nav, dict) else nav
                if isinstance(nav_list, list):
                    for item in nav_list:
                        if isinstance(item, dict) and item.get("title","").lower() in ("specs", "specifications"):
                            self.next_data_spec_tab = True
                            break

            # Extract keyFeature and keySummary from products
            default_model = product_data.get("modelCode","")
            products = product_data.get("products", [])
            target = next((p for p in products if p.get("modelCode") == default_model), None)
            if not target and products:
                target = products[0]
            if target:
                self.next_data_key_feature = target.get("keyFeature", "") or ""
                self.next_data_key_summary = target.get("keySummary", []) or []
        except Exception:
            pass

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_script:
            self._script_buf += data
        elif self._in_body and data.strip():
            t = data.strip()
            if len(t) > 20:
                self.text_chunks.append(t)
            if re.search(r'\b(faq|frequently asked|what is|how to|why|when)\b', t, re.I):
                self.faq_hints += 1


# ── Page Type Detection ──────────────────────────────────────────────────────

PAGE_TYPES = {
    "home":         "홈페이지",
    "product_line": "제품 라인업 페이지",   # /smartphones/galaxy-s26/
    "product":      "제품 상세 페이지",      # /buy/galaxy-s26-plus-256gb-sm-...
    "buy_flow":     "구매 선택 페이지",      # /galaxy-s26/buy (variant 미선택)
    "category":     "카테고리 리스팅",       # /monitors/gaming/ (필터/목록)
    "app":          "앱/서비스 페이지",
    "support":      "지원/고객센터 페이지",
    "other":        "기타 페이지",
}

# 페이지 타입별 평가 제외 카테고리 (해당 페이지에 애초에 없는 요소)
PAGE_TYPE_SKIP = {
    "home":         {"구조화 데이터", "스펙 명확성", "가격·구매 가용성", "리뷰 스키마"},
    "product_line": {"리뷰 스키마"},           # 라인업 전체 평점은 없음, 나머지는 모두 평가
    "product":      set(),                     # 모든 카테고리 평가
    "buy_flow":     {"FAQ 구조", "스펙 명확성"},
    "category":     {"스펙 명확성", "리뷰 스키마", "가격·구매 가용성"},
    "app":          {"스펙 명확성", "가격·구매 가용성", "리뷰 스키마"},
    "support":      {"구조화 데이터", "스펙 명확성", "가격·구매 가용성", "리뷰 스키마"},
    "other":        set(),
}

# Samsung 카테고리 슬러그 패턴 (제품명이 아닌 분류어)
_CATEGORY_SLUG_RE = re.compile(
    r'^(all-|view-all|shop-all)|^(gaming|oled|qled|neo-qled|frame|serif|lifestyle|'
    r'solid-state-drives|memory|all-monitors|smart-monitors|televisions|home-theater|'
    r'washers|dryers|refrigerators|dishwashers|ranges|microwaves|vacuums|air-purifiers|'
    r'unlocked-phones|prepaid-phones|flip-phones|fold-phones|galaxy-a|galaxy-m)$',
    re.I
)
# Samsung SKU 슬러그 패턴 (모델명 or SKU 포함)
_SKU_RE = re.compile(
    r'(sm-|ls|qn|un|ws|lf|mw|rf|nt|np|wf|wv|dw|ne|nz|me)[a-z0-9-]{5,}'
    r'|sku-[a-z0-9-]+'
    r'|-[a-z]{2}[a-z0-9]{4,}$'         # 끝에 붙는 색상/용량 코드
    r'|[a-z0-9]+-\d{3,}[a-z]{2,}',     # 모델번호 패턴
    re.I
)


def detect_page_type(parser, url):
    pt = parser.page_track.lower()
    path = url.replace("https://www.samsung.com/us", "").rstrip("/") or "/"
    segments = [s for s in path.split("/") if s]
    depth = len(segments)
    last = segments[-1] if segments else ""

    # ① pageTrack으로 명확히 식별되는 타입
    if pt == "home" or depth == 0:
        return "home"
    if "support" in pt or (segments and segments[0] == "support"):
        return "support"
    if "apps" in pt or (segments and segments[0] == "apps"):
        return "app"
    if "marketing" in pt:               # "im marketing page" = 제품 라인업 랜딩
        return "product_line"

    # ② URL 구조: buy 세그먼트 위치로 판별
    if "buy" in segments:
        buy_idx = segments.index("buy")
        if buy_idx < depth - 1:         # /buy/[sku-slug] → 특정 variant 상세
            return "product"
        else:                           # /product/buy (variant 미선택)
            return "buy_flow"

    # ③ JSON-LD + SKU 패턴으로 제품 상세 판별
    has_product_ld = any(ld.get("@type") == "Product" for ld in parser.json_lds)
    has_sku = bool(_SKU_RE.search(last))

    if has_product_ld and has_sku:
        return "product"

    # ④ 카테고리 리스팅 판별: 분류어 슬러그 or (prod_ld 있지만 sku 없고 depth≥3)
    is_category_slug = bool(_CATEGORY_SLUG_RE.search(last))
    if is_category_slug or (has_product_ld and not has_sku and depth >= 3):
        return "category"

    # ⑤ depth 1~2: 제품 라인업 페이지 (e.g. /smartphones/galaxy-s26/)
    if depth <= 2:
        return "product_line"

    # ⑥ depth 3+: 라인업의 서브 overview (대부분 product_line으로 취급)
    return "product_line"


def fetch_page(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        charset = "utf-8"
        ct = r.headers.get("Content-Type","")
        m = re.search(r"charset=([\w-]+)", ct)
        if m:
            charset = m.group(1)
        return r.read().decode(charset, errors="replace")


# ── Analyzers ────────────────────────────────────────────────────────────────

def analyze_structured_data(parser):
    score = 0
    issues = []
    tips = []
    found_types = []

    for ld in parser.json_lds:
        t = ld.get("@type","")
        found_types.append(t)
        if t == "Product":
            score += 15
            if "name" in ld: score += 2
            if "description" in ld: score += 2
            if "offers" in ld: score += 3
            if "aggregateRating" in ld: score += 3
        elif t in ("FAQPage","QAPage"):
            score += 10
        elif t in ("BreadcrumbList",):
            score += 3
        elif t:
            score += 2

    if not parser.json_lds:
        issues.append("JSON-LD 구조화 데이터 없음")
        tips.append("Product, FAQPage Schema.org 마크업 추가 권장")
    elif "Product" not in found_types:
        issues.append("Product 스키마 없음")
        tips.append("상품 페이지라면 Product 스키마 필수")

    score = min(score, 20)
    return {"score": score, "max": 20, "label": "구조화 데이터", "issues": issues, "tips": tips, "detail": f"발견된 타입: {found_types or ['없음']}"}


def analyze_meta(parser):
    score = 0
    issues = []
    tips = []

    if parser.title:
        score += 3
    else:
        issues.append("title 태그 없음")

    desc = parser.metas.get("description","")
    if desc:
        score += 3
        if len(desc) < 50:
            issues.append(f"description 너무 짧음 ({len(desc)}자)")
            tips.append("description은 120~160자 권장")
    else:
        issues.append("meta description 없음")
        tips.append("AI가 페이지 요약 시 description을 참조함")

    if parser.metas.get("og:title"): score += 2
    if parser.metas.get("og:description"): score += 1
    if parser.metas.get("og:image"): score += 1
    if not parser.metas.get("og:title"):
        tips.append("Open Graph 태그 추가 권장 (소셜/AI 공유 최적화)")

    score = min(score, 10)
    return {"score": score, "max": 10, "label": "메타 정보", "issues": issues, "tips": tips, "detail": f"title: {parser.title[:50] or '-'}"}


def analyze_structure(parser):
    score = 0
    issues = []
    tips = []

    h1s = parser.headings.count("h1")
    h2s = parser.headings.count("h2")
    h3s = parser.headings.count("h3")

    if h1s == 1:
        score += 6
    elif h1s == 0:
        issues.append("H1 태그 없음")
        tips.append("페이지당 H1 하나 필수 — AI가 주제 파악에 사용")
    elif h1s > 1:
        issues.append(f"H1이 {h1s}개 (1개 권장)")

    if h2s >= 2:
        score += 5
    elif h2s == 1:
        score += 2
        tips.append("H2 소제목을 더 추가하면 AI 이해도 향상")
    else:
        issues.append("H2 소제목 부족")

    if h3s >= 1: score += 2
    if parser.tables >= 1: score += 2
    else:
        tips.append("스펙은 테이블 형태로 제공 시 AI 파싱 정확도 향상")

    score = min(score, 15)
    return {"score": score, "max": 15, "label": "콘텐츠 구조", "issues": issues, "tips": tips, "detail": f"H1:{h1s} H2:{h2s} H3:{h3s} 테이블:{parser.tables}"}


def analyze_spec_clarity(parser):
    score = 0
    issues = []
    tips = []

    # ── 정적 HTML 신호 ──────────────────────────────────────────
    if parser.tables >= 1:
        score += 6
        if parser.tables >= 3: score += 3

    if parser.lists >= 2: score += 3
    elif parser.lists == 1: score += 1

    text = " ".join(parser.text_chunks)
    spec_patterns = [r'\d+\s*(GB|TB|MP|GHz|mAh|inch|″|mm|g\b|W\b|Hz|ch\b|dB)', r'\d+x\d+']
    spec_hits = sum(len(re.findall(p, text, re.I)) for p in spec_patterns)
    if spec_hits >= 5: score += 3
    elif spec_hits >= 2: score += 1

    # ── Next.js __NEXT_DATA__ 신호 (Samsung PDP 동적 페이지) ────
    dynamic_spec = False
    if parser.next_data_spec_tab:
        # Specs 탭 존재 → 스펙은 있으나 JS 동적 로드
        dynamic_spec = True
        if parser.tables == 0:
            score += 3   # 스펙 존재 부분 점수 (테이블 없음 감점 상쇄)

    # keyFeature 텍스트에서 수치 탐지
    kf_text = parser.next_data_key_feature
    if kf_text:
        kf_hits = sum(len(re.findall(p, kf_text, re.I)) for p in spec_patterns)
        if kf_hits >= 2 and spec_hits < 2:
            score += 1   # 키 피처에서만 수치 발견 시 소량 가점

    # ── 이슈 / 팁 결정 ────────────────────────────────────────
    if parser.tables >= 1:
        pass  # 정적 테이블 있음 → 이슈 없음
    elif dynamic_spec:
        issues.append("스펙 데이터가 JavaScript 동적 로드 방식으로 제공됨")
        tips.append("스펙 테이블을 정적 HTML <table>에 포함 시 AI 크롤러가 직접 추출 가능")
    else:
        issues.append("스펙 테이블 없음 또는 파싱 불가")
        tips.append("스펙을 <table> 태그로 제공 시 AI가 정확히 추출 가능")

    if spec_hits < 2 and (not kf_text or sum(len(re.findall(p, kf_text, re.I)) for p in spec_patterns) < 2):
        tips.append("스펙 수치(GB, GHz 등) 표기 방식을 일관되게 유지 권장")

    score = min(score, 15)
    detail_parts = [f"리스트:{parser.lists}개", f"스펙수치:{spec_hits}개"]
    if dynamic_spec:
        detail_parts.append("동적스펙탭:감지")
    if parser.next_data_key_summary:
        detail_parts.append(f"키피처:{len(parser.next_data_key_summary)}개")
    return {"score": score, "max": 15, "label": "스펙 명확성", "issues": issues, "tips": tips, "detail": " ".join(detail_parts)}


def analyze_faq(parser):
    score = 0
    issues = []
    tips = []

    faq_ld = any(ld.get("@type") in ("FAQPage","QAPage") for ld in parser.json_lds)
    if faq_ld:
        score += 10
    elif parser.faq_hints >= 3:
        score += 5
        tips.append("FAQ 콘텐츠 발견 — FAQPage Schema로 마크업 추가 권장")
    else:
        issues.append("FAQ 구조 없음")
        tips.append("'자주 묻는 질문' 섹션 추가 시 AI 답변 정확도 향상")

    score = min(score, 10)
    return {"score": score, "max": 10, "label": "FAQ 구조", "issues": issues, "tips": tips, "detail": f"FAQ 스키마: {'있음' if faq_ld else '없음'}"}


def analyze_text_clarity(parser):
    score = 0
    issues = []
    tips = []

    chunks = [t for t in parser.text_chunks if len(t) > 30]
    if len(chunks) >= 10: score += 3

    avg_len = sum(len(t) for t in chunks) / max(len(chunks), 1)
    if avg_len < 200:
        score += 2
    else:
        tips.append("문장을 짧고 명확하게 유지 — AI가 핵심 추출 용이")

    score = min(score, 5)
    return {"score": score, "max": 5, "label": "텍스트 명확성", "issues": issues, "tips": tips, "detail": f"텍스트 블록 {len(chunks)}개 평균 {int(avg_len)}자"}


def analyze_entity_links(parser, html=""):
    score = 0
    issues = []
    tips = []

    internal = len(re.findall(r'href=["\'](?:https?://www\.samsung\.com)?/us/[^"\']+["\']', html))
    eco_keywords = ["SmartThings", "Galaxy ecosystem", "compatible with", "works with", "pairs with"]
    eco_hits = sum(1 for kw in eco_keywords if re.search(re.escape(kw), html, re.I))

    if internal >= 10: score += 5
    elif internal >= 4: score += 3
    elif internal >= 1: score += 1
    else:
        issues.append("내부 링크 없음 — 생태계 연결 구조가 AI에 비가시")

    if eco_hits >= 2: score += 5
    elif eco_hits == 1: score += 2
    else:
        issues.append("생태계 연동 키워드 없음")
        tips.append("SmartThings·Galaxy 생태계 연동 정보 추가 시 AI가 삼성 USP 인식")

    score = min(score, 10)
    return {"score": score, "max": 10, "label": "제품 간 연결성", "issues": issues, "tips": tips, "detail": f"내부링크:{internal}개 생태계키워드:{eco_hits}개"}


def analyze_commerce(parser):
    score = 0
    issues = []
    tips = []

    has_offer = any(
        ld.get("@type") in ("Offer","AggregateOffer") or
        (isinstance(ld.get("offers"), dict) and ld["offers"].get("@type") == "Offer")
        for ld in parser.json_lds
    )
    if has_offer:
        score += 5
    else:
        issues.append("Offer 스키마 없음 — AI 쇼핑에서 아마존·베스트바이에 직판 채널이 밀림")
        tips.append("Offer 스키마에 price·availability·url 추가 필수")

    text = " ".join(parser.text_chunks)
    price_hits = len(re.findall(r'\$\s*[\d,]+(?:\.\d{2})?', text))
    if price_hits >= 1: score += 3
    else:
        tips.append("가격 정보를 텍스트로도 명시 — AI 쇼핑 결과 노출에 필요")

    avail_kw = ["add to cart", "buy now", "in stock", "out of stock", "available"]
    avail_hits = sum(1 for kw in avail_kw if re.search(kw, text, re.I))
    if avail_hits >= 1: score += 2
    else:
        tips.append("구매 가용성 정보(재고, Add to Cart) 텍스트로 제공 권장")

    score = min(score, 10)
    return {"score": score, "max": 10, "label": "가격·구매 가용성", "issues": issues, "tips": tips, "detail": f"Offer스키마:{'있음' if has_offer else '없음'} 가격표기:{price_hits}개"}


def analyze_reviews(parser):
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
        if rating_ld.get("ratingValue"): score += 1
    else:
        issues.append("AggregateRating 스키마 없음")
        tips.append("삼성닷컴 자체 리뷰를 AggregateRating 스키마로 마크업 — AI 구매 추천 쿼리에서 공식 평점 인용")

    score = min(score, 5)
    review_count = rating_ld.get("reviewCount", "-") if rating_ld else "-"
    rating_val = rating_ld.get("ratingValue", "-") if rating_ld else "-"
    return {"score": score, "max": 5, "label": "리뷰 스키마", "issues": issues, "tips": tips, "detail": f"평점:{rating_val} 리뷰수:{review_count}"}


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
    skip = PAGE_TYPE_SKIP.get(page_type, set())

    all_cats = [
        analyze_structured_data(parser),
        analyze_meta(parser),
        analyze_structure(parser),
        analyze_spec_clarity(parser),
        analyze_faq(parser),
        analyze_text_clarity(parser),
        analyze_entity_links(parser, html),
        analyze_commerce(parser),
        analyze_reviews(parser),
    ]

    categories = []
    for c in all_cats:
        if c["label"] in skip:
            categories.append({**c, "skipped": True, "skip_reason": f"{PAGE_TYPES[page_type]}에 해당 없음"})
        else:
            categories.append(c)

    scored = [c for c in categories if not c.get("skipped")]
    total = sum(c["score"] for c in scored)
    max_total = sum(c["max"] for c in scored)
    all_tips = [t for c in scored for t in c["tips"]]
    pct_score = int(total / max_total * 100) if max_total > 0 else 0
    grade = "A" if pct_score >= 80 else "B" if pct_score >= 60 else "C" if pct_score >= 40 else "D"

    return {
        "url": url, "total": total, "max": max_total, "grade": grade,
        "page_type": page_type, "page_track": parser.page_track,
        "categories": categories, "tips": all_tips,
    }


# ── Sitemap & Batch ──────────────────────────────────────────────────────────

SITEMAPS = [
    "https://www.samsung.com/us/top_sitemap.xml",
    "https://www.samsung.com/us/us-b2c-sitemap.xml",
]
SKIP_PATTERNS = re.compile(r'/(app|set-login|qrservice|reserve|tvs/2023|s10|s8|s9|note9|note10)/|#')


def fetch_sitemap_urls(limit=100):
    urls = []
    seen = set()
    for sitemap in SITEMAPS:
        if len(urls) >= limit:
            break
        try:
            req = urllib.request.Request(sitemap, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=10) as r:
                xml = r.read().decode("utf-8", errors="replace")
            found = re.findall(r'<loc>(https://www\.samsung\.com/us/[^<]+)</loc>', xml)
            for u in found:
                u = u.strip()
                if u not in seen and not SKIP_PATTERNS.search(u):
                    seen.add(u)
                    urls.append(u)
                if len(urls) >= limit:
                    break
        except Exception:
            continue
    return urls[:limit]


def _run_batch(urls):
    global _batch_state
    sem = threading.Semaphore(8)  # 최대 8개 동시

    def worker(url):
        with sem:
            try:
                result = analyze_url(url)
                result["url"] = url
            except Exception as e:
                result = {"url": url, "error": str(e), "total": 0, "grade": "-"}
            _batch_state["results"].append(result)
            _batch_state["done"] += 1

    threads = [threading.Thread(target=worker, args=(u,), daemon=True) for u in urls]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 점수순 정렬 후 파일 저장
    _batch_state["results"].sort(key=lambda x: x.get("total", 0), reverse=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({
        "urls": urls,
        "results": _batch_state["results"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M"),
    }, ensure_ascii=False, indent=2))
    _batch_state["running"] = False


def start_batch():
    global _batch_state
    if _batch_state["running"]:
        return False
    urls = fetch_sitemap_urls(100)
    _batch_state = {"running": True, "done": 0, "total": len(urls), "results": [], "started": time.time()}
    threading.Thread(target=_run_batch, args=(urls,), daemon=True).start()
    return True


# ── LLM Chat ─────────────────────────────────────────────────────────────────

def build_analysis_context(result):
    url = result.get("url", "")
    total = result.get("total", 0)
    grade = result.get("grade", "-")
    categories = result.get("categories", [])
    page_type = result.get("page_type", "other")

    scored = [c for c in categories if not c.get("skipped")]
    skipped = [c for c in categories if c.get("skipped")]
    max_total = sum(c.get("max", 0) for c in scored)
    pct_score = int(total / max_total * 100) if max_total > 0 else 0

    # 다음 등급까지 갭 계산
    grade_thresholds = {"A": 80, "B": 60, "C": 40}
    next_grade_gap = ""
    for g, thr in grade_thresholds.items():
        needed_pct = thr
        needed_pts = max(0, round(needed_pct * max_total / 100) - total)
        if pct_score < needed_pct:
            next_grade_gap = f"{g}등급까지 {needed_pts}점 필요 ({needed_pct}% 기준)"
            break

    cat_lines = []
    for c in scored:
        guide = next((g for g in CATEGORY_GUIDE if g["label"] == c["label"]), None)
        cpct = int(c["score"] / c["max"] * 100) if c["max"] else 0
        tier = "높음(≥70%)" if cpct >= 70 else "보통(40~69%)" if cpct >= 40 else "낮음(<40%)"
        issues = ", ".join(c.get("issues", [])) or "없음"
        tips = ", ".join(c.get("tips", [])) or "없음"
        cat_lines.append(
            f"## {c['label']} [{c['score']}/{c['max']}점, {cpct}%, 수준:{tier}]\n"
            f"- 세부 현황: {c.get('detail', '')}\n"
            f"- 발견된 이슈: {issues}\n"
            f"- 개선 팁: {tips}\n"
            f"- AI 검색 영향: {guide['reason'] if guide else ''}\n"
            f"- 권장 액션: {guide['action'] if guide else ''}"
        )

    skipped_labels = ", ".join(f"{c['label']}({c.get('skip_reason','')})" for c in skipped) or "없음"

    return f"""당신은 AEO(AI Engine Optimization) 전문가입니다. 아래는 {url} 페이지의 LLM 호환성 분석 결과입니다.
삼성닷컴 운영자 관점에서, AI 검색(ChatGPT, Perplexity, Google AI Overview) 노출 개선에 집중하세요.
분석 데이터를 근거로 구체적이고 실행 가능한 조언을 제공하세요.

# 분석 대상
- URL: {url}
- 페이지 유형: {PAGE_TYPES.get(page_type, page_type)}
- 종합 등급: {grade} ({total}/{max_total}점, {pct_score}%)
- 등급 갭: {next_grade_gap or "최고 등급(A) 달성"}
- 평가 제외 카테고리: {skipped_labels}

# 카테고리별 상세 분석 (평가 대상만)
{chr(10).join(cat_lines)}

# 핵심 개선 우선순위
{chr(10).join(f'- {t}' for t in result.get('tips', []))}

# 대화 지침
- 이 페이지 유형({PAGE_TYPES.get(page_type, page_type)})에 맞는 조언만 제공
- 평가 제외 카테고리({skipped_labels})는 이 페이지에 해당 없음을 명시
- 점수가 낮은 항목부터 우선순위 조언
- 삼성닷컴 개발팀이 실제 구현할 수 있는 수준의 구체적 조치 제안
"""


def call_claude(messages, system_prompt):
    if not ANTHROPIC_API_KEY:
        return "ANTHROPIC_API_KEY가 설정되지 않았습니다. 환경 변수를 확인해주세요."
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "system": system_prompt,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        return f"API 오류: {e.code} — {err[:200]}"
    except Exception as e:
        return f"오류: {e}"


def call_claude_stream(messages, system_prompt):
    if not ANTHROPIC_API_KEY:
        yield "data: " + json.dumps({"text": "ANTHROPIC_API_KEY가 설정되지 않았습니다."}) + "\n\n"
        yield "data: [DONE]\n\n"
        return
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "stream": True,
        "system": system_prompt,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            for raw in r:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    ev = json.loads(data_str)
                    if ev.get("type") == "content_block_delta":
                        text = ev.get("delta", {}).get("text", "")
                        if text:
                            yield "data: " + json.dumps({"text": text}) + "\n\n"
                except Exception:
                    continue
    except urllib.error.HTTPError as e:
        err = e.read().decode()[:200]
        yield "data: " + json.dumps({"text": f"API 오류: {e.code} — {err}"}) + "\n\n"
    except Exception as e:
        yield "data: " + json.dumps({"text": f"오류: {e}"}) + "\n\n"
    yield "data: [DONE]\n\n"


# ── Handler ──────────────────────────────────────────────────────────────────

def _get(body, key):
    v = body.get(key, "")
    return v[0] if isinstance(v, list) else (v or "")


def handle(method, path, body, ctx):
    # URL 자동완성 API
    if path == "/llm-check/suggest":
        q = _get(body, "q").strip().lower()
        urls = get_cached_sitemap_urls()
        if q:
            matched = [u for u in urls if q in u.lower()][:12]
        else:
            matched = urls[:12]
        return ("json", {"urls": matched, "total": len(urls)})

    # 배치 상태 API
    if path == "/llm-check/status":
        s = _batch_state
        return ("json", {
            "running": s["running"],
            "done": s["done"],
            "total": s["total"],
            "pct": int(s["done"] / max(s["total"], 1) * 100),
        })

    # 배치 시작
    if method == "POST" and path == "/llm-check/batch":
        already = not start_batch()
        return ("html", render_progress(already_running=already))

    # 배치 진행 페이지
    if method == "GET" and path == "/llm-check/batch":
        if _batch_state["running"] or _batch_state["done"] > 0:
            if not _batch_state["running"] and RESULTS_FILE.exists():
                return ("html", render_batch_results())
            return ("html", render_progress())
        return ("redirect", "/llm-check")

    # 배치 결과
    if method == "GET" and path == "/llm-check/results":
        if RESULTS_FILE.exists():
            return ("html", render_batch_results())
        return ("redirect", "/llm-check")

    # LLM 채팅 (스트리밍)
    if method == "POST" and path == "/llm-check/chat/stream":
        messages = body.get("messages", []) if isinstance(body, dict) else []
        analysis = body.get("analysis", {}) if isinstance(body, dict) else {}
        system_prompt = build_analysis_context(analysis)
        return ("sse", call_claude_stream(messages, system_prompt))

    # LLM 채팅 (폴백 — 논스트리밍)
    if method == "POST" and path == "/llm-check/chat":
        messages = body.get("messages", []) if isinstance(body, dict) else []
        analysis = body.get("analysis", {}) if isinstance(body, dict) else {}
        system_prompt = build_analysis_context(analysis)
        reply = call_claude(messages, system_prompt)
        return ("json", {"reply": reply})

    # 단건 분석
    if method == "GET" and path == "/llm-check":
        url = _get(body, "url").strip()
        if url:
            result = analyze_url(url)
            if "error" in result:
                return ("html", render_form(error=f"페이지 로드 실패: {result['error']}"))
            return ("html", render_result(result))
        return ("html", render_form())
    if method == "POST" and path == "/llm-check":
        url = _get(body, "url").strip()
        if not url:
            return ("html", render_form(error="URL을 입력해주세요"))
        result = analyze_url(url)
        if "error" in result:
            return ("html", render_form(error=f"페이지 로드 실패: {result['error']}"))
        return ("html", render_result(result))
    return ("html", render_form())


def render_progress(already_running=False):
    msg = "이미 분석이 진행 중입니다." if already_running else "사이트맵에서 URL을 수집하고 분석을 시작합니다..."
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 배치 분석 진행 중</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.progress-wrap{{background:white;border-radius:16px;padding:40px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.08);margin-top:40px}}
.spinner{{width:48px;height:48px;border:4px solid #e2e8f0;border-top-color:#6d28d9;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 20px}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.prog-bar{{background:#f1f5f9;border-radius:8px;height:12px;overflow:hidden;margin:16px 0}}
.prog-fill{{background:linear-gradient(90deg,#6d28d9,#4f46e5);height:100%;transition:width 0.5s;border-radius:8px}}
.prog-text{{color:#64748b;font-size:0.9rem}}
.done-count{{font-size:2rem;font-weight:700;color:#6d28d9}}
</style></head><body>
<nav>
  <a href="/" style="color:white;font-weight:600;text-decoration:none">🧭 Wayfinder</a>
  <a href="/llm-check">← 돌아가기</a>
</nav>
<div class="container">
  <div class="progress-wrap">
    <div class="spinner"></div>
    <h2 style="color:#1e293b;margin-bottom:8px">삼성닷컴 100개 URL 분석 중</h2>
    <p class="prog-text" id="msg">{msg}</p>
    <div class="done-count"><span id="done">0</span> / <span id="total">-</span></div>
    <div class="prog-bar"><div class="prog-fill" id="fill" style="width:0%"></div></div>
    <p class="prog-text" id="pct-text">0% 완료</p>
  </div>
</div>
<script>
function poll() {{
  fetch('/llm-check/status').then(r=>r.json()).then(d=>{{
    document.getElementById('done').textContent = d.done;
    document.getElementById('total').textContent = d.total || '-';
    document.getElementById('fill').style.width = d.pct + '%';
    document.getElementById('pct-text').textContent = d.pct + '% 완료';
    if (!d.running && d.done > 0) {{
      document.getElementById('msg').textContent = '분석 완료! 결과 페이지로 이동합니다...';
      setTimeout(() => location.href='/llm-check/results', 1000);
    }} else {{
      setTimeout(poll, 2000);
    }}
  }}).catch(()=>setTimeout(poll, 3000));
}}
setTimeout(poll, 1500);
</script>
</body></html>'''


def render_batch_results():
    data = json.loads(RESULTS_FILE.read_text())
    results = data.get("results", [])
    timestamp = data.get("timestamp", "")

    grade_colors = {"A": "#10b981", "B": "#0ea5e9", "C": "#f59e0b", "D": "#ef4444", "-": "#94a3b8"}
    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for r in results:
        g = r.get("grade", "-")
        if g in grade_counts:
            grade_counts[g] += 1

    rows = ""
    for i, r in enumerate(results):
        url = r.get("url", "")
        short = url.replace("https://www.samsung.com/us/", "/").rstrip("/") or "/"
        total = r.get("total", 0)
        max_pts = r.get("max", 100) or 100
        pct = int(total / max_pts * 100)
        grade = "A" if pct >= 80 else "B" if pct >= 60 else "C" if pct >= 40 else "D"
        g_color = grade_colors.get(grade, "#94a3b8")
        bar_color = "#10b981" if pct >= 70 else "#f59e0b" if pct >= 40 else "#ef4444"
        cats = r.get("categories", [])
        cat_scores = " ".join(
            f'<span title="{c["label"]}" style="font-size:0.75rem;color:#94a3b8">{c["score"]}</span>'
            for c in cats
        ) if cats else ""
        error = r.get("error", "")
        rows += f'''<tr onclick="location.href='/llm-check?url={url}'" style="cursor:pointer">
          <td style="color:#64748b;font-size:0.8rem">{i+1}</td>
          <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:0.82rem;color:#1e293b" title="{url}">{short}</td>
          <td><span style="font-weight:700;color:{g_color}">{grade}</span></td>
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div style="background:#f1f5f9;border-radius:4px;height:6px;width:80px;overflow:hidden">
                <div style="background:{bar_color};height:100%;width:{pct}%"></div>
              </div>
              <span style="font-size:0.82rem;color:#64748b">{total}/100</span>
            </div>
          </td>
          <td style="color:#94a3b8;font-size:0.75rem">{"⚠ " + error[:40] if error else cat_scores}</td>
        </tr>'''

    summary_bars = "".join(
        f'<div style="text-align:center"><div style="font-size:1.5rem;font-weight:700;color:{grade_colors[g]}">{grade_counts[g]}</div><div style="font-size:0.8rem;color:#94a3b8">등급 {g}</div></div>'
        for g in ["A","B","C","D"]
    )

    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 배치 분석 결과</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.summary-card{{background:white;border-radius:16px;padding:24px;box-shadow:0 4px 24px rgba(0,0,0,0.08);margin-bottom:24px}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06)}}
thead th{{background:#f8fafc;padding:12px 16px;text-align:left;font-size:0.78rem;color:#64748b;font-weight:600;border-bottom:1px solid #f1f5f9}}
tbody tr{{border-bottom:1px solid #f8fafc;transition:background 0.15s}}
tbody tr:hover{{background:#f8faff}}
tbody td{{padding:10px 16px;vertical-align:middle}}
.filter-btn{{padding:6px 14px;border:1px solid #e2e8f0;border-radius:20px;background:white;font-size:0.82rem;cursor:pointer;color:#64748b}}
.filter-btn.active{{background:#6d28d9;color:white;border-color:#6d28d9}}
input[type=text]{{padding:8px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:0.85rem;outline:none;width:220px}}
</style></head><body>
<nav>
  <a href="/" style="color:white;font-weight:600;text-decoration:none">🧭 Wayfinder</a>
  <div style="display:flex;gap:12px;align-items:center">
    <form method="POST" action="/llm-check/batch" style="display:inline">
      <button type="submit" style="padding:6px 14px;background:#6d28d9;color:white;border:none;border-radius:8px;cursor:pointer;font-size:0.82rem">🔄 재분석</button>
    </form>
    <a href="/llm-check">단건 분석</a>
  </div>
</nav>
<div style="padding:32px 40px 40px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
    <div>
      <h2 style="color:#1e293b;margin-bottom:4px">samsung.com/us 배치 분석 결과</h2>
      <p style="color:#94a3b8;font-size:0.85rem">{timestamp} · {len(results)}개 URL</p>
    </div>
  </div>
  <div class="summary-card">
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">{summary_bars}</div>
  </div>
  {render_category_panel()}
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap">
    <button class="filter-btn active" onclick="filterGrade('all',this)">전체</button>
    <button class="filter-btn" onclick="filterGrade('A',this)">A등급</button>
    <button class="filter-btn" onclick="filterGrade('B',this)">B등급</button>
    <button class="filter-btn" onclick="filterGrade('C',this)">C등급</button>
    <button class="filter-btn" onclick="filterGrade('D',this)">D등급</button>
    <input type="text" id="search" placeholder="URL 검색..." oninput="filterSearch(this.value)" style="margin-left:auto">
  </div>
  <table id="result-table">
    <thead><tr>
      <th>#</th><th>URL</th><th>등급</th><th>점수</th><th>카테고리별 점수</th>
    </tr></thead>
    <tbody id="tbody">{rows}</tbody>
  </table>
</div>
<script>
const allRows = Array.from(document.querySelectorAll('#tbody tr'));
let currentGrade = 'all';

function filterGrade(g, btn) {{
  currentGrade = g;
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  applyFilter();
}}
function filterSearch(q) {{ applyFilter(q); }}
function applyFilter(q='') {{
  const search = (q || document.getElementById('search').value).toLowerCase();
  allRows.forEach(r => {{
    const grade = r.cells[2].textContent.trim();
    const url = r.cells[1].textContent.toLowerCase();
    const gOk = currentGrade === 'all' || grade === currentGrade;
    const sOk = !search || url.includes(search);
    r.style.display = gOk && sOk ? '' : 'none';
  }});
}}
</script>
</body></html>'''


def render_form(error=""):
    err_html = f'<div class="error">{error}</div>' if error else ""
    gnb_groups = get_cached_gnb_products()
    # Build grouped preset HTML
    if gnb_groups:
        preset_html = ""
        for cat, products in gnb_groups.items():
            if cat == "기타":
                continue
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
                f'{cat}</span>{btns}</div>'
            )
    else:
        # Fallback while GNB is loading
        preset_html = '<div style="color:#94a3b8;font-size:0.82rem">로딩 중...</div>'
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AEO 분석 · samsung.com/us</title>
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
.how-strip{{background:white;border-radius:20px;padding:32px;box-shadow:0 4px 32px rgba(0,0,0,0.07);margin:-36px auto 0;position:relative;z-index:10;max-width:760px;margin-left:auto;margin-right:auto}}
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
.analyze-btn{{width:100%;padding:14px;background:#6d28d9;color:white;border:none;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer;margin-top:10px;transition:background 0.2s;letter-spacing:0.01em}}
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
  <a href="/">← 홈</a>
</nav>

<div class="hero">
  <div class="section">
    <div class="hero-eyebrow">AI Engine Optimization Audit</div>
    <h1 class="hero-title">samsung.com/us<br><em>AEO 페이지 진단 도구</em></h1>
    <p class="hero-sub">AI 검색 엔진이 해당 페이지를 얼마나 정확하게 이해하고 인용하는지 측정합니다. 구조화 데이터, 콘텐츠 구조, 스펙 가독성 등 9개 항목을 기준으로 개선 우선순위를 제시합니다.</p>
  </div>
</div>

<div style="max-width:760px;margin:0 auto;padding:0 16px">
  <div class="how-strip">
    <div class="steps">
      <div class="step">
        <div class="step-num">1</div>
        <div class="step-title">URL 입력</div>
        <div class="step-desc">분석할 samsung.com/us 페이지 주소를 입력합니다</div>
      </div>
      <div class="step">
        <div class="step-num">2</div>
        <div class="step-title">자동 분석</div>
        <div class="step-desc">구조화 데이터·메타·콘텐츠 등 9개 항목을 자동으로 점검합니다</div>
      </div>
      <div class="step">
        <div class="step-num">3</div>
        <div class="step-title">등급 + 액션</div>
        <div class="step-desc">A~D 종합 등급과 카테고리별 즉시 실행 가능한 개선 방향을 제시합니다</div>
      </div>
    </div>
  </div>
</div>

<div class="feat-grid">
  <div class="feat-card">
    <div class="feat-icon">📊</div>
    <div class="feat-title">9개 카테고리 진단</div>
    <div class="feat-desc">구조화 데이터, 메타 정보, 콘텐츠 구조, 스펙 명확성, FAQ, 가격·구매 가용성 등 AI 검색 관련 핵심 요소를 항목별로 점검합니다.</div>
  </div>
  <div class="feat-card">
    <div class="feat-icon">🎯</div>
    <div class="feat-title">페이지 유형별 맞춤 평가</div>
    <div class="feat-desc">홈·제품 라인업·PDP·카테고리·서포트 등 페이지 유형을 자동 감지하고, 해당 유형에 맞는 항목만 선별해 평가합니다.</div>
    <div class="grade-row">
      <div class="g-badge" style="background:#f0fdf4;color:#10b981">A</div>
      <div class="g-badge" style="background:#eff6ff;color:#0ea5e9">B</div>
      <div class="g-badge" style="background:#fffbeb;color:#f59e0b">C</div>
      <div class="g-badge" style="background:#fef2f2;color:#ef4444">D</div>
    </div>
  </div>
  <div class="feat-card">
    <div class="feat-icon">💡</div>
    <div class="feat-title">구체적 개선 제안</div>
    <div class="feat-desc">단순 점수 평가에 그치지 않고, 각 항목에서 AI 검색 노출에 실제로 영향을 주는 문제점과 즉시 적용 가능한 개선 액션을 제공합니다.</div>
  </div>
</div>

<div style="max-width:760px;margin:-8px auto 24px;padding:0 16px">
  <div style="background:#fafafa;border:1px solid #e2e8f0;border-left:4px solid #94a3b8;border-radius:10px;padding:16px 20px">
    <div style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">이 툴에 대한 솔직한 안내</div>
    <div style="font-size:0.82rem;color:#475569;line-height:1.7">
      <p style="margin-bottom:6px">✅ <strong>신뢰할 수 있는 부분:</strong> 구조화 데이터(JSON-LD), FAQ 스키마, 메타 정보 등은 Google이 공식 문서에서 AI Overview 노출에 영향을 준다고 명시한 항목입니다. Perplexity처럼 실시간 크롤링 기반 AI도 페이지 구조를 직접 읽습니다.</p>
      <p style="margin-bottom:6px">⚠️ <strong>한계:</strong> 각 항목의 점수 가중치(예: 구조화 데이터 20점)는 공개된 가이드라인을 바탕으로 설정한 것으로, 실제 AI 인용률과의 상관관계가 데이터로 검증된 수치는 아닙니다. A등급 페이지가 반드시 ChatGPT에 잘 인용된다는 보장은 없습니다.</p>
      <p style="margin:0">📌 <strong>올바른 활용법:</strong> "이 페이지가 AI 친화적으로 구조화되어 있는가"를 진단하는 참고 도구로 쓰세요. 절대적인 지표보다는 개선 우선순위를 잡는 데 활용하는 것을 권장합니다.</p>
    </div>
  </div>
</div>

<div class="form-wrap">
  <div class="form-card">
    {err_html}
    <label class="form-label" for="url">분석할 URL</label>
    <form method="POST" action="/llm-check" id="analyze-form" onsubmit="return submitForm()">
      <div style="position:relative">
        <input id="url" class="url-input" type="text" name="url"
          placeholder="https://www.samsung.com/us/... 또는 경로명 검색"
          autocomplete="off"
          oninput="onUrlInput(this.value)"
          onkeydown="onUrlKeydown(event)"
          onfocus="onUrlInput(this.value)"
          onblur="setTimeout(hideSuggest,200)">
        <div id="suggest-box"></div>
      </div>
      <button class="analyze-btn" type="submit">분석 시작 →</button>
    </form>

    <div style="margin-top:20px;padding-top:20px;border-top:1px solid #f1f5f9">
      <p style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">
        빠른 선택 <span style="font-weight:400;letter-spacing:0">— samsung.com/us GNB 최신 제품</span>
      </p>
      {preset_html}
    </div>

    <div id="recent-section" style="display:none;margin-top:20px;padding-top:20px;border-top:1px solid #f1f5f9">
      <p style="font-size:0.78rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">🕐 최근 분석</p>
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
    return '<a class="recent-url-item" href="/llm-check?url=' + encodeURIComponent(item.url) + '">'
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
  fetch('/llm-check/suggest?q=' + encodeURIComponent(q))
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

  box.innerHTML = urls.map((u, i) => {{
    const path = u.replace('https://www.samsung.com/us','') || '/';
    return `<div class="suggest-item" data-url="${{escHtml(u)}}" onmousedown="pickSuggest('${{escHtml(u)}}')">${{highlight(path)}}</div>`;
  }}).join('') + (total > urls.length ? `<div class="suggest-status">사이트맵 ${{total}}개 중 상위 ${{urls.length}}개 표시</div>` : `<div class="suggest-status">사이트맵 ${{total}}개 URL 로드됨</div>`);
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

function submitForm() {{
  hideSuggest();
  return true;
}}

function escHtml(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
</script>
</body></html>'''


CATEGORY_GUIDE = [
    {
        "label": "구조화 데이터",
        "max": 20,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 1.1.9 2 2 2h12a2 2 0 002-2V7M4 7l8-4 8 4M4 7h16"/>',
        "definition": "AI가 JSON-LD·Schema.org를 파싱해 제품 정보를 추출합니다.",
        "reason": "구조화 데이터가 없으면 AI가 스펙을 추측으로 해석해 오답을 생성합니다. 신제품 출시 후 스펙 혼동이 집중 발생하며, ChatGPT·Perplexity가 삼성닷컴 대신 GSMArena 등 서드파티를 우선 인용하게 됩니다.",
        "action": "Product + Offer + AggregateRating 스키마를 제품 페이지 템플릿에 표준 블록으로 삽입",
        "references": [
            ("Google: AI Overviews와 웹 콘텐츠 — 구조화 데이터 활용 가이드", "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data"),
            ("Google: AI Overviews 작동 방식 공식 설명", "https://support.google.com/websearch/answer/14901683"),
            ("Schema.org Product / Offer / AggregateRating 공식 사양", "https://schema.org/Product"),
        ],
        "criteria": [
            (0, 5,  "구조화 데이터 전무 — AI가 스펙을 추측으로 해석, 오답 생성 위험"),
            (6, 12, "기본 스키마 존재하나 Product 스키마 불완전 — 일부 스펙 오류 발생"),
            (13, 20,"Product+Offer+Rating 완비 — AI 검색 1차 인용 소스 자격 확보"),
        ],
    },
    {
        "label": "메타 정보",
        "max": 10,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>',
        "definition": "Title·Description·OG 태그는 AI가 페이지 정체성을 판단하는 첫 번째 신호입니다.",
        "reason": "제네릭한 제목만 있으면 AI가 카테고리 페이지를 제품 페이지로 오분류합니다. Google AI Overview 소스 패널 제외, Perplexity에서 삼성닷컴 링크가 리뷰 사이트에 밀리는 직접 원인입니다.",
        "action": "[모델명] | [핵심 기능] | Samsung US 패턴으로 메타 타이틀 작성 규칙 표준화",
        "references": [
            ("Google: AI Overviews 소스 선정 — 페이지 관련성·신뢰도 기준", "https://support.google.com/websearch/answer/14901683"),
            ("Google Search Central: 타이틀·메타 설명 가이드라인", "https://developers.google.com/search/docs/appearance/title-link"),
            ("Google: E-E-A-T와 AI 소스 신뢰도 평가 기준", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"),
        ],
        "criteria": [
            (0, 3,  "Title/Description 부실 — AI가 페이지 분류 오류 빈번, Overview 소스 패널 탈락"),
            (4, 7,  "기본 메타 있으나 OG 태그 미완성 — 소셜/AI 공유 최적화 미흡"),
            (8, 10, "모든 메타 완비 — AI Overview 소스 패널 진입 가능, 페이지 정체성 명확"),
        ],
    },
    {
        "label": "콘텐츠 구조",
        "max": 15,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h10"/>',
        "definition": "H1~H3 헤딩 계층이 AI의 문서 목차 역할을 합니다.",
        "reason": "삼성닷컴은 비주얼 중심 디자인으로 제품명이 div에 묻혀있는 경우가 많습니다. AI가 슬로건을 주제로 인식해 스펙 추출에 실패하고, 마케팅 카피와 실제 스펙을 동등하게 취급합니다.",
        "action": "제품명 → H1, 주요 기능 섹션 → H2, 세부 사양 → H3으로 DOM 계층 재정렬 (디자인 변경 없이 가능)",
        "references": [
            ("Google: 크롤링 가능한 콘텐츠 구조 — AI Overview 소스 선정의 전제", "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics"),
            ("Google Search Central: 헤딩 계층 구조와 콘텐츠 이해", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"),
            ("Google: 도움이 되는 콘텐츠 시스템 — AI Overview 소스 품질 기준", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"),
        ],
        "criteria": [
            (0, 5,  "헤딩 구조 부재 — 마케팅 카피와 스펙 구분 불가, AI 섹션 추출 실패"),
            (6, 10, "기본 구조 있으나 H2/H3 활용 부족 — 일부 섹션 인식 오류"),
            (11, 15,"명확한 계층 구조 완비 — AI가 섹션별 정보 정확히 추출 가능"),
        ],
    },
    {
        "label": "스펙 명확성",
        "max": 15,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 6h18M3 14h18M3 18h18"/>',
        "definition": "스펙 데이터가 &lt;table&gt;·리스트 형태로 제공될 때 AI가 정확하게 추출합니다.",
        "reason": "JS로 렌더링되는 스펙 컴포넌트는 AI 크롤러가 읽지 못합니다. 비교 쿼리에서 삼성 컬럼이 빈칸으로 표시되고, AI 쇼핑 결과에서 아마존·베스트바이에 직판 채널이 밀립니다.",
        "action": "크롤러용 정적 HTML &lt;table&gt;을 JS 컴포넌트와 병행 제공 (디자인 변경 없이 즉시 적용 가능)",
        "references": [
            ("Google: JavaScript 렌더링과 AI 크롤러 접근성", "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics"),
            ("Google: 제품 구조화 데이터 — 스펙 정보 마크업 가이드", "https://developers.google.com/search/docs/appearance/structured-data/product"),
            ("Google: AI Overviews 소스 품질 — 팩트 정확성 기준", "https://support.google.com/websearch/answer/14901683"),
        ],
        "criteria": [
            (0, 5,  "스펙 테이블 없음 — 서드파티 스펙 사이트에 권위 이전, AI 비교 쿼리에서 삼성 누락"),
            (6, 10, "일부 스펙 구조화, 단위 표기 불규칙 — 부분적 AI 인식 가능"),
            (11, 15,"구조화된 스펙 완비 — AI 비교 쿼리에서 삼성 데이터 직접 인용"),
        ],
    },
    {
        "label": "FAQ 구조",
        "max": 10,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>',
        "definition": "FAQPage 스키마는 AI에게 '이 질문에는 이 답이 정답'이라고 직접 선언하는 수단입니다.",
        "reason": "FAQ가 없으면 AI가 Reddit·Quora의 구버전 정보를 인용합니다. 보증 기간, 방수 등급, 호환성 오답이 고객 서비스 비용 증가로 직결되며, 경쟁사 FAQ가 삼성 브랜드 검색에 노출될 수 있습니다.",
        "action": "CS 티켓 Top 20 질문을 추출해 제품 카테고리 페이지 하단에 FAQPage 스키마 Q&A 섹션 추가",
        "references": [
            ("Google: FAQPage 구조화 데이터 — AI Overview Q&A 직접 인용 근거", "https://developers.google.com/search/docs/appearance/structured-data/faqpage"),
            ("Google: AI Overviews가 Q&A 콘텐츠를 활용하는 방식", "https://support.google.com/websearch/answer/14901683"),
            ("Schema.org FAQPage 공식 사양", "https://schema.org/FAQPage"),
        ],
        "criteria": [
            (0, 2,  "FAQ 없음 — AI가 Reddit·포럼의 구버전·비공식 정보를 공식 답변으로 인용"),
            (3, 7,  "FAQ 콘텐츠 있으나 스키마 미적용 — AI가 Q&A 구조를 인식하지 못함"),
            (8, 10, "FAQPage 스키마 완비 — AI가 공식 Q&A를 직접 답변에 활용, CS 비용 절감"),
        ],
    },
    {
        "label": "텍스트 명확성",
        "max": 5,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
        "definition": "짧고 팩트 중심의 문장에서 AI의 정보 추출 정확도가 높아집니다.",
        "reason": "'Experience the ultimate innovation…' 같은 마케팅 언어에서 AI는 추출할 팩트가 없다고 판단하고 CNET·Engadget 리뷰를 1차 소스로 선택합니다. 공식 채널이 비공식 채널에 권위를 빼앗기는 구조입니다.",
        "action": "각 제품 페이지에 'Key Specs' 섹션을 별도 추가해 단문 bullet point 5~7개로 팩트만 제공",
        "references": [
            ("Google: 도움이 되는 콘텐츠 시스템 — AI Overview 소스 선정의 핵심 기준", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"),
            ("Google: E-E-A-T (경험·전문성·권위·신뢰성) 평가 가이드", "https://developers.google.com/search/docs/fundamentals/creating-helpful-content#e-e-a-t"),
            ("Google Search Central: 사용자에게 유용한 콘텐츠 작성 모범 사례", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"),
        ],
        "criteria": [
            (0, 1, "마케팅 언어 과다 — AI 팩트 추출 실패, 리뷰 사이트를 1차 소스로 선택"),
            (2, 3, "부분적 팩트 섹션 존재 — AI가 일부 정보 추출 가능"),
            (4, 5, "팩트 중심 단문 구조 — AI 정보 추출 최적화, 공식 채널 권위 확보"),
        ],
    },
    {
        "label": "제품 간 연결성",
        "max": 10,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>',
        "definition": "내부 링크와 생태계 키워드로 AI가 삼성 제품 간 연동 관계를 인식합니다.",
        "reason": "삼성은 SmartThings·Galaxy 생태계 연동이 핵심 USP임에도, 페이지 간 연결 구조가 부실하면 AI가 이 강점을 인식하지 못합니다. '갤럭시폰과 연동되는 기기 추천해줘' 같은 쿼리에서 경쟁사에 밀리는 직접 원인입니다.",
        "action": "제품 페이지마다 '호환 기기' 섹션 + 내부 링크 추가, SmartThings 연동 정보 텍스트로 명시",
        "references": [
            ("Google: 크롤링 가능한 링크 구조 — AI 크롤러의 사이트 탐색 방식", "https://developers.google.com/search/docs/crawling-indexing/links-crawlable"),
            ("Google: Knowledge Graph 엔티티 인식 — 제품 관계 파악 원리", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"),
            ("Google: AI Overviews 소스 다양성 및 관련 페이지 연결", "https://support.google.com/websearch/answer/14901683"),
        ],
        "criteria": [
            (0, 3, "연결 구조 없음 — 삼성 생태계 강점이 AI에 완전히 비가시, 생태계 쿼리 기회 손실"),
            (4, 7, "일부 내부 링크 존재 — 생태계 일부 인식 가능, 체계적 연결 보강 필요"),
            (8, 10,"생태계 연결 완비 — SmartThings·Galaxy 연동 AI 완전 인식, 생태계 쿼리 선점"),
        ],
    },
    {
        "label": "가격·구매 가용성",
        "max": 10,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/>',
        "definition": "Offer 스키마와 가격·재고 정보가 AI 쇼핑 결과 노출을 결정합니다.",
        "reason": "ChatGPT Shopping, Google AI Overview 쇼핑 탭이 급성장 중입니다. Offer 스키마 없이는 AI 쇼핑 결과에서 삼성닷컴 직판 채널이 아마존·베스트바이에 밀려 직판 마진이 손실됩니다.",
        "action": "Offer 스키마에 price·availability·url 필드 완비, 실시간 재고 연동 검토",
        "references": [
            ("Google: 제품 구조화 데이터 (Offer·가격·재고) — AI 쇼핑 결과 노출 요건", "https://developers.google.com/search/docs/appearance/structured-data/product"),
            ("Google: AI Overviews 쇼핑 기능 — Offer 스키마 필수 조건", "https://support.google.com/websearch/answer/14901683"),
            ("Google Merchant Center: 상품 데이터 품질 가이드", "https://support.google.com/merchants/answer/7052112"),
        ],
        "criteria": [
            (0, 3, "Offer 스키마 없음 — AI 쇼핑에서 아마존·베스트바이에 직판 채널 완전 밀림"),
            (4, 7, "기본 가격 정보 있으나 재고·프로모션 정보 누락 — 부분적 AI 쇼핑 노출"),
            (8, 10,"완전한 커머스 신호 — AI 쇼핑 탭 직접 노출, 직판 채널 경쟁력 확보"),
        ],
    },
    {
        "label": "리뷰 스키마",
        "max": 5,
        "icon": '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>',
        "definition": "AggregateRating 스키마로 삼성 공식 평점이 AI 구매 추천에 반영됩니다.",
        "reason": "AI가 구매 고려 쿼리에 답할 때 리뷰 데이터를 강하게 참조합니다. 스키마 없이는 삼성닷컴 자체 평점 대신 아마존·Best Buy 리뷰를 우선 인용하며, 삼성 공식 채널 신뢰도가 저하됩니다.",
        "action": "AggregateRating 스키마에 ratingValue·reviewCount·bestRating 필드 완비",
        "references": [
            ("Google: 리뷰 스니펫 구조화 데이터 — AI 구매 추천 쿼리 반영 근거", "https://developers.google.com/search/docs/appearance/structured-data/review-snippet"),
            ("Google: AI Overviews에서 평점 데이터 활용 방식", "https://support.google.com/websearch/answer/14901683"),
            ("Schema.org AggregateRating 공식 사양", "https://schema.org/AggregateRating"),
        ],
        "criteria": [
            (0, 1, "리뷰 스키마 없음 — 구매 고려 쿼리에서 아마존 리뷰가 공식 평점보다 우선 노출"),
            (2, 3, "AggregateRating 있으나 reviewCount 누락 — AI가 평점 신뢰도를 낮게 판단"),
            (4, 5, "완전한 리뷰 스키마 — AI 구매 추천에서 삼성닷컴 공식 평점 직접 인용"),
        ],
    },
]

GRADE_GUIDE = {
    "A": ("AI 검색 우선 소스", "ChatGPT·Perplexity·Google AI Overview에서 삼성닷컴이 1차 인용 소스로 안정적으로 등장. 신제품 출시 후 정보 오류 발생 최소화."),
    "B": ("부분적 AI 가시성", "플래그십 제품은 AI에 잘 노출되나 비주력 카테고리는 서드파티에 밀림. 카테고리별 우선순위 집중 개선 필요."),
    "C": ("AI 검색 기회 손실", "삼성닷컴이 AI 응답 소스로 거의 활용되지 않는 상태. 잘못된 정보 유통 위험 높음. 즉각적인 개선 투자 필요."),
    "D": ("AI 검색 부재 상태", "AI 검색 생태계에서 사실상 존재하지 않는 것으로 간주. 단순 SEO 문제를 넘어 브랜드 신뢰도 리스크. 플랫폼 아키텍처 레벨 개입 필요."),
}


def render_category_panel(current_page_type="other"):
    # 카테고리 약어 (헤더용)
    label_abbr = {
        "구조화 데이터": "구조화", "메타 정보": "메타", "콘텐츠 구조": "콘텐츠",
        "스펙 명확성": "스펙", "FAQ 구조": "FAQ", "텍스트 명확성": "텍스트",
        "제품 간 연결성": "연결성", "가격·구매 가용성": "가격/구매", "리뷰 스키마": "리뷰",
    }
    all_labels = [c["label"] for c in CATEGORY_GUIDE]
    col_headers = "".join(
        f'<th style="padding:8px 6px;font-size:0.72rem;color:#475569;font-weight:600;'
        f'text-align:center;white-space:nowrap;border-bottom:2px solid #e2e8f0" title="{lb}">'
        f'{label_abbr.get(lb, lb[:5])}</th>'
        for lb in all_labels
    )
    example_urls = {
        "home": "/us/",
        "product_line": "/us/smartphones/galaxy-s25/",
        "product": "/us/smartphones/.../buy/galaxy-s25-ultra-256gb",
        "buy_flow": "/us/smartphones/galaxy-s25/buy/",
        "category": "/us/monitors/gaming/",
        "app": "/us/apps/samsung-health/",
        "support": "/us/support/",
        "other": "(기타 페이지)",
    }
    type_rows = ""
    for i, (pt_key, pt_name) in enumerate(PAGE_TYPES.items()):
        skip_set = PAGE_TYPE_SKIP.get(pt_key, set())
        is_current = (pt_key == current_page_type)
        bg = "#faf5ff" if is_current else ("#ffffff" if i % 2 == 0 else "#fafafa")
        left_border = "border-left:3px solid #6d28d9;" if is_current else "border-left:3px solid transparent;"
        name_color = "#6d28d9" if is_current else "#1e293b"
        current_badge = ' <span style="font-size:0.65rem;background:#6d28d9;color:white;padding:1px 6px;border-radius:8px;margin-left:4px;font-weight:700">현재</span>' if is_current else ""
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
            f'white-space:nowrap;background:{bg};{left_border}border-right:1px solid #f1f5f9">{pt_name}{current_badge}</td>'
            f'<td style="padding:8px 14px;font-size:0.72rem;color:#94a3b8;font-family:monospace;'
            f'white-space:nowrap;background:{bg};border-right:1px solid #e2e8f0">{ex}</td>'
            f'{cells}</tr>'
        )
    page_type_table = (
        '<div style="border-top:1px solid #e2e8f0;padding-top:20px;margin-top:8px">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
        '<span style="font-weight:700;color:#1e293b;font-size:0.88rem">🗂 페이지 유형별 평가 항목</span>'
        '<span style="font-size:0.72rem;color:#94a3b8">'
        '<span style="color:#10b981;font-weight:700">✓</span> 평가 대상 &nbsp;·&nbsp; '
        '<span style="color:#d1d5db;font-weight:700">—</span> 해당 유형에 없어 점수 제외</span></div>'
        '<div style="overflow-x:auto;border-radius:10px;border:1px solid #e2e8f0;overflow:hidden">'
        '<table style="border-collapse:collapse;width:100%"><thead>'
        f'<tr style="background:#f8fafc">'
        f'<th style="padding:8px 14px;text-align:left;font-size:0.72rem;color:#64748b;font-weight:600;white-space:nowrap;border-bottom:2px solid #e2e8f0;border-right:1px solid #f1f5f9">페이지 유형</th>'
        f'<th style="padding:8px 14px;text-align:left;font-size:0.72rem;color:#64748b;font-weight:600;border-bottom:2px solid #e2e8f0;border-right:1px solid #e2e8f0">URL 예시</th>'
        f'{col_headers}</tr></thead><tbody>{type_rows}</tbody></table></div></div>'
    )

    cards = ""
    for cat in CATEGORY_GUIDE:
        cards += f'''
        <div style="background:white;border:1px solid #e2e8f0;border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:8px">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <div style="width:36px;height:36px;background:#ede9fe;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <svg style="width:18px;height:18px;color:#6d28d9" fill="none" stroke="#6d28d9" viewBox="0 0 24 24">{cat["icon"]}</svg>
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
      <span style="font-weight:700;color:#1e293b;font-size:0.95rem">📋 카테고리 평가 기준</span>
      <span style="margin-left:10px;font-size:0.78rem;color:#94a3b8">samsung.com/us 운영자 관점 — 각 카테고리가 AI 검색에 미치는 영향</span>
    </div>
    <svg id="guide-chevron" style="width:18px;height:18px;color:#6d28d9;transition:transform 0.3s;flex-shrink:0" fill="none" stroke="#6d28d9" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
    </svg>
  </div>
  <div id="guide-body" style="max-height:0;overflow:hidden;transition:max-height 0.4s ease;background:#f8fafc">
    <div style="padding:20px">
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">
        {cards}
      </div>
      <div style="border-top:1px solid #e2e8f0;padding-top:16px">
        <div style="font-weight:700;color:#1e293b;font-size:0.85rem;margin-bottom:10px">종합 등급 기준</div>
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


def render_result(r):
    pct = int(r["total"] / r["max"] * 100) if r.get("max") else 0
    grade_colors = {"A": "#10b981", "B": "#0ea5e9", "C": "#f59e0b", "D": "#ef4444"}
    g_color = grade_colors.get(r["grade"], "#64748b")
    guide_map = {g["label"]: g for g in CATEGORY_GUIDE}

    # Summary data
    non_skipped = [c for c in r["categories"] if not c.get("skipped") and c.get("max", 0) > 0]
    strengths = [c for c in non_skipped if int(c["score"] / c["max"] * 100) >= 70]
    weaknesses = sorted([c for c in non_skipped if int(c["score"] / c["max"] * 100) < 70], key=lambda c: c["score"] / c["max"])[:3]
    next_grades = {"D": ("C", 40), "C": ("B", 60), "B": ("A", 80), "A": (None, 100)}
    next_g, next_pct_thresh = next_grades[r["grade"]]
    if next_g:
        min_for_next = (next_pct_thresh * r["max"] + 99) // 100
        needed_score = max(0, min_for_next - r["total"])
        gap_text = f"{next_g} 등급까지 +{needed_score}점 필요"
    else:
        gap_text = "최고 등급 달성 ✓"
    strength_items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;padding:3px 0">'
        f'<span style="width:6px;height:6px;background:#10b981;border-radius:50%;flex-shrink:0"></span>'
        f'<span style="font-size:0.8rem;color:#374151">{_html.escape(c["label"])}</span>'
        f'<span style="font-size:0.75rem;color:#10b981;margin-left:auto;font-weight:600">{int(c["score"]/c["max"]*100)}%</span>'
        f'</div>'
        for c in strengths
    ) or '<span style="font-size:0.8rem;color:#94a3b8">해당 없음</span>'
    weakness_items = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;padding:3px 0">'
        f'<span style="width:6px;height:6px;background:#ef4444;border-radius:50%;flex-shrink:0"></span>'
        f'<span style="font-size:0.8rem;color:#374151">{_html.escape(c["label"])}</span>'
        f'<span style="font-size:0.75rem;color:#ef4444;margin-left:auto;font-weight:600">{int(c["score"]/c["max"]*100)}%</span>'
        f'</div>'
        for c in weaknesses
    ) or '<span style="font-size:0.8rem;color:#94a3b8">개선 필요 없음</span>'
    summary_html = f'''
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px">
      <div style="background:white;border-radius:12px;padding:16px;border:1px solid #e2e8f0">
        <div style="font-size:0.7rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">현황</div>
        <div style="font-size:2.2rem;font-weight:900;color:{g_color};line-height:1">{r["grade"]}</div>
        <div style="font-size:0.82rem;color:#374151;margin-top:4px">{pct}% &middot; {r["total"]}/{r["max"]}점</div>
        <div style="font-size:0.76rem;color:#64748b;margin-top:3px">{PAGE_TYPES.get(r.get("page_type","other"), "기타")}</div>
        <div style="margin-top:10px;padding:6px 8px;background:#f5f3ff;border-radius:6px;font-size:0.75rem;color:#6d28d9;font-weight:600">{gap_text}</div>
      </div>
      <div style="background:white;border-radius:12px;padding:16px;border:1px solid #e2e8f0">
        <div style="font-size:0.7rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">강점 (70%+)</div>
        {strength_items}
      </div>
      <div style="background:white;border-radius:12px;padding:16px;border:1px solid #e2e8f0">
        <div style="font-size:0.7rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px">즉시 개선 필요</div>
        {weakness_items}
      </div>
    </div>'''

    # Grade legend
    grade_thresholds = {"A": "80%+", "B": "60–79%", "C": "40–59%", "D": "40% 미만"}
    grade_bgs = {"A": "#f0fdf4", "B": "#eff6ff", "C": "#fffbeb", "D": "#fef2f2"}
    grade_legend_html = ""
    for g, (title, _) in GRADE_GUIDE.items():
        gc = grade_colors[g]
        is_current = (g == r["grade"])
        border = f"2px solid {gc}" if is_current else f"1px solid {gc}33"
        shadow = f"box-shadow:0 0 0 3px {gc}22;" if is_current else ""
        grade_legend_html += f'''
        <div style="background:{grade_bgs[g]};border:{border};border-radius:10px;padding:12px 8px;text-align:center;{shadow}position:relative">
          {"<div style='position:absolute;top:-8px;right:-8px;background:#1e293b;color:white;font-size:0.65rem;padding:2px 6px;border-radius:10px'>현재</div>" if is_current else ""}
          <div style="font-weight:900;font-size:1.3rem;color:{gc}">{g}</div>
          <div style="font-size:0.7rem;color:{gc};font-weight:600;margin-bottom:2px">{grade_thresholds[g]}</div>
          <div style="font-size:0.72rem;font-weight:600;color:#374151;line-height:1.3">{title}</div>
        </div>'''

    cat_rows = ""
    for idx, c in enumerate(r["categories"]):
        c_pct = int(c["score"] / c["max"] * 100)
        bar_color = "#10b981" if c_pct >= 70 else "#f59e0b" if c_pct >= 40 else "#ef4444"
        issues_html = "".join(f'<li style="color:#ef4444">⚠ {_html.escape(i)}</li>' for i in c["issues"])
        tips_html_inner = "".join(f'<li style="color:#0ea5e9">💡 {_html.escape(t)}</li>' for t in c["tips"])

        guide = guide_map.get(c["label"])
        toggle_id = f"cat-guide-{idx}"
        if c.get("skipped"):
            toggle_html = ""
        elif guide:
            n = len(guide["criteria"])
            tier_colors = ["#ef4444", "#f59e0b", "#10b981"]
            criteria_html = "".join(
                f'<div style="padding:4px 0;font-size:0.78rem;color:{tier_colors[min(i, len(tier_colors)-1)]}">'
                f'<span style="font-weight:600">{lo}~{hi}점</span> — {_html.escape(desc)}</div>'
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
              📐 평가 루브릭 보기
            </button>
            <div id="{toggle_id}" style="display:none;margin-top:8px;background:#f8f7ff;border-radius:8px;padding:12px;border-left:3px solid #6d28d9">
              <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:8px;font-style:italic">이 카테고리가 무엇인지, 왜 평가하는지에 대한 기준입니다. 이 페이지에서 발견된 구체적 문제·조치는 하단 개선 제안을 확인하세요.</div>
              <div style="font-size:0.8rem;color:#475569;margin-bottom:6px"><strong>정의:</strong> {guide["definition"]}</div>
              <div style="font-size:0.8rem;color:#475569;margin-bottom:8px"><strong>AI 검색 영향:</strong> {guide["reason"]}</div>
              <div style="border-top:1px solid #e2e8f0;padding-top:8px;margin-bottom:8px"><strong style="font-size:0.75rem;color:#64748b">점수 구간별 의미</strong>{criteria_html}</div>
              {f'<div style="border-top:1px solid #e2e8f0;padding-top:8px"><strong style="font-size:0.75rem;color:#64748b">📚 근거 자료</strong><div style="margin-top:4px">{refs_html}</div></div>' if refs_html else ""}
            </div>
          </div>'''
        else:
            toggle_html = ""

        if c.get("skipped"):
            cat_rows += f'''
        <div style="background:#f8fafc;border-radius:12px;padding:14px 20px;box-shadow:none;margin-bottom:8px;border:1px dashed #e2e8f0;display:flex;align-items:center;gap:10px">
          <span style="font-size:0.85rem;color:#94a3b8">{_html.escape(c["label"])}</span>
          <span style="font-size:0.75rem;color:#cbd5e1;background:#f1f5f9;padding:2px 8px;border-radius:10px">{_html.escape(c.get("skip_reason","해당 없음"))}</span>
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

    # 카테고리별 개선 제안 (actionable) — skipped 카테고리 제외
    tips_blocks = ""
    has_any_tip = False
    for c in r["categories"]:
        if c.get("skipped"):
            continue
        if not c.get("issues") and not c.get("tips"):
            continue
        has_any_tip = True
        c_pct = int(c["score"] / c["max"] * 100)
        bar_color = "#10b981" if c_pct >= 70 else "#f59e0b" if c_pct >= 40 else "#ef4444"
        guide = guide_map.get(c["label"])

        items_html = ""
        for issue in c.get("issues", []):
            items_html += f'<div style="display:flex;gap:8px;padding:6px 0;border-bottom:1px solid #fef2f2"><span style="color:#ef4444;flex-shrink:0">⚠</span><span style="font-size:0.85rem;color:#374151">{_html.escape(issue)}</span></div>'
        for tip in c.get("tips", []):
            items_html += f'<div style="display:flex;gap:8px;padding:6px 0;border-bottom:1px solid #f0fdf4"><span style="color:#6d28d9;flex-shrink:0">→</span><span style="font-size:0.85rem;color:#374151">{_html.escape(tip)}</span></div>'
        if guide:
            items_html += f'<div style="margin-top:8px;padding:8px 10px;background:#f5f3ff;border-radius:6px;font-size:0.82rem;color:#6d28d9"><strong>💡 권장 조치:</strong> {_html.escape(guide["action"])}</div>'

        tips_blocks += f'''
        <div style="background:white;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);margin-bottom:10px">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
            <span style="font-weight:700;font-size:0.88rem;color:#1e293b">{_html.escape(c["label"])}</span>
            <span style="font-size:0.78rem;font-weight:600;color:{bar_color}">{c["score"]}/{c["max"]}점</span>
          </div>
          {items_html}
        </div>'''

    if not has_any_tip:
        tips_blocks = "<div style='color:#94a3b8;font-size:0.88rem;padding:16px'>모든 항목 양호 — 개선 사항 없음</div>"

    # JS data for recently viewed sidebar
    recent_data = json.dumps({"url": r["url"], "grade": r["grade"], "pct": pct}, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 LLM 분석 결과</title>
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
.recent-panel{{position:sticky;top:20px;background:white;border-radius:12px;border:1px solid #e2e8f0;padding:14px;overflow:hidden}}
.recent-item{{display:block;padding:8px 0;border-bottom:1px solid #f1f5f9;text-decoration:none;color:inherit}}
.recent-item:last-child{{border-bottom:none}}
.recent-item:hover .recent-path{{color:#6d28d9}}
@media(max-width:900px){{.recent-sidebar{{display:none}}}}
</style></head><body>
<nav>
  <a href="/" style="color:white;font-weight:600;text-decoration:none">🧭 Wayfinder</a>
  <div style="display:flex;gap:16px">
    <a href="/llm-check">← 다시 분석</a>
    <a href="/llm-check/results">배치 결과</a>
  </div>
</nav>
<div class="result-layout">
  <div class="result-main">
    <div class="score-card">
      <div class="grade" style="color:{g_color}">{r["grade"]}</div>
      <div class="total-score">{r["total"]} / {r["max"]}점 ({pct}%)</div>
      <a class="url-badge" href="{_html.escape(r['url'])}" target="_blank" rel="noopener">{_html.escape(r["url"])} ↗</a>
      <div style="margin-top:10px;font-size:0.78rem;opacity:0.8">
        페이지 유형: <strong>{PAGE_TYPES.get(r.get("page_type","other"), "기타")}</strong>
        {f'<span style="margin-left:10px;background:rgba(255,255,255,0.15);padding:2px 8px;border-radius:4px">AA pageTrack: &quot;{_html.escape(r["page_track"])}&quot;</span>' if r.get("page_track") else ""}
      </div>
    </div>

    {summary_html}

    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:28px">
      {grade_legend_html}
    </div>

    {render_category_panel(r.get("page_type", "other"))}

    <div class="section-title">📊 카테고리별 분석</div>
    <p style="font-size:0.8rem;color:#94a3b8;margin:-8px 0 12px">각 항목 우측의 <strong style="color:#6d28d9">📐 평가 루브릭 보기</strong>를 누르면 해당 카테고리의 정의·영향·점수 구간 기준을 확인할 수 있습니다.</p>
    {cat_rows}

    <div class="section-title">💡 카테고리별 개선 제안</div>
    <p style="font-size:0.8rem;color:#94a3b8;margin:-8px 0 12px">이 페이지 분석에서 실제로 발견된 문제점과 조치 방향입니다. 평가 항목의 정의나 점수 기준이 궁금하면 위 카드의 📐 루브릭을 참고하세요.</p>
    <div style="margin-bottom:32px">{tips_blocks}</div>
  </div>

  <div class="recent-sidebar">
    <div class="recent-panel">
      <div style="font-size:0.75rem;font-weight:700;color:#1e293b;margin-bottom:10px">🕐 최근 분석</div>
      <div id="recent-list"><div style="color:#cbd5e1;font-size:0.75rem">기록 없음</div></div>
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
    var raw=item.url.replace(/^https?:\/\/(www\.)?samsung\.com/,'');
    var short=raw.length>26?raw.slice(0,23)+'...':raw;
    var active=item.url===cur.url;
    return '<a class="recent-item" href="/llm-check?url='+encodeURIComponent(item.url)+'">'
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

