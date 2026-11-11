import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=[]
def log(m):
    s=time.strftime("%H:%M:%S")+" "+m; print(s); LOG.append(s)
    open(str(WORK/"ua-10"/"actions.log"),"w",encoding="utf8").write("\n".join(LOG))
(WORK/"ua-10").mkdir(parents=True,exist_ok=True)
app = App("ua-10", 7950).start()
folder = make_user_folder(WORK / "ua-10" / "stuff", "messy")
log("started app; folder "+str(folder))
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    log("opened page: "+page.inner_text("body")[:600].replace("\n"," | "))
    shot(page, folder, "01_home")
    page.get_by_text("Folders").first.click(); time.sleep(1)
    log("Folders tab: "+page.inner_text("body")[:800].replace("\n"," | "))
    inputs=page.locator("input[type=text], input:not([type])")
    log("inputs count "+str(inputs.count()))
    inputs.first.fill(str(folder))
    btns=page.locator("button")
    log("buttons: "+" / ".join(btns.all_inner_texts()))
    for b in btns.all():
        t=b.inner_text().lower()
        if "add" in t: b.click(); break
    time.sleep(2)
    log("after add: "+page.inner_text("body")[:900].replace("\n"," | "))
    shot(page, folder, "02_folders")
    page.get_by_text("Work").first.click(); time.sleep(1)
    ta=page.locator("textarea, input[type=text]").last
    q="Where did I leave off? What is in my folder?"
    ta.fill(q); ta.press("Enter"); log("asked: "+q)
    time.sleep(30)
    log("work page: "+page.inner_text("body")[:1800].replace("\n"," | "))
    shot(page, folder, "03_work")
    page.get_by_text("What it knows").first.click(); time.sleep(2)
    log("knows: "+page.inner_text("body")[:1200].replace("\n"," | "))
    page.get_by_text("Settings").first.click(); time.sleep(2)
    log("settings: "+page.inner_text("body")[:1800].replace("\n"," | "))
    browser.close()
app.stop()
