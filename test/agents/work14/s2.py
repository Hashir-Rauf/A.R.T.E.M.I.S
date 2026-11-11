from common import *
app = App("ua-14", 7954).start()
folder = make_user_folder(WORK / "ua-14" / "stuff", "notes")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(1500)
    try: page.get_by_text("Voice is on").click(timeout=3000); log("unticked voice")
    except Exception as e: log("voice untick failed")
    page.get_by_role("tab", name="Folders").click(); page.wait_for_timeout(1000)
    log("FOLDERS: "+page.inner_text("body")[-1500:])
    log("inputs: "+str([(i.get_attribute("placeholder"), i.get_attribute("type"), i.is_visible()) for i in page.query_selector_all("input,textarea")]))
    log("buttons: "+str([b.inner_text() for b in page.query_selector_all("button") if b.is_visible()]))
    browser.close()
finally:
    app.stop()
