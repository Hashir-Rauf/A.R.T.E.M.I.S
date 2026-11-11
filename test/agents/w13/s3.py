import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open("actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s); LOG.write(s+"\n"); LOG.flush()
app = App("ua-13", 7953).start()
folder = make_user_folder(WORK/"ua-13"/"stuff","messy")
def body(page,n=1500): return page.inner_text("body")[-n:].replace("\n"," | ")
try:
  with sync_playwright() as pw:
    browser,page=browser_page(pw,app)
    def tab(n):
        page.locator("button[role=tab]",has_text=n).first.dispatch_event("click"); page.wait_for_timeout(1200); log("clicked tab "+n)
    def click(t):
        page.get_by_role("button",name=t).first.dispatch_event("click"); log("clicked "+t)
    try: page.get_by_label("Voice is on").uncheck(); log("unticked voice")
    except Exception as e: log("voice fail")
    tab("Folders")
    page.get_by_label("Folder to add").fill(str(folder)); log("typed folder path")
    click("Add folder"); page.wait_for_timeout(2500)
    log("AFTER ADD: "+body(page,1200)); shot(page,folder,"added")
    tab("Work")
    box=page.get_by_placeholder("Tidy up this folder")
    def ask(q,wait=40000):
        box.fill(q); log("ASK: "+q); click("Ask")
        page.wait_for_timeout(wait); log("SAW: "+body(page,1800))
    ask("where is my budget file")
    ask("which invoice is the latest one")
    shot(page,folder,"answers")
    click("Suggest a tidy-up"); page.wait_for_timeout(30000); log("TIDY: "+body(page,2200)); shot(page,folder,"tidy")
    browser.close()
finally:
  app.stop()
