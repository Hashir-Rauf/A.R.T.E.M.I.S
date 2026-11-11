box=page.locator("input.border-none, .border-none").first
box.fill("Look through the app folder and tell me what this project does, and suggest a fix for anything that looks buggy"); log("typed question 1")
page.get_by_role("button",name="Ask").click(timeout=5000); log("clicked Ask")
for i in range(30):
    time.sleep(3)
    t=page.inner_text("body")
    if "processing" not in t.split("Suggest a tidy-up")[0][-300:] and i>2: break
log("waited %d polls"%i)
txt=page.inner_text("body"); print(txt[txt.find("Clear conversation")-2500:][:3500])
shot(page, folder, "q1")
