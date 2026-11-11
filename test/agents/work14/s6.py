from common import *
import pathlib
app = App("ua-14", 7954).start()
folder = make_user_folder(WORK / "ua-14" / "stuff", "notes")
p=pathlib.Path(folder)
(p/"2026-11-08_journal.md").write_text("# Journal 8 Nov\nStopped at: methods chapter, section 3.2, need to rerun the survey stats.\nNext: email supervisor about ethics form; update Notion board.\n",encoding="utf-8")
(p/"2026-11-weekly-review.md").write_text("# Weekly review\n- Thesis lit review done\n- Methods draft 60%\n- Todo: book viva slot, fix reference list\n",encoding="utf-8")
def body(page): return page.inner_text("body")
def tail_after(page, marker):
    t=body(page); i=t.rfind(marker); return t[i:i+1800] if i>=0 else t[-1800:]
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(2000)
    page.get_by_role("tab", name="Folders").first.click(); page.wait_for_timeout(2000)
    page.get_by_label("Folder to add").fill(str(p)); log("filled folder path")
    page.get_by_role("button", name="Add folder").click(); page.wait_for_timeout(4000)
    log("ADDED: "+body(page)[-900:]); shot(page, folder, "b_added")
    page.get_by_role("tab", name="Work").first.click(); page.wait_for_timeout(800)
    log("WORK: "+body(page)[-1500:])
    ta=page.locator("textarea:visible, input[type=text]:visible")
    log("visible text fields "+str(ta.count()))
    for q in ["Where did I stop on my thesis?","What is on my weekly review to do list?"]:
        f=page.locator("textarea:visible").first if page.locator("textarea:visible").count() else ta.first
        f.fill(q); log("asked: "+q)
        page.get_by_role("button", name="Ask", exact=True).locator("visible=true").first.click()
        page.wait_for_timeout(45000)
        log("AFTER: "+body(page)[-1800:]); shot(page, folder, "d_"+q[:5])
    browser.close()
finally: app.stop()
