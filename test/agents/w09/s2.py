import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/w09/actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s[:2500].encode("ascii","replace").decode()); LOG.write(s+"\n"); LOG.flush()
app = App("ua-09", 7949).start()
folder = make_user_folder(WORK / "ua-09" / "stuff", "messy")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(2)
    def tab(t):
        page.get_by_role("tab",name=t).click(); time.sleep(1.5)
    tab("Settings"); log("SETTINGS: "+page.inner_text("body").replace("\n"," | ")[600:4500]); shot(page,folder,"settings")
    tab("Folders"); log("FOLDERS: "+page.inner_text("body").replace("\n"," | ")[600:3000])
    inputs=page.locator("input:visible"); log("inputs: "+str(inputs.count())+" "+str([inputs.nth(i).get_attribute("placeholder") for i in range(inputs.count())]))
    btns=page.locator("button:visible"); log("buttons: "+str([btns.nth(i).inner_text() for i in range(btns.count())]))
    log("files: "+str(sorted(p.name for p in folder.rglob('*'))))
    browser.close()
finally:
    app.stop()
