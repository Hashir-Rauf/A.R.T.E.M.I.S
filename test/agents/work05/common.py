import sys; sys.stdout.reconfigure(encoding="utf-8")
import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open("actions.log","a",encoding="utf-8")
def log(m):
    s=f"[{time.strftime('%H:%M:%S')}] {m}"; print(s); LOG.write(s+"\n"); LOG.flush()
def tab(page,n):
    page.get_by_role("tab",name=n).click(); time.sleep(1.5)
def vis(page,n=2500):
    return page.locator("body").inner_text()[:n]
