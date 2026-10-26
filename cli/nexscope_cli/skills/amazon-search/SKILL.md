---
name: ecommerce.amazon-search
description: Simulates a real user searching on Amazon's storefront to get real-time keyword ranking and search results page data. Use when the user mentions Amazon product search, search result scraping, keyword ranking on search pages, ASIN ranking position check, competitor discovery, search page price comparison, sponsored product analysis, new product monitoring, or storefront search simulation. Even if the user does not explicitly mention "search simulation", trigger this skill whenever their need involves real-time Amazon search results, product ranking data, or storefront SERP analysis.
---

# Amazon Product Search

This skill guides you on how to perform Amazon storefront search simulations, helping Amazon sellers retrieve real-time search result data including product rankings, prices, ratings, and more.

## Core Concepts

This tool simulates a real user searching on Amazon's storefront. It returns live search result page (SERP) data: product listings with their positions, prices, ratings, review counts, brands, delivery info, sponsored flags, and more. This is **real-time** data directly from the Amazon frontend, not historical analytics.

**Key distinction from ABA data**: ABA data is aggregated historical search term analytics. This tool returns the actual product listings a user would see when searching a keyword on Amazon right now.

**Keyword language**: Keywords should be in the language of the target marketplace. For example, use English keywords for amazon.com, German keywords for amazon.de, Japanese keywords for amazon.co.jp, etc.

## Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| keyword | string | No | Search keyword (translate to the target marketplace's language) | - |
| amazonDomain | string | No | Amazon marketplace domain | amazon.com |
| node | string | No | Amazon category node ID for category-scoped searches | - |
| language | string | No | Language locale code (e.g., en_US, de_DE, ja_JP) | - |
| sort | string | No | Sort order for results | relevanceblender |
| page | integer | No | Page number (starting from 1, ~20 results per page) | 1 |
| deliveryZip | string | No | Postal/zip code for delivery location simulation | - |
| device | string | No | Device type: desktop, mobile, or tablet | desktop |

### Supported Marketplaces

| Domain | Country |
|--------|---------|
| amazon.com | United States |
| amazon.co.uk | United Kingdom |
| amazon.de | Germany |
| amazon.fr | France |
| amazon.it | Italy |
| amazon.es | Spain |
| amazon.co.jp | Japan |
| amazon.ca | Canada |
| amazon.com.au | Australia |
| amazon.com.br | Brazil |
| amazon.in | India |
| amazon.nl | Netherlands |
| amazon.se | Sweden |
| amazon.pl | Poland |
| amazon.sg | Singapore |
| amazon.sa | Saudi Arabia |
| amazon.ae | United Arab Emirates |
| amazon.com.mx | Mexico |
| amazon.com.tr | Turkey |
| amazon.com.be | Belgium |
| amazon.cn | China |
| amazon.eg | Egypt |

Default marketplace is **amazon.com**. Use amazon.com when the user doesn't specify a marketplace.

### Sort Options

| Value | Description |
|-------|-------------|
| relevanceblender | Featured / Relevance (default) |
| price-asc-rank | Price: Low to High |
| price-desc-rank | Price: High to Low |
| review-rank | Average Customer Review |
| date-desc-rank | Newest Arrivals |
| exact-aware-popularity-rank | Best Sellers |

## Local migration candidate dependency

This Skill requires Python 3.11+ and exactly `nexscope-cli==0.1.1` (compatibility API 1). Build or obtain the matching wheel from https://github.com/nexscope-ai/nexscope-cli and verify its SHA-256 before installation. Install it with `python -m pip install --no-index --no-deps /absolute/path/nexscope_cli-0.1.1-py3-none-any.whl` in the interpreter used by this script. The independent adapter uses the standard library; browser/plugin dependencies are installed separately. Do not auto-install an unverified similarly named package. Keep the current published Skill until the paired wheel and old command compatibility have passed acceptance.

The original `NEXSCOPE_API_KEY`, `NEXSCOPE_PROXY_BASE`, JSON object argument, `--inline` and `--no-cache` remain supported. No OS keyring, browser login, or `/api/cli/account` preflight is required. Search page numbers and batch detail parameters are forwarded once without the pilot workflow's one-page/three-ASIN limit. Inspect outer response code/error: JSON API failures preserve the legacy output and exit-code behavior.

Use an HTTPS API origin (HTTP loopback is supported for local tests). Redirects are refused. Missing/wrong dependencies fail before any request. Missing credentials, invalid output paths and malformed JSON also fail without calling the service. Never silently fall back to the old implementation. Cache is isolated to the selected credential context and process; existing `.cache` files are left untouched but ignored. Payloads above 2 MiB are refused; ambiguous failures are never retried.

Upgrade the wheel first, then replace the entire Skill directory. Roll back the Skill directory first, then restore the previous wheel if needed. Use the paired rollback artifacts, preserve user output/credentials, and use `--no-cache` with old scripts when switching Keys. This candidate has only local mock verification; no production or paid validation and no public release is claimed.

## Usage

- **API Endpoint**: `POST /amazon/search` (see `references/api.md` for full parameters/response/error codes)
- **Python Script**: `python scripts/amazon_search.py '<JSON params>' [--inline]`
- **Cost Constraint**: Invoking this Skill consumes credits. No automatic retry, pagination or scope expansion. The migrated adapter uses only in-memory session caching; a new script process makes a new request, even with identical parameters. The old 24h disk cache is not read or written. Keep --no-cache for an explicit cache bypass. Obtain user scope before additional paid queries.

