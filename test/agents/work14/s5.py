from common import *
app = App("ua-14", 7954).start()
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(2500)
    page.get_by_role("tab", name="Folders").first.click(); page.wait_for_timeout(1500)
    log("inputs "+str([(i.get_attribute("placeholder"),i.get_attribute("type"),i.is_visible()) for i in page.query_selector_all("input,textarea")]))
    page.screenshot(path="dbg.png", full_page=True)
    log("html of folders area: "+page.evaluate("()=>{const e=[...document.querySelectorAll('input')].filter(i=>i.offsetParent);return e.map(i=>i.outerHTML).join('|')}")[:800])
    browser.close()
finally: app.stop()
