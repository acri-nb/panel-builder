import requests
from db_SQLAlchemy import SessionLocal
from update.acquire_data import acquire_panelapp_aus ,acquire_panelapp_uk, get_panel,get_panel_details, acquire_gencc ,acquire_clingen
from update.acquire_data import normalize_panelapp_aus,normalize_panelapp_uk,normalize_ontario,normalize_blueprint,normalize_gencc,normalize_clingen
from update.comparison import compare_panel
from bs4 import BeautifulSoup



#test on clingen
db = SessionLocal()

try:

    # 1. Acquire current ClinGen data
    print("Acquiring ClinGen data...")

    df = acquire_clingen()

    print("ClinGen data acquired!")

    print("\nTotal records:", len(df))

    # 2. See available diseases
    print("\nExample disease labels:")
    print(
        df["DISEASE LABEL"]
        .dropna()
        .drop_duplicates()
        .head(20)
        .to_list()
    )

    # 3. Choose ONE disease/panel
    test_panel_name = "Charcot-Marie-Tooth disease axonal type 2N"

    test_df = df[
        df["DISEASE LABEL"].str.strip()
        == test_panel_name
    ]

    if test_df.empty:

        print(
            f"\nDisease not found: "
            f"{test_panel_name}"
        )

    else:

        print(
            f"\nFound {len(test_df)} "
            f"ClinGen records for:"
        )

        print(test_panel_name)

        # 4. Normalize only this disease
        normalized_panels = normalize_clingen(
            test_df
        )

        print("\n==============================")
        print("NORMALIZED CLINGEN DATA")
        print("==============================")

        for panel in normalized_panels:

            print(panel)

            # 5. Compare with database
            result = compare_panel(
                db,
                panel
            )

            print("\n==============================")
            print("COMPARISON RESULT")
            print("==============================")

            print("Status:", result["status"])

            if result["status"] == "new":

                print(
                    "Panel does not exist in database."
                )

            elif result["status"] == "unchanged":

                print("No changes detected.")

            elif result["status"] == "changed":

                print("\nMetadata changes:")
                print(result["metadata_changes"])

                print("\nGene changes:")
                print(result["gene_changes"])

                print("\nSTR changes:")
                print(result["str_changes"])

finally:

    db.close()



#test on gencc
db = SessionLocal()

try:

    # 1. Acquire current GenCC data
    print("Acquiring GenCC data...")

    df = acquire_gencc()

    print("GenCC data acquired!")

    print("\nTotal records:", len(df))

    # 2. Choose ONE disease/panel to test
    test_panel_name = "Shprintzen-Goldberg syndrome"

    test_df = df[
        df["disease_title"].str.strip()
        == test_panel_name
    ]

    if test_df.empty:

        print(
            f"\nPanel/disease not found: "
            f"{test_panel_name}"
        )

    else:

        print(
            f"\nFound {len(test_df)} "
            f"GenCC records for:"
        )

        print(test_panel_name)

        # 3. Normalize only this disease
        normalized_panels = normalize_gencc(
            test_df
        )

        print("\n==============================")
        print("NORMALIZED GENCC DATA")
        print("==============================")

        for panel in normalized_panels:
            print(panel)

            # 4. Compare with database
            result = compare_panel(
                db,
                panel
            )

            print("\n==============================")
            print("COMPARISON RESULT")
            print("==============================")

            print("Status:", result["status"])

            if result["status"] == "new":

                print(
                    "Panel does not exist in database."
                )

            elif result["status"] == "unchanged":

                print("No changes detected.")

            elif result["status"] == "changed":

                print("\nMetadata changes:")
                print(result["metadata_changes"])

                print("\nGene changes:")
                print(result["gene_changes"])

                print("\nSTR changes:")
                print(result["str_changes"])

finally:

    db.close()




#test on blueprint genetics 
db = SessionLocal()

