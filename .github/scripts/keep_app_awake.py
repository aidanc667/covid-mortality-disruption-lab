"""Visits the deployed Streamlit app with a real headless browser so it
never crosses Streamlit Community Cloud's 12-hour inactivity sleep
threshold.

A plain HTTP request (curl, requests.get) does not work for this: a
GET only fetches the static page shell, but Streamlit's idle timer is
only reset by an actual WebSocket connection, which the page's own
JavaScript establishes after it loads. A headless browser executes
that JavaScript the same way a real visitor's browser would; a bare
HTTP client never does. If the app has already gone to sleep, this
also finds and clicks the "Yes, get this app back up!" button so the
next real visitor doesn't have to.

The button is matched two ways: primarily by its `data-testid`
attribute (`wakeup-button-viewer`, confirmed against a real working
community implementation -- https://github.com/vicenteaguero/streamlit-wakeup
-- as the stable selector Streamlit Cloud's own frontend actually uses,
not a guess), with the earlier text-based match kept as a fallback in
case that attribute ever changes. It's a plain page-level element, not
nested in an iframe or a closed shadow root.
"""
from playwright.sync_api import sync_playwright

APP_URL = "https://covid-mortality-disruption-lab.streamlit.app"
WAKE_BUTTON_SELECTOR = '[data-testid="wakeup-button-viewer"]'
WAKE_BUTTON_TEXT = "get this app back up"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(APP_URL, timeout=60_000)
        page.wait_for_timeout(3_000)

        wake_button = page.locator(WAKE_BUTTON_SELECTOR)
        if wake_button.count() == 0:
            wake_button = page.get_by_text(WAKE_BUTTON_TEXT, exact=False)

        if wake_button.count() > 0:
            print("App was asleep -- clicking the wake-up button.")
            wake_button.first.click()
            page.wait_for_timeout(30_000)
        else:
            print("App was already awake -- this visit resets its idle timer.")

        browser.close()


if __name__ == "__main__":
    main()
