import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
def log(m):
    s=time.strftime("%H:%M:%S")+" "+m; print(s)
    open(str(WORK/"ua-10"/"actions.log"),"a",encoding="utf8").write(s+"\n")
app = App("ua-10", 7950).start()
folder = make_user_folder(WORK / "ua-10" / "stuff", "messy")
shots=WORK/"ua-10"; 
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    tab=lambda n: page.locator('[role=tab]', has_text=n).first
    tab("Folders").click(); time.sleep(1)
    inp=page.get_by_placeholder('Thesis', exact=False).first; log('inputs: '+str(page.locator('input').evaluate_all('els=>els.map(e=>e.type+":"+e.placeholder+":"+e.offsetParent)')))
    inp.click(); inp.press_sequentially(str(folder), delay=5); time.sleep(1)
    page.locator('button:visible', has_text="Add folder").first.click(); time.sleep(4)
    log("folders after add: "+page.inner_text("body")[-1500:].replace("\n"," | "))
    page.screenshot(path=str(shots/"folders_after.png"))
    log("header: "+page.inner_text("body")[:300].replace("\n"," | "))
    browser.close()
app.stop()
