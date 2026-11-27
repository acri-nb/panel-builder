import requests
import json
from pathlib import Path
import time
from datetime import datetime


# ==========================
# Configuration
# ==========================

BASE_URLS = {
    "uk": "https://panelapp.genomicsengland.co.uk/api/v1",
    "aus": "https://panelapp-aus.org/api/v1"
}


RAW_FOLDER = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data"
)


# ==========================
# Get all panels
# ==========================

def get_all_panels(source):

    url = f"{BASE_URLS[source]}/panels/"

    all_panels = []

    while url:

        response = requests.get(url)

        print(f"{source} panels -> {response.status_code}")

        response.raise_for_status()

        data = response.json()

        all_panels.extend(data["results"])

        url = data["next"]

    return all_panels



# ==========================
# Extract panel IDs
# ==========================

def extract_panel_ids(panels):

    return [
        panel["id"]
        for panel in panels
    ]



# ==========================
# Get STRs for one panel
# ==========================

def get_panel_strs(source, panel_id):

    url = (
        f"{BASE_URLS[source]}"
        f"/panels/{panel_id}/strs/"
    )


    while True:

        response = requests.get(url)

        print(
            f"{source} panel {panel_id} STRs -> {response.status_code}"
        )


        if response.status_code == 200:

            all_strs = []

            data = response.json()

            all_strs.extend(data["results"])


            # Handle pagination
            next_url = data["next"]

            while next_url:

                response_next = requests.get(next_url)

                response_next.raise_for_status()

                data_next = response_next.json()

                all_strs.extend(data_next["results"])

                next_url = data_next["next"]


            return all_strs


        elif response.status_code == 429:

            print("Rate limit reached, waiting...")
            time.sleep(10)


        else:

            print(response.text)
            return None



# ==========================
# Save STR raw data
# ==========================

def save_str_data(source, panel_id, data):

    folder = RAW_FOLDER / f"panelapp_{source}_strs"

    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    file_path = folder / f"panel_{panel_id}_strs.json"


    with open(file_path, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            indent=4
        )



# ==========================
# Main extraction
# ==========================

for source in ["uk", "aus"]:


    print("\n======================")
    print(f"Downloading {source} STRs")
    print("======================\n")


    panels = get_all_panels(source)

    panel_ids = extract_panel_ids(panels)


    print(
        f"{source}: {len(panel_ids)} panels found"
    )


    for panel_id in panel_ids:


        strs = get_panel_strs(
            source,
            panel_id
        )


        if strs is not None:

            save_str_data(
                source,
                panel_id,
                strs
            )


        # small delay to avoid rate limits
        time.sleep(1)



print("Finished extracting STR data")