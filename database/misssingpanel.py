

import json
from collections import Counter

with open(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\panelapp_aus_processednew.json",
    "r",
    encoding="utf-8"
) as f:
    panels = json.load(f)

names = [panel["panel_name"] for panel in panels]

duplicates = [
    name for name, count in Counter(names).items()
    if count > 1
]

print("Duplicate panel names:")
for d in duplicates:
    print(d)


import json

json_file = r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\panelapp_aus_processednew.json"

with open(json_file, "r", encoding="utf-8") as f:
    panels = json.load(f)

print("Total objects:", len(panels))

for i, panel in enumerate(panels):
    if not panel.get("panel_name"):
        print("Missing panel name at index:", i, panel)


from pathlib import Path

raw_folder = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\detailled_panel_aus"
)

files = list(raw_folder.glob("panel_aus_*.json"))

print("Raw panel files:", len(files))