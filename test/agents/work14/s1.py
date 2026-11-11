from common import *
app = App("ua-14", 7954).start()
folder = make_user_folder(WORK / "ua-14" / "stuff", "notes")
log(f"folder {folder}")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    log("opened app")
    page.wait_for_timeout(2000)
    log("SCREEN: "+page.inner_text("body")[:1500])
    shot(page, folder, "a_home")
    for t in ["Folders"]:
        page.get_by_text(t, exact=True).first.click(); page.wait_for_timeout(1000)
        log("Folders tab: "+page.inner_text("body")[:1200])
    log("inputs: "+str([ (i.get_attribute("placeholder"), i.get_attribute("type")) for i in page.query_selector_all("input,textarea")]))
    log("buttons: "+str([b.inner_text() for b in page.query_selector_all("button")]))
    browser.close()
finally:
    app.stop()
