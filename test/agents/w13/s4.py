import sys,time,os; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open("actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s); LOG.write(s+"\n"); LOG.flush()
app = App("ua-13", 7953).start()
folder = WORK/"ua-13"/"stuff"
def body(page,n=1500): return page.inner_text("body")[-n:].replace("\n"," | ")
try:
  with sync_playwright() as pw:
    browser,page=browser_page(pw,app)
    def tab(n):
        page.locator("button[role=tab]",has_text=n).first.dispatch_event("click"); page.wait_for_timeout(1500); log("clicked tab "+n)
    def click(t):
        page.get_by_role("button",name=t).first.dispatch_event("click"); log("clicked "+t)
    try: page.get_by_label("Voice is on").uncheck()
    except Exception: pass
    log("start body: "+body(page,300))
    tab("Folders")
    if "stuff" not in page.inner_text("body"):
        page.get_by_label("Folder to add").fill(str(folder)); click("Add folder"); page.wait_for_timeout(2500); log("re-added folder")
    tab("Work")
    click("Suggest a tidy-up"); page.wait_for_timeout(25000)
    click("Approve"); page.wait_for_timeout(6000)
    log("AFTER APPROVE: "+body(page,1500)); log("files now: "+str(sorted(os.listdir(folder))))
    shot(page,folder,"approved")
    click("What changed"); page.wait_for_timeout(4000); log("WHATCHANGED: "+body(page,1200))
    click("Undo last change"); page.wait_for_timeout(6000); log("AFTER UNDO: "+body(page,1200)); log("files now: "+str(sorted(os.listdir(folder))))
    tab("What it knows"); log("KNOWS: "+body(page,2000)); shot(page,folder,"knows")
    tab("Settings"); log("SETTINGS: "+page.inner_text("body")[-3500:].replace("\n"," | ")); shot(page,folder,"settings")
    browser.close()
finally:
  app.stop()
