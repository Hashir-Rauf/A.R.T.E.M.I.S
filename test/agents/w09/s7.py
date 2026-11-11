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
    page.get_by_role("checkbox").first.uncheck() if page.get_by_role("checkbox").count() else None
    ta=page.locator("textarea:visible, input:visible").all(); log("fields: "+str([ (t.evaluate("e=>e.tagName"),t.get_attribute("placeholder")) for t in ta]))
    box=page.get_by_placeholder("What would you like done").first if page.get_by_placeholder("What would you like done").count() else page.locator("textarea:visible").first
    box.fill("Hello. I do bookkeeping for small shops. Is it safe to let you read my clients' tax files? Who is responsible if you make a mistake?")
    page.get_by_role("button",name="Ask",exact=True).click(); log("ASKED safety question via fill")
    for i in range(8):
        time.sleep(10); t=page.inner_text("body").replace(chr(10)," | "); 
        if "responsible" in t.lower() and i>0: pass
    log("SCREEN: "+t[t.find("Clear conversation")-1500:t.find("Clear conversation")+50]); shot(page,folder,"safety")
    browser.close()
finally:
    app.stop()
