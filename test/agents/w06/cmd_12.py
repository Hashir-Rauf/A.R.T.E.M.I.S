say("Fix the bug in add() in app/util.py")
print("--- util.py on disk:", open(os.path.join(folder,"app","util.py")).read())
btn=[(b.inner_text(),b.is_enabled()) for b in page.query_selector_all("button") if b.is_visible() and b.inner_text() in ("Approve","No, leave it","Undo last change","Approve, don't ask again")]
print(btn)
