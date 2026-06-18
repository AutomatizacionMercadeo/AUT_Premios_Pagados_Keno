from playwright.sync_api import sync_playwright

class BrowserManager:
    def __init__(self, headless):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None

    def open(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page(ignore_https_errors=True, accept_downloads=True)
        return self.page

    def close(self):
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
