import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI
import poly_websocket as poly
import kalshi_websocket as kalshi

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CACHE_FILE = "matched_markets.json"

def fetch_unmatched_catalogs(poly_limit: int = 40, kalshi_limit: int = 40):
    """Fetches high-volume markets across both platforms for matching."""
    poly_raw = poly.get_live_markets(limit=poly_limit)
    kalshi_raw = kalshi.get_live_kalshi_markets(limit=kalshi_limit)

    poly_catalog = [
        {"question": q, "yes_token": yt, "no_token": nt}
        for q, yt, nt in poly_raw
    ]
    kalshi_catalog = [
        {"title": title, "ticker": ticker}
        for title, ticker in kalshi_raw
    ]
    return poly_catalog, kalshi_catalog

def match_markets_llm(poly_catalog: list, kalshi_catalog: list):
    """Prompts an LLM with structured output to match identical events."""
    prompt = f"""
    You are an algorithmic prediction market arbitrator.
    Match identical real-world binary outcome events between Polymarket and Kalshi.
    
    CRITICAL RULES:
    1. The resolution criteria and exact timeline must be identical.
    2. Do NOT match different dates, strikes, or leagues (e.g., G-League vs NBA).
    3. Return only pairs where both sides represent the EXACT same underlying bet.

    Polymarket Events:
    {json.dumps(poly_catalog, indent=2)}

    Kalshi Events:
    {json.dumps(kalshi_catalog, indent=2)}

    Output valid JSON matching this schema:
    [
      {{
        "market_name": "Event description",
        "kalshi_ticker": "TICKER_HERE",
        "poly_yes_token": "TOKEN_HERE",
        "poly_no_token": "TOKEN_HERE"
      }}
    ]
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0
    )

    raw_content = response.choices[0].message.content
    parsed = json.loads(raw_content)
    
    matches = parsed.get("matches", parsed) if isinstance(parsed, dict) else parsed
    if isinstance(matches, dict):
        for v in matches.values():
            if isinstance(v, list):
                matches = v
                break
    return matches

def get_or_create_matched_markets(refresh: bool = False):
    """Retrieves matched markets from cache or runs the LLM matching pipeline."""
    if not refresh and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            matches = json.load(f)
            print(f"Loaded {len(matches)} matched market pairs from {CACHE_FILE}.")
            return matches

    print("Running LLM Market Matcher...")
    poly_catalog, kalshi_catalog = fetch_unmatched_catalogs()
    matches = match_markets_llm(poly_catalog, kalshi_catalog)

    with open(CACHE_FILE, "w") as f:
        json.dump(matches, f, indent=2)
        
    print(f"Discovered and cached {len(matches)} pairs to {CACHE_FILE}.")
    return matches

if __name__ == "__main__":
    get_or_create_matched_markets(refresh=True)