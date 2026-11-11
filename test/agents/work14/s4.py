from common import *
app = App("ua-14", 7954).start()
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(2500)
    page.get_by_role("tab", name="Folders").last.click(); page.wait_for_timeout(2000)
    log("TEXT: "+page.inner_text("body")[-900:])
    log("inputs "+str([(i.get_attribute("placeholder"),i.is_visible()) for i in page.query_selector_all("input")]))
    page.screenshot(path="dbg.png")
    browser.close()
finally: app.stop()
