import argparse
import collections
import html
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

SOURCES = ("google", "kayak", "trip")
SELECTORS = {"google": '[role="listitem"]', "kayak": '[data-resultid], .nrc6', "trip": '[data-testid^="u-flight-card-"], [data-shoppinginfoid]'}


def days_between(first, last):
    a, b = date.fromisoformat(first), date.fromisoformat(last)
    if a > b or any((d.year, d.month) != (2026, 12) for d in (a, b)):
        raise ValueError("Use dates December 1–31, 2026, in ascending order")
    return [(a + timedelta(days=i)).isoformat() for i in range((b-a).days+1)]


def search_url(source, day):
    if source == "google":
        return "https://www.google.com/travel/flights?" + urlencode({"hl":"en","curr":"CAD","q":f"One way flights from YVR to DEL on {day} for 1 adult economy"})
    if source == "kayak":
        return f"https://www.ca.kayak.com/flights/YVR-DEL/{day}?sort=price_a&currency=CAD&adults=1&cabin=e"
    if source == "trip":
        return "https://ca.trip.com/flights/showfarefirst?" + urlencode({"dcity":"YVR","acity":"DEL","ddate":day,"triptype":"OW","class":"Y","quantity":1,"childqty":0,"babyqty":0,"locale":"en-CA","curr":"CAD","sort":"price"})
    raise ValueError("Unknown source")


