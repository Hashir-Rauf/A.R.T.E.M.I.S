import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
L=open("actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s); L.write(s+"\n"); L.flush()
app = App("ua-04", 7944).start()
folder = make_user_folder(WORK / "ua-04" / "stuff", "notes")
log(f"folder {folder}")
import os
for r,d,f in os.walk(folder):
    for x in f: log("file "+os.path.join(r,x))
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    log("opened app; text: "+page.inner_text("body")[:1500])
    page.get_by_text("Folders").first.click(); time.sleep(1)
    log("Folders tab: "+page.inner_text("body")[:1500])
    inputs=page.locator("input:visible")
    log(f"inputs {inputs.count()}")
    page.screenshot(path="f1.png")
    browser.close()
app.stop()