**Output Strategy (default script behavior)**:
- **Always** write the full response to `<cwd>/nexscope/<YYYY-MM-DD>/<session>/data/ecommerce.amazon-search-amazon_search-<timestamp>.json`. The current directory must be writable; output is reserved before requesting data. No home/temp fallback. SESSION_ID, if supplied, must be a safe directory name.
- Response ≤ 8 KB: print full JSON to stdout after saving
- Response > 8 KB: stdout prints only a summary (top-level fields, counts like `total`/`costToken`, length of largest list fields + first 3 samples)
- Add `--inline` to force full stdout output (still saves to disk)

**Data Reading Tip**: Check the summary first. Use `jq` or `ConvertFrom-Json` to extract specific fields from the saved JSON file, avoiding loading the full payload into context.

## Authentication and Credits

If authentication fails or credits are depleted:
- Ensure `NEXSCOPE_API_KEY` is set as an environment variable.
- For 401/402 errors or insufficient balance messages, direct the user to https://www.nexscope.ai/help/skills-external-access?co-from=skillNS to top up credits.

## How to Build Queries

Construct the request parameters based on the user's intent:

1. **Determine the marketplace**: Map the user's target country to the correct `amazonDomain` value
2. **Set the keyword**: Translate the search term into the target marketplace's language
3. **Choose sort order**: If the user wants results sorted by price, reviews, or newness, set the `sort` parameter
4. **Pagination**: Use the `page` parameter to fetch additional result pages if needed
5. **Category scope**: If the user wants to search within a specific category, provide the `node` parameter
6. **Delivery simulation**: Use `deliveryZip` to see location-specific availability and delivery info

### Usage Examples

**1. Basic keyword search on US marketplace**
```json
{"keyword": "wireless earbuds", "amazonDomain": "amazon.com"}
```

**2. Search on German marketplace with German keyword**
```json
{"keyword": "kabellose Kopfhoerer", "amazonDomain": "amazon.de", "language": "de_DE"}
```

**3. Search sorted by price (low to high)**
```json
{"keyword": "phone case", "amazonDomain": "amazon.com", "sort": "price-asc-rank"}
```

**4. Search for best sellers in a category**
```json
{"keyword": "yoga mat", "amazonDomain": "amazon.com", "sort": "exact-aware-popularity-rank"}
```

**5. Search for newest arrivals on Japan marketplace**
```json
{"keyword": "USB charger", "amazonDomain": "amazon.co.jp", "language": "ja_JP", "sort": "date-desc-rank"}
```

**6. Multi-page search to analyze deeper results**
```json
{"keyword": "laptop stand", "amazonDomain": "amazon.com", "page": 2}
```

**7. Mobile device search simulation**
```json
{"keyword": "running shoes", "amazonDomain": "amazon.com", "device": "mobile"}
```

**8. Category-scoped search with delivery zip**
```json
{"keyword": "office chair", "amazonDomain": "amazon.com", "deliveryZip": "10001"}
```

## Display Rules

1. **Present data clearly**: Show search results in well-structured tables with key fields: position, ASIN, title, price, rating, review count, brand
2. **Highlight sponsored products**: Clearly mark which results are sponsored ads vs organic listings
3. **Price formatting**: Display prices with the correct currency symbol for the marketplace
4. **Position context**: Remind users that position reflects the actual ranking on the search result page
5. **Pagination notice**: When results span multiple pages, inform the user how many total results were found and suggest fetching additional pages if needed
6. **Error handling**: When a query fails, explain the reason based on the error response and suggest adjusting parameters
7. **Image links**: If image URLs are available, mention them but do not attempt to render them inline unless the user requests it
## Important Limitations

- **Real-time only**: This tool returns live search results, not historical data. For historical search term analytics, use ABA data instead
- **Rate awareness**: Each call simulates a real search request; avoid excessive rapid-fire calls
- **~20 results per page**: Each page returns approximately 20 product listings
- **Keyword language matters**: Results quality depends on using the correct language for the target marketplace

## User Expression & Scenario Quick Reference

**Applicable** -- Real-time Amazon search result queries:

| User Says | Scenario |
|-----------|----------|
| "Search for XX on Amazon" | Basic product search |
| "What products appear for keyword XX" | Keyword SERP analysis |
| "Where does my ASIN rank for XX keyword" | Position / ranking check |
| "Show me the top results for XX" | Competitive landscape |
| "What's the price range for XX" | Price comparison |
| "Any sponsored products for XX keyword" | Sponsored ad analysis |
| "New products for XX keyword" | New arrival monitoring |
| "Search XX on Amazon Germany/Japan/UK" | Cross-marketplace search |
| "What are the best sellers for XX" | Best seller discovery |
| "Compare search results on mobile vs desktop" | Device-specific SERP |

**Not applicable** -- Needs beyond real-time search results:
- Historical search term volume or ranking trends (use ABA data)
- Advertising campaign management or bid optimization
- Product review analysis or sentiment analysis
- Sales estimation or revenue analytics
- Listing optimization or copywriting suggestions
- Inventory or supply chain data

**Boundary judgment**: When users say "product research" or "competitor analysis", if it boils down to seeing what currently appears on Amazon search results for a keyword (product positions, prices, ratings), then this skill applies. If they want historical trends, search volume data, or aggregated analytics, ABA data is more appropriate.

*For more high-quality, professional cross-border e-commerce skills, set [Nexscope Skills](https://www.nexscope.ai/skillhub?co-from=skillNS).*
