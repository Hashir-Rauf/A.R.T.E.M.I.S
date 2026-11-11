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
    P=lambda n=2200: page.locator('[role=tabpanel]:visible').first.inner_text()[:n].replace("\n"," | ")
    log("SESSION3 start")
    tab("Folders").click(); time.sleep(1)
    if page.get_by_text("18 files").count()==0 and page.get_by_text(" files").count()<2:
        inp=page.get_by_placeholder('Thesis', exact=False).first
        inp.click(); inp.press_sequentially(str(folder), delay=5)
        page.locator('button:visible', has_text="Add folder").first.click(); time.sleep(4)
    log("folders: "+P(700))
    tab("Work").click(); time.sleep(1)
    try: page.get_by_label("Voice is on").first.uncheck()
    except: pass
    log("CLICK Suggest a tidy-up")
    page.locator('button:visible', has_text="Suggest a tidy-up").first.click(); time.sleep(50)
    log("SAW: "+page.locator('[role=tabpanel]:visible').first.inner_text()[-1800:].replace("\n"," | "))
    page.screenshot(path=str(W/"tidy.png"))
    bs=page.locator('button:visible'); log("buttons: "+" / ".join(bs.all_inner_texts())[:500])
    page.locator('button:visible', has_text="No, leave it").first.click(); time.sleep(3)
    log("CLICK No leave it -> "+page.locator('[role=tabpanel]:visible').first.inner_text()[-500:].replace("\n"," | "))
    log("CLICK What changed")
    page.locator('button:visible', has_text="What changed").first.click(); time.sleep(8)
    log("SAW: "+page.locator('[role=tabpanel]:visible').first.inner_text()[-700:].replace("\n"," | "))
    log("CLICK Repeated tasks")
    page.locator('button:visible', has_text="Repeated tasks").first.click(); time.sleep(8)
    log("SAW: "+page.locator('[role=tabpanel]:visible').first.inner_text()[-600:].replace("\n"," | "))
    tab("What it knows").click(); time.sleep(3)
    log("KNOWS: "+P(2500)); page.screenshot(path=str(W/"knows.png"))
    tab("Settings").click(); time.sleep(3)
    log("SETTINGS: "+P(3500)); page.screenshot(path=str(W/"settings.png"))
    browser.close()
app.stop()
