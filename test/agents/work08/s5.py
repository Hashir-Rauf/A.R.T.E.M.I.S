import sys,time,os; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
from pathlib import Path
def log(m):
    l=f"[{time.strftime('%H:%M:%S')}] {m}"; print(l.encode("ascii","replace").decode()); open("actions.log","a",encoding="utf-8").write(l+"\n")
app = App("ua-08", 7948).start()
cf = Path(WORK)/"ua-08"/"clients"
def txt(page): return page.inner_text("body")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(3)
    try: page.get_by_role("tab",name="Folders").click(); log("Folders tab now: "+txt(page)[txt(page).find("Folders ARTEMIS"):][:700])
    except Exception as e: log("err "+str(e)[:100])
    page.get_by_role("tab",name="Work").click(); time.sleep(1)
    def ask(q, wait=40):
        before=txt(page)
        box=page.get_by_placeholder("Tidy up this folder")
        box.fill(q); log("ASK: "+q)
        page.get_by_role("button",name="Ask",exact=True).click()
        t0=time.time(); last=""; 
        while time.time()-t0<wait:
            time.sleep(4); cur=txt(page)
            if cur!=before and cur==last: break
            last=cur
        i=cur.find(q); log("SAW: "+cur[i:i+1800] if i>=0 else "SAW: "+cur[-1500:])
    def newlines(before,cur):
        bs=set(before.split(chr(10))); return chr(10).join(l for l in cur.split(chr(10)) if l not in bs)
    def ask(q, wait=60):
        before=txt(page)
        page.get_by_placeholder("Tidy up this folder").fill(q); log("ASK: "+q)
        page.get_by_role("button",name="Ask",exact=True).click()
        time.sleep(10); t0=time.time(); last=""
        while time.time()-t0<wait:
            time.sleep(5); cur=txt(page)
            if cur==last: break
            last=cur
        log("SAW NEW: "+newlines(before,cur)[:1500])
    def click(name):
        before=txt(page); page.get_by_role("button",name=name,exact=True).click(); time.sleep(12)
        log("CLICK "+name+" -> "+newlines(before,txt(page))[:1500])
    click("No, leave it")
    ask("cancel")
    ask("What does the Northwind NDA say about sharing material with third parties?")
    ask("Which invoices are unpaid and how much is owed in total?")
    ask("Summarise what is left on my todo list.")
    for t in ["What it knows","Settings"]:
        page.get_by_role("tab",name=t).click(); time.sleep(3); log("TAB "+t+": "+txt(page)[:3000])
    shot(page, cf, "08_chat")
    browser.close()
app.stop()