try:

    # 1. Blueprint panel to test
    url = "https://www.blueprintgenetics.com/tests/panels/neurology/collagen-type-vi-related-disorders-panel/"

    category = "Neurology"

    print("Scraping Blueprint panel:")
    print(url)

    # 2. Request panel page
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    print("Panel page acquired!")

    # 3. Parse page
    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # 4. Panel name
    title = soup.find("h1")

    if title:
        panel_name = title.get_text(strip=True)
    else:
        panel_name = None

    # 5. Content last modified
    content_last_modified = None

    for div in soup.find_all("div"):

        text = div.get_text(
            separator=" ",
            strip=True
        )

        if text.startswith(
            "Content last modified:"
        ):

            content_last_modified = text.replace(
                "Content last modified:",
                ""
            ).strip()

            break

    # 6. Find Panel Content table
    header = soup.find(
        lambda tag:
        tag.name in ["h1", "h2", "h3", "h4"]
        and "Panel Content" in tag.get_text(
            strip=True
        )
    )

    genes = []

    if header:

        table = header.find_next("table")

        if table:

            tbody = table.find("tbody")

            if tbody:

                rows = tbody.find_all("tr")

                for row in rows:

                    columns = row.find_all("td")

                    if len(columns) < 5:
                        continue

                    gene = {
                        "gene_symbol":
                            columns[0].get_text(
                                strip=True
                            ),

                        "phenotypes":
                            columns[1].get_text(
                                separator=", ",
                                strip=True
                            ),

                        "inheritance":
                            columns[2].get_text(
                                strip=True
                            ),

                        "clinvar":
                            columns[3].get_text(
                                strip=True
                            ),

                        "hgmd":
                            columns[4].get_text(
                                strip=True
                            )
                    }

                    genes.append(gene)

    # 7. Build raw Blueprint record
    panel = {
        "panel_name": panel_name,
        "source": "Blueprint Genetics",
        "category": category,
        "url": url,
        "content_last_modified":
            content_last_modified,
        "genes": genes
    }

    print("\n==============================")
    print("SCRAPED BLUEPRINT PANEL")
    print("==============================")

    print(panel)

    # 8. Normalize
    normalized_panels = normalize_blueprint(
        [panel]
    )

    normalized_panel = normalized_panels[0]

    print("\n==============================")
    print("NORMALIZED PANEL")
    print("==============================")

    print(normalized_panel)

    # 9. Compare with database
    result = compare_panel(
        db,
        normalized_panel
    )

    # 10. Print comparison result
    print("\n==============================")
    print("COMPARISON RESULT")
    print("==============================")

    print("Status:", result["status"])

    if result["status"] == "new":

        print("Panel does not exist in database.")

    elif result["status"] == "unchanged":

        print("No changes detected.")

    elif result["status"] == "changed":

        print("\nMetadata changes:")
        print(result["metadata_changes"])

        print("\nGene changes:")
        print(result["gene_changes"])

        print("\nSTR changes:")
        print(result["str_changes"])

finally:

    db.close()







#test on ontario 
db = SessionLocal()

try:

    # 1. Specific Ontario panel to test
    url = (
        "https://www.ontariohealth.ca/"
        "clinical/genetics/test-directory/"
        "genetic-test-details?cf=9000"
    )

    print("Scraping Ontario panel:")
    print(url)

    # 2. Request the panel page
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    print("Panel page acquired!")

    # 3. Parse page
    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # 4. Extract data
    data = {
        "source": "Ontario Health",
        "url": url
    }

    elements = soup.find_all(["dt", "dd"])

    for i in range(0, len(elements) - 1, 2):

        key = elements[i].get_text(strip=True)

        value = elements[i + 1].get_text(
            separator=" ",
            strip=True
        )

        data[key] = value

    # 5. Extract Last Updated
    last_updated = None

    for p in soup.find_all("p"):

        text = p.get_text(strip=True)

        if "Last Updated" in text:

            last_updated = text.replace(
                "Last Updated:",
                ""
            ).strip()

            break

    # 6. Build the same raw record produced by acquire_ontario()
    record = {
        "source": data.get("source"),
        "url": data.get("url"),
        "title": data.get("Title"),
        "lab": data.get("Lab"),
        "category": data.get("Category"),
        "subcategory": data.get("Sub Category"),
        "gene_platform_region": data.get(
            "Gene/Platform/Region List"
        ),
        "disease_condition": data.get(
            "Disease/Condition"
        ),
        "last_updated": last_updated
    }

    print("\n==============================")
    print("SCRAPED ONTARIO RECORD")
    print("==============================")

    print(record)

    # 7. Normalize
    normalized_records = normalize_ontario(
        [record]
    )

    normalized_panel = normalized_records[0]

    print("\n==============================")
    print("NORMALIZED PANEL")
    print("==============================")

    print(normalized_panel)

    # 8. Compare with database
    result = compare_panel(
        db,
        normalized_panel
    )

    # 9. Print comparison result
    print("\n==============================")
    print("COMPARISON RESULT")
    print("==============================")

    print("Status:", result["status"])

    if result["status"] == "new":

        print("Panel does not exist in database.")

    elif result["status"] == "unchanged":

        print("No changes detected.")

    elif result["status"] == "changed":

        print("\nMetadata changes:")
        print(result["metadata_changes"])

        print("\nGene changes:")
        print(result["gene_changes"])

        print("\nSTR changes:")
        print(result["str_changes"])

