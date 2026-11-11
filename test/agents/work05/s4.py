from common import *
import os
app = App("ua-05", 7945).start()
folder = make_user_folder(WORK / "ua-05" / "stuff", "project")
for p in ["README.md","app/main.py","app/util.py"]:
    log("=== "+p+"\n"+open(os.path.join(folder,p),encoding="utf-8").read()[:900])
def last(page):
    t=page.locator("body").inner_text()
    i=t.find("1x"); return t[i:i+2500]
def ask(page,q,wait=50):
    log("ASK: "+q)
    page.locator("textarea:visible").first.fill(q)
    page.get_by_role("button",name="Ask",exact=True).click()
    time.sleep(wait)
    log("SCREEN:\n"+last(page))
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.get_by_text("Voice is on").first.click()
    tab(page,"Folders")
    page.locator("textarea:visible").first.fill(str(folder))
    page.get_by_role("button",name="Add folder").click(); time.sleep(6)
    tab(page,"Work")
    sel=page.locator("select:visible")
    log("selects: %d"%sel.count())
    for i in range(sel.count()):
        log("select %d options: %s"%(i, sel.nth(i).locator("option").all_inner_texts()))
    if sel.count(): sel.first.select_option(index=sel.first.locator("option").count()-1)
    ask(page,"Where is the retry logic and is there anything in the code that looks like a bug?")
    shot(page,folder,"ask1")
    ask(page,"Find every TODO or FIXME in this folder")
    ask(page,"Fix the most obvious bug in the code")
    shot(page,folder,"ask3")
finally:
    app.stop()
