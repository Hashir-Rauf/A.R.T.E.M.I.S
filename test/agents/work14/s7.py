from common import *
import pathlib
app = App("ua-14", 7954).start()
p=pathlib.Path(make_user_folder(WORK / "ua-14" / "stuff", "notes"))
(p/"2026-11-08_journal.md").write_text("# Journal 8 Nov\nStopped at: methods chapter, section 3.2, need to rerun the survey stats.\nNext: email supervisor about ethics form; update Notion board.\n",encoding="utf-8")
(p/"2026-11-weekly-review.md").write_text("# Weekly review\n- Thesis lit review done\n- Methods draft 60%\n- Todo: book viva slot, fix reference list\n",encoding="utf-8")
def dump(page,name):
    t=page.inner_text("body"); open(name+".txt","w",encoding="utf-8").write(t); page.screenshot(path=name+".png",full_page=True); return t
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(2000)
    page.get_by_role("tab", name="Folders").first.click(); page.wait_for_timeout(1500)
    page.get_by_label("Folder to add").fill(str(p)); page.get_by_role("button", name="Add folder").click(); page.wait_for_timeout(4000)
    log("added folder")
    page.get_by_role("tab", name="Work").first.click(); page.wait_for_timeout(1000)
    for i,q in enumerate(["Where did I stop on my thesis?","What do I still need to do this week?"]):
        page.get_by_label("What would you like done").fill(q); log("asked: "+q)
        page.get_by_role("button", name="Ask", exact=True).locator("visible=true").first.click()
        page.wait_for_timeout(50000)
        t=dump(page,"ans%d"%i); log("answer region: "+t[t.find("Suggest a tidy-up")-1500:t.find("Suggest a tidy-up")][:1500])
    page.get_by_role("button", name="Suggest a tidy-up").click(); log("clicked Suggest a tidy-up"); page.wait_for_timeout(50000)
    t=dump(page,"tidy"); log("TIDY: "+t[t.find("Suggest a tidy-up"):][:1800])
    for tab in ["What it knows","Settings"]:
        page.get_by_role("tab", name=tab).first.click(); page.wait_for_timeout(2000)
        t=dump(page,tab.replace(" ","_")); log(tab.upper()+": "+t[t.find("stored locally")+14:][:2200])
    browser.close()
finally: app.stop()
