page.get_by_placeholder("C:\Users\you\Documents\Thesis").fill(str(folder)); log("typed folder path")
page.get_by_role("button",name="Add folder").click(timeout=5000); log("clicked Add folder")
time.sleep(3)
print(page.inner_text("body")[-1200:])
page.get_by_role("tab",name="Work").click(timeout=5000); log("back to Work")
ta=[e for e in page.query_selector_all("textarea,input[type=text]") if e.is_visible()]
print([(e.get_attribute("placeholder")) for e in ta])
