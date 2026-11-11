import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/scratch15/actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s.encode("ascii","replace").decode()); LOG.write(s+"\n"); LOG.flush()
app = App("ua-15", 7955).start()
folder = make_user_folder(WORK / "ua-15" / "stuff", "notes")
log("folder "+str(folder))
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(3000)
    log("landing text: "+page.inner_text("body")[:2500])
    shot(page, folder, "landing")
    for t in ["Folders","What it knows","Settings"]:
        try:
            page.get_by_text(t, exact=True).first.click(); page.wait_for_timeout(1000)
            log(f"TAB {t}: "+page.inner_text("body")[:2500])
        except Exception as e: log("tab fail "+t+str(e)[:100])
    browser.close()
finally:
    app.stop()
