import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
L=open("actions.log","a",encoding="utf-8"); sys.stdout.reconfigure(encoding="utf-8")
def log(m):
    s=f"[{time.strftime('%H:%M:%S')}] {m}"; print(s); L.write(s+"\n"); L.flush()
app = App("ua-11", 7951).start()
folder = make_user_folder(WORK / "ua-11" / "stuff", "messy")
log(f"started app, folder {folder}")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(3000)
    log("opened app; visible text:\n"+page.inner_text("body")[:2500])
    log("buttons: "+str([b.inner_text()[:30] for b in page.query_selector_all("button")][:40]))
    log("inputs: "+str([(i.get_attribute("placeholder"),i.get_attribute("id")) for i in page.query_selector_all("input,textarea")]))
    shot(page, folder, "home")
    browser.close()
app.stop()
