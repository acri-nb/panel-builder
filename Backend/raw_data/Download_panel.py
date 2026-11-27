#downloading info 

import requests
import json
from pathlib import Path
from datetime import datetime
import time 

def get_panel(url_panel):

    all_panels = []

    while url_panel:
        response_panel = requests.get(url_panel)
        response_panel.raise_for_status()

        panel = response_panel.json()

        # Add the panels from this page
        all_panels.extend(panel["results"])

        # Go to next page
        url_panel = panel["next"]

    return all_panels

def save_panel(data_panel,source):

    date = datetime.today().strftime("%Y-%m-%d")

    file_path = r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\newpanels_" +source +"_"+ date + ".json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data_panel, file, indent=4)

def extract_panel_ids(panel_data):

    panel_ids = []

    for panel in panel_data:
        panel_ids.append(panel["id"])

    return panel_ids



def get_panel_id(panel_id):

    url_panel_id = f"https://panelapp.genomicsengland.co.uk/api/v1/panels/{panel_id}/"
    while True:

        response = requests.get(url_panel_id)

        print(f"Panel {panel_id} -> Status code: {response.status_code}")

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 429:
            print("Rate limit reached. Waiting...")
            time.sleep(10)

        else:
            print(response.text)
            return None
        
def get_panel_aus_id(panel_id):

    url_panel_aus_id = f"https://panelapp-aus.org/api/v1/panels/{panel_id}/"
    while True:

        response = requests.get(url_panel_aus_id)

        print(f"Panel {panel_id} -> Status code: {response.status_code}")

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 429:
            print("Rate limit reached. Waiting...")
            time.sleep(10)

        else:
            print(response.text)
            return None



def save_panel_id(data_panel_id,source ,id):
    
    file_path = r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\new_detailled_panel_" + source + "\panel_" + source +"_" +str(id) + ".json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data_panel_id, file, indent=4)


#saving england data
# url = "https://panelapp.genomicsengland.co.uk/api/v1/panels/"
# panels = get_panel(url)
# save_panel(panels,"uk")
# print(len(panels))

# panel_ids = extract_panel_ids(panels)
# print(len(panel_ids))

# print(panel_ids)

# for id in panel_ids:
#   data_panel_id= get_panel_id(id)
  
#   if data_panel_id is not None:
#    save_panel_id(data_panel_id,"uk", id)


#saving aus data
url_aus ="https://panelapp-aus.org/api/v1/panels/"
panels_aus = get_panel(url_aus)
save_panel(panels_aus,"aus")
print (len(panels_aus))

panel_aus_ids = extract_panel_ids(panels_aus)
print(len(panel_aus_ids))
print(panel_aus_ids)

for id in panel_aus_ids:
  data_panel_aus_id= get_panel_aus_id(id)
  
  if data_panel_aus_id is not None:
   save_panel_id(data_panel_aus_id, "aus", id)


