page.click("text=Voice is on") if False else None
try:
    cb=page.get_by_label("Voice is on (microphone allowed)"); 
    if cb.is_checked(): cb.uncheck(); log("unticked voice")
except Exception as e: log("voice untick fail "+str(e)[:80])
page.get_by_role("button",name="Folders").first.click(); log("clicked Folders tab")
time.sleep(1)
print(page.inner_text("body")[:1800])
print([ (i.get_attribute("placeholder"),i.get_attribute("id")) for i in page.query_selector_all("input")])
shot(page, folder, "folders")
