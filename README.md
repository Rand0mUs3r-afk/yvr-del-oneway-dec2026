# YVR → DEL: December 2026 one-way fare candidates

Standalone, manual GitHub-hosted checker. No downloads or installation on your computer; no paid API, proxy or CAPTCHA service.

## Run from your browser
1. Open this repository's **Actions** tab.
2. Select **Check December one-way fares**.
3. Click **Run workflow**. Choose `all` or an individual source.
4. Dates default to December 1–31, 2026. For the first validation, set both dates to `2026-12-01`.
5. Open the run, then its **Summary**. The scan writes its report there: candidates sorted by CAD amount, source coverage, requested dates and captured card text. No result download is necessary.

## What is implemented
Experimental browser adapters attempt Google Flights, KAYAK Canada and Trip.com. A full request targets all 31 December dates on each selected source. Requests specify YVR → DEL, one-way, one adult, economy, CAD. Up to 40 loaded result elements per date are inspected; the scanner does not enumerate all available fares, scroll through all inventory or complete checkout. No two-stop or CAD1700 round-trip budget filter is applied.

Only cards containing YVR before DEL and exactly one distinct explicitly labelled CAD/CA$/C$ amount are ranked. Bare $ is not assumed to be CAD; round-trip-labelled cards are rejected. Unknown dates or fare context are NOT independently verified just because a search URL requested them.

## Important limitations — read before relying on a result
The adapters have offline parser/link/date/report checks, but have **not been live-validated from GitHub's runner**. A source may block cloud browsers, redirect, change its layout, or fail to expose readable cards. A first run is validation, not a guarantee of working multi-site prices.

`captured` means displayed price candidates were extracted, NOT a confirmed bookable one-way fare. Dates, passenger/cabin settings, taxes, baggage, ticket protection and final checkout totals require review on the linked source. Your 23kg checked/cabin bag requirement is not priced automatically. The lowest captured amount is not a guaranteed cheapest available flight.

Blocked/failed/unreadable dates are explicitly reported, never converted into no availability. A source stops after a challenge or three consecutive failed dates. Remaining dates are marked not attempted. Other selected sources are still attempted. If zero candidates are captured, the workflow fails deliberately and the Summary explains the unsuccessful coverage.

## Cost and privacy
Use standard GitHub-hosted runners in this PUBLIC repository. Workflow compute for that public-repository configuration is free under GitHub's documented policy. This project does not upload artifacts, publish Pages, start schedules, store credentials, open passenger pages or book tickets. It installs its dependencies only on the temporary GitHub runner. The report is visible to readers who can see this public repository's workflow run. Do not add personal data, passwords or payment details.

Workflow permissions are read-only; it does not commit reports or alter repository settings. A manual run is required. No stealth measures, CAPTCHA bypass, paid APIs or proxies are included.
