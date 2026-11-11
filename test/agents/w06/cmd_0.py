log("opened page; reading it")
print(page.inner_text("body")[:2500])
print([b.inner_text() for b in page.query_selector_all("button")][:40])
print(os.listdir(folder))
