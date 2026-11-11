import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
W=WORK/"ua-10"
def log(m):
    s=time.strftime("%H:%M:%S")+" "+m; print(s)
    open(str(W/"actions.log"),"a",encoding="utf8").write(s+"\n")
app = App("ua-10", 7950).start()
folder = make_user_folder(W/"stuff", "messy")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    tab=lambda n: page.locator('[role=tab]', has_text=n).first
    def panel(n=2500): return page.locator('[role=tabpanel]:visible').first.inner_text()[:n].replace("\n"," | ")
    log("SESSION2 start")
    tab("Folders").click(); time.sleep(1)
    inp=page.get_by_placeholder('Thesis', exact=False).first
    if page.get_by_text("18 files").count()==0:
        inp.click(); inp.press_sequentially(str(folder), delay=5)
        page.locator('button:visible', has_text="Add folder").first.click(); time.sleep(4)
    log("folders: "+page.inner_text("body")[300:900].replace("\n"," | "))
    tab("Work").click(); time.sleep(1)
    try: page.get_by_label("Voice is on").first.uncheck(); log("unticked voice")
    except Exception as e: log("voice untick failed")
    def ask(q, wait=45):
        ta=page.get_by_placeholder("What would you like done", exact=False).first
        if ta.count()==0: ta=page.locator('textarea:visible').first
        ta.click(); ta.press_sequentially(q, delay=3); log("ASK: "+q)
        page.locator('button:visible', has_text="Ask").first.click()
        time.sleep(wait)
        t=page.locator('[role=tabpanel]:visible').first.inner_text()
        i=t.find(q[:20]); log("SAW: "+t[max(0,i-100):i+1800].replace("\n"," | "))
        page.screenshot(path=str(W/("ask_%d.png"%int(time.time()))))
    ask("Where did I leave off? What is in this folder?")
    ask("Which files are invoices and what do they say?")
    ask("Draft a short polite email to a vendor asking about the late April invoice")
    ask("Suggest a tidy-up of this folder", 50)
    log("buttons now: "+" / ".join(page.locator('button:visible').all_inner_texts())[:600])
    browser.close()
app.stop()
