    def vis(): return page.locator("body").inner_text()
    def flat(t): return t.replace("\n"," | ")
    tb=page.get_by_role("textbox")
    for i in range(tb.count()):
        try: log(f"textbox {i} visible={tb.nth(i).is_visible()} label={tb.nth(i).get_attribute('aria-label')} ph={tb.nth(i).get_attribute('placeholder')}")
        except Exception as e: pass
    vt=[tb.nth(i) for i in range(tb.count()) if tb.nth(i).is_visible()]
    vt[0].fill(str(folder)); log("typed folder path into first visible textbox")
    page.get_by_role("button",name="Add folder").click(); time.sleep(4)
    log("after Add folder: "+flat(vis().split("Keep it on this computer")[-1][:600]))
    page.screenshot(path="f2.png")
    page.get_by_role("tab",name="Work").click(); time.sleep(1)
    tas=page.locator("textarea:visible"); log(f"textareas {tas.count()}")
    def ask(q,wait=40):
        tas.first.fill(q); log("ASK: "+q)
        page.get_by_role("button",name="Ask",exact=True).click()
        time.sleep(wait)
        a=vis(); i=a.find("Clear conversation")
        log("SCREEN AFTER: "+flat(a[max(0,i-1800):i] if i>0 else a[-1500:]))
    page.get_by_role("tab",name="What it knows").click(); time.sleep(3)
    t=vis(); j=t.find("Settings | Settings"); log("KNOWS2: "+flat(t[t.rfind("Settings",0,len(t))-0:][:0]+t.split("Work | Folders | What it knows | Settings")[-1][:3500]))
    page.screenshot(path="k2.png",full_page=True)
    browser.close()
app.stop()
