from common import *
app = App("ua-05", 7945).start()
folder = make_user_folder(WORK / "ua-05" / "stuff", "project")
log(f"folder={folder}")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.get_by_text("Voice is on").first.click(); log("unticked voice")
    tab(page,"Folders"); log("Folders tab:\n"+vis(page,3000))
    els=page.locator("input:visible, textarea:visible, button:visible")
    for i in range(els.count()):
        log("el %d %s"%(i, els.nth(i).evaluate("e=>e.tagName+' ph='+(e.placeholder||'')+' '+(e.innerText||'').slice(0,40)")))
    tab(page,"What it knows"); log("Knows tab:\n"+vis(page,2500))
    tab(page,"Settings"); log("Settings:\n"+vis(page,3500))
finally:
    app.stop()
