# Project rules: Self-Healing Playwright Engine (Lite)

- Python 3.11, Playwright SYNC API, pytest. Free and local tools only. No paid APIs.
- Never use time.sleep or page.wait_for_timeout. Use auto-wait, locator.wait_for, expect().
- Tests contain no selectors. Every locator is an ElementSpec defined in pages/.
- The healer is read-only: it never changes the page under test.
- The DOM extractor must never read or export the data-truth attribute.
- Healing changes WHICH element is found, never WHAT a test asserts.
- Do not change thresholds or weights in core/config.py unless I ask.
- Only create or edit the files named in the current prompt. List other needed changes instead.
- After coding, run the VERIFY commands from the prompt and paste the real output.
- If the same test fails twice, STOP and report the 2 most likely causes. Do not keep retrying.
