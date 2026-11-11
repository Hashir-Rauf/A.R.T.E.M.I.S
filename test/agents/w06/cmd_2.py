for el in page.get_by_text("Folders", exact=True).all():
    if el.is_visible():
        el.click(); log("clicked Folders tab"); break
time.sleep(1)
print(page.inner_text("body")[-1800:])
print([(i.get_attribute("placeholder"),i.get_attribute("id")) for i in page.query_selector_all("input")])
