import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size":8.5,"font.family":"serif","font.serif":["Times New Roman","DejaVu Serif"],"pdf.fonttype":42})
fig,ax=plt.subplots(2,2,figsize=(6.6,5.0))
def bars(a,labels,vals,cols,title,ymax):
    a.bar(labels,vals,color=cols)
    for i,v in enumerate(vals): a.text(i,v+ymax*0.02,str(v),ha="center",fontsize=8.5)
    a.set_title(title,fontsize=9.2); a.set_ylim(0,ymax)
    for s in ("top","right"): a.spines[s].set_visible(False)
bars(ax[0][0],["Critical","High","Medium","Low"],[1,18,37,15],["#8b1a1a","#c0504d","#e0a060","#b8b8b8"],"(a) Distinct defects by severity (71)",44)
bars(ax[0][1],["Pass","Pass with\nissues","Fail"],[0,23,4],["#4f9d69","#6f9fd0","#c0504d"],"(b) Verdicts of the 27 sessions",27)
bars(ax[1][0],["Pass","Partial","Fail","Not\ntested"],[13,20,5,1],["#4f9d69","#e0b44c","#c0504d","#9aa0a6"],"(c) Backlog stories and gates (39)",24)
areas=["Workspace","Trust","Gateway","File feat.","Doc/code","Outward","Speech","Remote","Everyday"]
rep=[13,11,11,15,18,13,9,12,11]
a=ax[1][1]; a.barh(areas[::-1],rep[::-1],color="#6f9fd0")
for i,v in enumerate(rep[::-1]): a.text(v+0.3,i,str(v),va="center",fontsize=8.2)
a.set_title("(d) Defects reported per area (113)",fontsize=9.2); a.set_xlim(0,22)
for s in ("top","right"): a.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("fig_campaign.pdf",bbox_inches="tight"); print("ok")
