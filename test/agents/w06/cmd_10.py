def say(q, maxs=100):
    page.get_by_placeholder("Tidy up this folder").fill(q); log("typed: "+q)
    ask_wait(maxs)
    c=convo(); i=c.find("Type a message first") 
    j=c.find("Clear conversation"); k=c.find("Suggest a tidy-up")
    print(c[k:j+1500][:3500])
say("Look through the app folder and tell me what this project does, and suggest a fix for anything that looks buggy")
shot(page, folder, "q1")
