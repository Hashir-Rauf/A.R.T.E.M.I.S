import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open("actions.log","a")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s); LOG.write(s+"\n"); LOG.flush()
app = App("ua-13", 7953).start()
folder = make_user_folder(WORK/"ua-13"/"stuff","messy")
def txt(page,n=1800):
    return page.inner_text("main")[:n] if page.query_selector("main") else page.inner_text("body")[-n:]
try:
  with sync_playwright() as pw:
    browser,page=browser_page(pw,app)
    def tab(n):
        page.locator("button[role=tab]",has_text=n).first.dispatch_event("click"); page.wait_for_timeout(1000); log("clicked tab "+n)
    try: page.get_by_label("Voice is on").uncheck(); log("unticked voice")
    except Exception as e: log("voice untick fail "+str(e)[:80])
    tab("Folders"); log("FOLDERS: "+page.inner_text("body")[-2500:].replace("\n"," | "))
    inputs=page.query_selector_all("input[type=text],input:not([type]),input[type=search]")
    log("inputs "+str([(i.get_attribute("placeholder"),i.is_visible()) for i in inputs]))
    shot(page,folder,"folders")
    browser.close()
finally:
  app.stop()
