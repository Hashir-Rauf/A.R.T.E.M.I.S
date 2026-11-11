from common import *
import os
app = App("ua-05", 7945).start()
folder = make_user_folder(WORK / "ua-05" / "stuff", "project")
for r,d,f in os.walk(folder): log("FILE "+r+" "+str(f))
def ask(page,q,wait=45):
    log("ASK: "+q)
    page.locator("textarea:visible").first.fill(q)
    page.get_by_role("button",name="Ask",exact=True).click()
    time.sleep(wait)
    log("SCREEN:\n"+page.locator("main, body").first.inner_text()[-2200:])
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.get_by_text("Voice is on").first.click()
    tab(page,"Folders")
    page.locator("textarea:visible").first.fill(str(folder))
    page.get_by_role("button",name="Add folder").click(); time.sleep(6)
    log("after add:\n"+vis(page,1800)); shot(page,folder,"folders")
    tab(page,"Work")
    ask(page,"Where did the retry logic for the payment client live, and is there anything in the code that looks like a bug?")
    shot(page,folder,"ask1")
    ask(page,"Find every TODO or FIXME in this folder")
    ask(page,"Suggest a fix for the most obvious bug, show me as a diff")
    shot(page,folder,"ask3")
finally:
    app.stop()
