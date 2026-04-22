# Crawler Module

This module contains the web crawler functionality for the sample search engine.

## Files

- `crawler.py`: Main crawler script that fetches web pages, extracts text, and indexes words into the database.
- `seeds.py`: Contains a list of seed URLs for initial crawling.
- `__init__.py`: Makes this directory a Python package.

## Features

- Crawls websites starting from seed URLs.
- Extracts and tokenizes text content.
- Indexes words with their frequencies, excluding stop words.
- Stores page data and word indices in the database.
- Auto-seeds from RSS feeds and Google search results.
- Handles duplicates and already-crawled pages.

## Usage

Run the crawler from the project root:

```bash
python -m crawler.crawler
```

Or directly:

```bash
cd crawler
python crawler.py
```

This will:
1. Initialize the database if needed.
2. Crawl static seed URLs.
3. Gather fresh seeds from RSS feeds and Google topics.
4. Crawl the new seeds.

## Dependencies

- requests
- beautifulsoup4
- feedparser
- Database connection (via db module)

## Configuration

- Modify `SEED_URLS` in `seeds.py` for custom starting points.
- Adjust `RSS_FEEDS` and `GOOGLE_TOPICS` in `crawler.py` for auto-seeding.
- Change `max_pages` in the crawl function for crawl depth.