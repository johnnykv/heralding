import os
import glob

# Detect all modules
for fullname in glob.glob(os.path.dirname(__file__) + "/*.py"):
    name = os.path.basename(fullname)
    # __init__ and handlerbase are not capabilities, so ignore them 
    if name[:-3] == "__init__" or name[:-3] == "handlerbase":
        pass
    else:
        __import__("beeswarm.drones.honeypot.capabilities." + name[:-3])
