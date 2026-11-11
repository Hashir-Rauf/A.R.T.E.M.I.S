def ask_wait(maxs=90):
    page.get_by_role("button",name="Ask",exact=True).click(timeout=5000); log("clicked Ask")
    t0=time.time(); time.sleep(5)
    while time.time()-t0<maxs:
        b=page.get_by_role("button",name="Ask",exact=True)
        if b.is_enabled(): break
        time.sleep(3)
    log("done after %ds"%(time.time()-t0))
def convo():
    t=page.inner_text("body"); i=t.find("Welcome."); 
    return t[i:] if i>=0 else t[-3000:]
ask_wait()
print(convo()[:3500])
shot(page, folder, "q1")
