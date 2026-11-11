import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(str(WORK/"ua-13"/"actions.log") if (WORK/"ua-13").exists() else "actions.log","a")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s); LOG.write(s+"\n"); LOG.flush()
app = App("ua-13", 7953).start()
folder = make_user_folder(WORK/"ua-13"/"stuff","messy")
log("folder "+str(folder))
try:
  with sync_playwright() as pw:
    browser,page=browser_page(pw,app)
    log("opened app")
    print(page.inner_text("body")[:2500])
    print([ (b.inner_text()[:30]) for b in page.query_selector_all("button")][:40])
    print([ (i.get_attribute("placeholder"),i.get_attribute("id")) for i in page.query_selector_all("input,textarea")])
    shot(page,folder,"first")
    browser.close()
finally:
  app.stop()
