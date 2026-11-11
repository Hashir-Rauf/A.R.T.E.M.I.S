import sys,time,os; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
def log(m):
    l=f"[{time.strftime('%H:%M:%S')}] {m}"; print(l.encode("ascii","replace").decode()); open("actions.log","a",encoding="utf-8").write(l+"\n")
app = App("ua-08", 7948).start()
from pathlib import Path
cf = Path(WORK)/"ua-08"/"clients"; cf.mkdir(parents=True,exist_ok=True)
files={
"Brightleaf_brief_v1.txt":"Brightleaf Bakery rebrand brief. Deliverables: logo, 3 packaging labels, tagline. Deadline 14 Dec. Budget 1200. Confidential.",
"Brightleaf_brief_v2_FINAL.txt":"Brightleaf Bakery rebrand brief v2. Client wants warmer colours, deadline moved to 20 Dec. Budget 1400. Confidential.",
"Brightleaf_brief_v2_FINAL_final.txt":"Brightleaf v2 final-final: add menu card design. Deadline 20 Dec. Budget 1500.",
"NDA_Northwind.txt":"Mutual NDA with Northwind Ltd. Designer must not share any client materials with third parties or upload to third-party services. Term 3 years.",
"Invoice_0042_Northwind.txt":"Invoice 0042 to Northwind Ltd. Amount 850. Due 30 Nov. Status: unpaid.",
"Invoice_0043_Brightleaf.txt":"Invoice 0043 to Brightleaf Bakery. Amount 600 deposit. Due 1 Dec. Status: paid.",
"copy_draft_homepage_v3.txt":"Northwind homepage copy draft 3: We build tools that quietly work. Needs tighter headline.",
"todo.md":"- chase Northwind invoice 0042\n- send Brightleaf mockups\n- renew Canva",
}
for k,v in files.items(): (cf/k).write_text(v,encoding="utf-8")
log(f"made client folder {cf} with {list(files)}")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(3)
    page.get_by_role("tab",name="Folders").click()
    log("clicked Folders tab")
    page.get_by_label("Folder to add").fill(str(cf)); log("typed folder path")
    page.get_by_role("button",name="Add folder").click(); time.sleep(4)
    log("added folder; Folders tab shows: "+page.inner_text("body")[:900])
    shot(page, cf, "08_folders")
    page.get_by_role("tab",name="Work").click(); time.sleep(1)
    log("Work tab: "+page.inner_text("body")[:1500])
    for el in page.query_selector_all("textarea,input,button"):
        try: log("ctrl "+el.evaluate("e=>e.tagName+'|'+(e.placeholder||'')+'|'+(e.innerText||'').slice(0,40)+'|'+(e.type||'')"))
        except: pass
    browser.close()
app.stop()