finally:

    db.close()






#test on panel uk
db = SessionLocal()

try:

    # 1. Get the list of PanelApp UK panels
    base_url = "https://panelapp.genomicsengland.co.uk/api/v1/panels/"

    panels = get_panel(base_url)

    # 2. Find the specific panel
    test_panel = None

    for panel in panels:
        if panel.get("name") == "Unexplained young onset end-stage renal disease - additional genes":
            test_panel = panel
            break

    if not test_panel:

        print("Mendeliome panel not found in PanelApp UK data.")

    else:

        print("Mendeliome panel found!")
        print("Panel ID:", test_panel.get("id"))

        # 3. Get details ONLY for this panel
        panel_id = test_panel.get("id")

        detailed_panel = get_panel_details(
            base_url,
            panel_id
        )

        print("\nDetailed panel acquired!")

        # 4. Normalize only this panel
        normalized_panels = normalize_panelapp_uk(
            [detailed_panel]
        )

        normalized_panel = normalized_panels[0]

        print("\nNormalized panel:")
        print(normalized_panel)

        # 5. Compare with database
        result = compare_panel(
            db,
            normalized_panel
        )

        # 6. Print comparison result
        print("\n==============================")
        print("COMPARISON RESULT")
        print("==============================")

        print("Status:", result["status"])

        if result["status"] == "new":

            print("Panel does not exist in database.")

        elif result["status"] == "unchanged":

            print("No changes detected.")

        elif result["status"] == "changed":

            print("\nMetadata changes:")
            print(result["metadata_changes"])

            print("\nGene changes:")
            print(result["gene_changes"])

            print("\nSTR changes:")
            print(result["str_changes"])

finally:

    db.close()




#test on panel aus
db = SessionLocal()

try:

    # 1. Acquire PanelApp AUS data
    panels = acquire_panelapp_aus()

    # 2. Find Cerebral Palsy
    test_panel = None

    for panel in panels:
        if panel.get("name") == "Mendeliome":
            test_panel = panel
            break

    if not test_panel:
        print("Mendeliome panel not found in PanelApp AUS data.")

    else:

        print("Mendeliome panel acquired!")

        # 3. Normalize only this panel
        normalized_panels = normalize_panelapp_aus(
            [test_panel]
        )

        normalized_panel = normalized_panels[0]

        print("\nNormalized panel:")
        print(normalized_panel)

        # 4. Compare with database
        result = compare_panel(
            db,
            normalized_panel
        )

        # 5. Print comparison result
        print("\n==============================")
        print("COMPARISON RESULT")
        print("==============================")

        print("Status:", result["status"])

        if result["status"] == "new":

            print("Panel does not exist in database.")

        elif result["status"] == "unchanged":

            print("No changes detected.")

        elif result["status"] == "changed":

            print("\nMetadata changes:")
            print(result["metadata_changes"])

            print("\nGene changes:")
            print(result["gene_changes"])

            print("\nSTR changes:")
            print(result["str_changes"])

finally:
    db.close()
