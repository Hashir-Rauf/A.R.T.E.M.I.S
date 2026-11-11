from common import *
import pathlib
app = App("ua-14", 7954).start()
folder = make_user_folder(WORK / "ua-14" / "stuff", "notes")
p=pathlib.Path(folder)
(p/"2026-11-08_journal.md").write_text("# Journal 8 Nov\nStopped at: methods chapter, section 3.2, need to rerun the survey stats.\nNext: email supervisor about ethics form; update Notion board.\n",encoding="utf-8")
(p/"2026-11-weekly-review.md").write_text("# Weekly review\n- Thesis lit review done\n- Methods draft 60%\n- Todo: book viva slot, fix reference list\n",encoding="utf-8")
def txt(page,n=1800): return page.inner_text("body")[-n:]
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(1500)
    try: page.get_by_text("Voice is on").click(timeout=3000); log("unticked voice")
    except Exception: log("voice untick failed")
    page.get_by_role("tab", name="Folders").click(); page.wait_for_timeout(500)
    page.wait_for_timeout(1000); log("pre: "+str([(i.get_attribute("placeholder"),i.is_visible()) for i in page.query_selector_all("input")])); 
    inp=page.locator("input:visible").last; inp.click(); inp.type(str(p), delay=5); log("typed path, value="+inp.input_value())
    page.get_by_role("button", name="Add folder").locator("visible=true").click(); page.wait_for_timeout(3000)
    log("ADDED: "+txt(page,700)); shot(page, folder, "b_added")
    page.get_by_role("tab", name="Work").first.click(); page.wait_for_timeout(500)
    box=page.get_by_placeholder("Where I stopped, what to do next") 
    log("work inputs: "+str([(i.get_attribute("placeholder"), i.is_visible()) for i in page.query_selector_all("input,textarea")]))
    page.screenshot(path=str(p/"c_work.png"))
    # ask where I stopped
    ta=[i for i in page.query_selector_all("input,textarea") if i.is_visible() and i.get_attribute("type")!="checkbox"]
    log("visible fields: "+str(len(ta)))
    ta[0].fill("Where did I stop on my thesis?")
    page.get_by_role("button", name="Ask", exact=True).locator("visible=true").click(); log("asked: where did I stop")
    page.wait_for_timeout(40000)
    log("REPLY: "+txt(page,2000)); shot(page, folder, "d_reply")
    ta[0].fill("What is on my weekly review to do list?")
    page.get_by_role("button", name="Ask", exact=True).locator("visible=true").click(); log("asked: weekly review todo")
    page.wait_for_timeout(40000)
    log("REPLY2: "+txt(page,2000))
    browser.close()
finally:
    app.stop()