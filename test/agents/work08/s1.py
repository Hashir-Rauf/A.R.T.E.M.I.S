import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
def log(m):
    l=f"[{time.strftime('%H:%M:%S')}] {m}"; print(l.encode("ascii","replace").decode()); open("actions.log","a",encoding="utf-8").write(l+"\n")
app = App("ua-08", 7948).start()
folder = make_user_folder(WORK / "ua-08" / "stuff", "messy")
log(f"folder {folder}")
import os
for r,d,f in os.walk(folder): log(f"files {r}: {f}")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(3)
    log("opened app; body: "+page.inner_text("body")[:1500])
    shot(page, folder, "08_home")
    for t in ["Folders"]:
        page.get_by_role("tab",name=t).click(); time.sleep(1)
        log(f"clicked {t}: "+page.inner_text("body")[:1200])
    browser.close()
app.stop()
