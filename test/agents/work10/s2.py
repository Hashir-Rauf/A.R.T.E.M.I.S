import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=[]
def log(m):
    s=time.strftime("%H:%M:%S")+" "+m; print(s); LOG.append(s)
    open(str(WORK/"ua-10"/"actions.log"),"a",encoding="utf8").write(s+"\n")
def body(n=1500): return page.inner_text("main, body")[:n].replace("\n"," | ")
app = App("ua-10", 7950).start()
folder = make_user_folder(WORK / "ua-10" / "stuff", "messy")
log("restarted app")
log("files: "+", ".join(p.name for p in folder.iterdir()))
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    tab=lambda n: page.locator('[role=tab]', has_text=n).first
    tab("Folders").click(); time.sleep(1)
    txt=page.locator('[role=tabpanel]:visible').first.inner_text() if page.locator('[role=tabpanel]:visible').count() else body(3000)
    log("Folders panel: "+txt[:1500].replace("\n"," | "))
    shot(page, folder, "02_folders")
    inp=page.locator('input[type=text]:visible, input:not([type]):visible')
    log("visible inputs "+str(inp.count()))
    inp.first.fill(str(folder))
    for b in page.locator('button:visible').all():
        if b.inner_text().strip().lower().startswith("add folder"): log("click "+b.inner_text()); b.click(); break
    time.sleep(3)
    log("after add: "+(page.locator('[role=tabpanel]:visible').first.inner_text()[:1500].replace("\n"," | ")))
    shot(page, folder, "03_added")
    tab("Work").click(); time.sleep(1)
    ta=page.locator('textarea:visible, input[placeholder]:visible').first
    page.get_by_text("Voice is on").first.click() if False else None
    q="What is in my folder? Anything about invoices or reports?"
    ta.fill(q); log("asked: "+q)
    page.locator('button:visible', has_text="Ask").first.click()
    time.sleep(40)
    log("work: "+page.locator('[role=tabpanel]:visible').first.inner_text()[:2500].replace("\n"," | "))
    shot(page, folder, "04_answer")
    browser.close()
app.stop()
