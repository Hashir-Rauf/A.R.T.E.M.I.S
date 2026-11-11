import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/w09/actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s[:1800].encode("ascii","replace").decode()); LOG.write(s+"\n"); LOG.flush()
app = App("ua-09", 7949).start()
folder = make_user_folder(WORK / "ua-09" / "stuff", "messy")
log("folder "+str(folder))
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(3)
    log("HOME TEXT: "+page.inner_text("body").replace("\n"," | "))
    shot(page, folder, "home")
    for t in ["Folders","What it knows","Settings"]:
        page.get_by_text(t,exact=True).first.click(); time.sleep(1.5)
        log("TAB "+t+": "+page.inner_text("body").replace("\n"," | "))
    log("files: "+str([p.name for p in folder.iterdir()]))
    browser.close()
finally:
    app.stop()
