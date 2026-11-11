import sys,time,os; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
L=open("actions.log","a",encoding="utf-8"); sys.stdout.reconfigure(encoding="utf-8")
def log(m):
    s=f"[{time.strftime('%H:%M:%S')}] {m}"; print(s); L.write(s+"\n"); L.flush()
def vis(page):
    return page.evaluate("""()=>{const o=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){const e=n.parentElement;if(!e)continue;const r=e.getBoundingClientRect();const cs=getComputedStyle(e);if(r.width>0&&r.height>0&&cs.visibility!='hidden'&&n.textContent.trim())o.push(n.textContent.trim())}return o.join(' | ')}""")
def tab(page,name):
    page.get_by_role("tab",name=name).first.click(); page.wait_for_timeout(1500)
