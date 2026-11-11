els=[(e.evaluate("e=>e.tagName"),e.get_attribute("placeholder"),e.get_attribute("aria-label"),e.get_attribute("class")) for e in page.query_selector_all("textarea,input,select") if e.is_visible()]
print(els)
