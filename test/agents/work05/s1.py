import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
import pickle
LOG=open("actions.log","a",encoding="utf-8")
def log(m):
    s=f"[{time.strftime('%H:%M:%S')}] {m}"; print(s); LOG.write(s+"\n"); LOG.flush()
app = App("ua-05", 7945).start()
folder = make_user_folder(WORK / "ua-05" / "stuff", "project")
log(f"started app, folder={folder}")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    log("opened page; visible text:\n"+page.inner_text("body")[:1500])
    for t in ["Folders"]:
        page.get_by_text(t, exact=True).first.click(); time.sleep(1)
        log("clicked "+t+"\n"+page.inner_text("body")[:1500])
    inputs=page.locator("input:visible, textarea:visible, button:visible")
    for i in range(inputs.count()):
        e=inputs.nth(i); log(f"el {i}: {e.evaluate('e=>e.tagName+\" \"+(e.placeholder||\"\")+\" \"+(e.innerText||\"\").slice(0,40)')}")
    app.stop()