def parse_card(text):
    text = text.replace("\u00a0", " ")
    if not re.search(r"\bYVR\b", text) or not re.search(r"\bDEL\b", text):
        return None
    if text.index("YVR") > text.index("DEL") or re.search(r"round[- ]trip", text, re.I):
        return None
    amounts = {round(float(x.replace(",", ""))*100) for x in re.findall(r"(?:CAD|CA\$|C\$)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text)}
    if len(amounts) != 1:
        return None
    return next(iter(amounts))/100


def cell(value):
    return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ")


def report(rows, coverage, dates):
    ranked = sorted(rows, key=lambda x:(x["price"], x["day"], x["source"]))
    out = ["# YVR → DEL · December 2026 · One-way price candidates", "",
           f"UTC run time: {datetime.now(timezone.utc).isoformat()}", "",
           "One adult, economy, requested CAD. No paid API, proxy or CAPTCHA service.", "",
           "> Experimental browser adapters, not a guaranteed market-wide minimum. Requested dates, one-way fare basis, passenger/cabin settings, baggage, taxes, final checkout total and ticket protection are not comprehensively verified. Site blocks or missing selectors are failures, NOT no availability.", "",
           "## Cheapest observed price candidates", ""]
    if ranked:
        best = ranked[0]
        out += [f'Lowest captured amount: CAD {best["price"]:,.2f} · requested date {best["day"]} · {best["source"]}. Unverified; review on source.', "",
                "| Requested departure | Source | Displayed CAD | Open source search |", "|---|---|---:|---|"]
        for r in ranked[:40]:
            out.append(f'| {r["day"]} | {r["source"]} | {r["price"]:,.2f} | [Review]({r["url"]}) |')
    else:
        out += ["No rankable CAD flight-card prices captured. This is an unsuccessful/incomplete price check, not evidence of no flights."]
    out += ["", "## Source coverage", "", "| Source | Dates with price candidates | Other date outcomes |", "|---|---:|---|"]
    for source in SOURCES:
        records = [x for x in coverage if x["source"] == source]
        if not records:
            out.append(f"| {source} | 0 | Not selected |")
            continue
        counts = collections.Counter(x["status"] for x in records)
        out.append(f'| {source} | {counts.pop("captured",0)}/{len(dates)} | {cell(dict(counts))} |')
    out += ["", "## Date-by-date status", "", "| Requested departure | Source | Status | Detail |", "|---|---|---|---|"]
    for x in coverage:
        out.append(f'| {x["day"]} | {x["source"]} | {x["status"]} | {cell(x["message"])} |')
    for r in ranked[:10]:
        out += ["", f'<details><summary>{cell(r["source"])} · {r["day"]} · CAD {r["price"]:,.2f} · captured card</summary><pre>{html.escape(r["text"])}</pre></details>']
    return "\n".join(out) + "\n"


def collect(page, source, day):
    url = search_url(source, day)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    reject = page.get_by_role("button", name=re.compile(r"^Reject all$",re.I))
    if reject.count() == 1 and reject.is_visible():
        reject.click(timeout=10000)
    deadline = time.monotonic() + 30
    previous = None
    stable = 0
    candidates = []
    while time.monotonic() < deadline:
        body = page.locator("body").inner_text(timeout=10000).casefold()
        if any(x in body for x in ("verify you are human","access denied","unusual traffic","complete the captcha","are you a robot")) or "/sorry/" in page.url:
            return [], "blocked", "Access challenge; no bypass attempted"
        locator = page.locator(SELECTORS[source])
        texts = []
        for i in range(min(locator.count(), 40)):
            item = locator.nth(i)
            if item.is_visible():
                texts.append(item.inner_text(timeout=5000))
        candidates = [text for text in dict.fromkeys(texts) if parse_card(text) is not None]
        stable = stable+1 if candidates and candidates == previous else 0
        previous = candidates
        if stable >= 2:
            return [{"source":source,"day":day,"price":parse_card(text),"url":url,"text":text} for text in candidates], "captured", f"{len(candidates)} price candidates; loaded cards only"
        page.wait_for_timeout(1000)
    return [], "unreadable", "No stable unambiguous CAD route cards; selector, currency, consent or page-state mismatch possible"


def self_test():
    assert len(days_between("2026-12-01","2026-12-31")) == 31
    assert days_between("2026-12-31","2026-12-31") == ["2026-12-31"]
    for bad in ("2026-11-30", "2027-01-01"):
        try:
            days_between(bad,bad)
            raise AssertionError("Invalid month accepted")
        except ValueError:
            pass
    assert parse_card("YVR DEL CAD 1,234.50") == 1234.5
    assert parse_card("YVR DEL C$900") == 900
    assert parse_card("YVR DEL CA$800") == 800
    assert parse_card("YVR DEL $700") is None
    assert parse_card("DEL YVR CAD 700") is None
    assert parse_card("YVR DEL CAD 700 round-trip") is None
    assert parse_card("YVR DEL CAD 700 CAD 900") is None
    assert parse_card("YVR DEL CAD 700 CAD 700") == 700
    assert "triptype=OW" in search_url("trip","2026-12-01")
    assert "curr=CAD" in search_url("google","2026-12-01")
    assert "2026-12-01" in search_url("kayak","2026-12-01")
    summary = report([],[],["2026-12-01"])
    assert "unsuccessful/incomplete" in summary
    print("Offline parser/link/date/report checks passed; NOT live adapter validation.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--first",default="2026-12-01")
    parser.add_argument("--last",default="2026-12-31")
    parser.add_argument("--source",choices=("all",)+SOURCES,default="all")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    dates = days_between(args.first,args.last)
    selected = SOURCES if args.source == "all" else (args.source,)
    rows, coverage = [], []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for source in selected:
                    context = browser.new_context(locale="en-CA",viewport={"width":1440,"height":1000},service_workers="block")
                    context.route(re.compile(r"/flights/passenger(?:[/?]|$)"),lambda route:route.abort())
                    page = context.new_page()
                    failures = 0
                    stop_reason = None
                    try:
                        for day in dates:
                            if stop_reason:
                                coverage.append({"source":source,"day":day,"status":"not_attempted","message":stop_reason})
                                continue
                            print(f"Checking {source} {day}",flush=True)
                            try:
                                offers, status, message = collect(page,source,day)
                                rows.extend(offers)
                            except Exception as error:
                                offers, status, message = [], "error", type(error).__name__
                            coverage.append({"source":source,"day":day,"status":status,"message":message})
                            failures = 0 if status == "captured" else failures+1
                            if status == "blocked":
                                stop_reason = "Source stopped after access challenge"
                            elif failures >= 3:
                                stop_reason = "Source stopped after three consecutive failed dates; no retry loop"
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        text = report(rows,coverage,dates)
        destination = os.environ.get("GITHUB_STEP_SUMMARY")
        if destination:
            with open(destination,"a",encoding="utf-8") as f:
                f.write(text)
        else:
            print(text)
    if not rows:
        raise SystemExit("No price candidates captured. Review the source-status report; do not treat this as a successful fare check.")

if __name__ == "__main__":
    main()
