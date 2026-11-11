import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/w09/actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s[:3500].encode("ascii","replace").decode()); LOG.write(s+"\n"); LOG.flush()
app = App("ua-09", 7949).start()
folder = make_user_folder(WORK / "ua-09" / "stuff", "messy")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(2)
    page.get_by_role("tab",name="Folders").click(); time.sleep(1)
    page.get_by_role("button",name="Browse").click(); time.sleep(5)
    log("BROWSE: "+page.inner_text("body").replace(chr(10)," | ")[250:700]); shot(page,folder,"browse")
    page.get_by_role("tab",name="What it knows").click(); time.sleep(2)
    log("WHAT IT KNOWS: "+page.inner_text("body").replace(chr(10)," | ")[560:3000]); shot(page,folder,"knows")
    page.get_by_role("tab",name="Work").click(); time.sleep(1)
    for name in ["Suggest a tidy-up","Undo last change","What changed"]:
        page.get_by_role("button",name=name).click(); time.sleep(6)
        log("CLICK "+name+": "+page.inner_text("body").replace(chr(10)," | ")[-900:])
    ta=page.locator("textarea:visible").first
    for q in ["I am an accountant. If I let you read my clients' tax files, does anything leave this computer? Who is responsible if you get something wrong?"]:
        ta.click(); page.keyboard.type(q,delay=1); page.get_by_role("button",name="Ask",exact=True).click(); log("ASKED: "+q); time.sleep(45)
        log("REPLY: "+page.inner_text("body").replace(chr(10)," | ")[-1300:]); shot(page,folder,"reply")
    page.get_by_role("tab",name="Settings").click(); time.sleep(1)
    log("SETTINGS tail: "+page.inner_text("body").replace(chr(10)," | ")[-1500:])
    browser.close()
finally:
    app.stop()
