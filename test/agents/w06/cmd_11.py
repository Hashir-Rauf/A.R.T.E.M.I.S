print(os.listdir(folder), [os.listdir(os.path.join(folder,d)) for d in os.listdir(folder) if os.path.isdir(os.path.join(folder,d))])
say("What files are in this folder and what does the README say?")
say("Is there a bug in the code? Show me a fix.")
