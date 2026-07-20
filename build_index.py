"""Bake gamedata.json into template.html -> index.html (the deployed site)."""
import json, os
D = os.path.dirname(os.path.abspath(__file__))
t = open(f"{D}/template.html").read()
data = open(f"{D}/gamedata.json").read()
assert "/*__GAMEDATA__*/" in t, "template placeholder missing"
idx = t.replace("/*__GAMEDATA__*/", data)
open(f"{D}/index.html", "w").write(idx)
print(f"index.html baked: {os.path.getsize(f'{D}/index.html')//1024} KB")
