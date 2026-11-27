import requests
import time 
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urljoin
from urllib.parse import urlparse
import pandas as pd
from io import BytesIO
import csv
from io import StringIO
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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


def get_panel_detailstodelete(base_url, panel_id):

    url = f"{base_url}{panel_id}/"

    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def get_panel_details(base_url, panel_id):
    url = f"{base_url}{panel_id}/"

    for attempt in range(3):
        time.sleep(1)  # Space out detail requests.

        response = requests.get(url, timeout=30)

        if response.status_code == 429 and attempt < 2:
            retry_after = response.headers.get("Retry-After")

            wait_seconds = (
                int(retry_after)
                if retry_after and retry_after.isdigit()
                else 30 * (attempt + 1)
            )

            print(
                f"PanelApp rate limit for panel {panel_id}. "
                f"Waiting {wait_seconds} seconds..."
            )
            time.sleep(wait_seconds)
            continue

        response.raise_for_status()
        return response.json()







def acquire_panelapp_aus():

    base_url = "https://panelapp-aus.org/api/v1/panels/"

    panels = get_panel(base_url)

    detailed_panels = []

    for panel in panels:

        panel_id = panel.get("id")

        detailed_panel = get_panel_details(base_url,panel_id)

        detailed_panels.append(detailed_panel)

    return detailed_panels

def acquire_panelapp_uk():
    base_url = "https://panelapp.genomicsengland.co.uk/api/v1/panels/"
    
    panels = get_panel(base_url)
    detailed_panels = []
    
    for panel in panels:
    
         panel_id = panel.get("id")

         detailed_panel = get_panel_details(base_url,panel_id)
    
         detailed_panels.append(detailed_panel)
    
    return detailed_panels


def acquire_blueprint():


    main_url = "https://www.blueprintgenetics.com/tests/panels/"

    # --------------------------------------------------
    # 1. Get the main Blueprint panels page
    # --------------------------------------------------

    response = requests.get(
        main_url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # --------------------------------------------------
    # 2. Find the "Explore all medical specialities"
    #    section
    # --------------------------------------------------

    accordion = soup.find(
        "div",
        id="test-specializations-accordion"
    )

    if accordion is None:
        print("Blueprint specialities section not found")
        return []

    # --------------------------------------------------
    # 3. Find all categories and their panel URLs
    # --------------------------------------------------

    panels = []

    category_sections = accordion.find_all(
        "div",
        class_="collapse-section"
    )

    for section in category_sections:

        # Find category name
        category_link = section.find(
            "a",
            class_="toggle-collapse"
        )

        if not category_link:
            continue

        category = category_link.get_text(
            strip=True
        )

        # Find all links inside this category
        panel_links = section.find_all(
            "a",
            href=True
        )

        for link in panel_links:

            url = link["href"]

            # Only keep Blueprint panel URLs
            if (
                "/tests/panels/" not in url
                and "/tests/screening/" not in url
            ):
                continue

            # Extract panel name
            title = link.find(
                "div",
                class_="test-list-title"
            )

            if title:
                name = title.get_text(
                    strip=True
                )
            else:
                name = link.get_text(
                    strip=True
                )

            panels.append({
                "category": category,
                "name": name,
                "url": url
            })

    # --------------------------------------------------
    # 4. Remove duplicate panel URLs
    # --------------------------------------------------

    unique_panels = {
        panel["url"]: panel
        for panel in panels
    }

    panels = list(unique_panels.values())

    print(
        f"Found {len(panels)} Blueprint panel URLs"
    )

    # --------------------------------------------------
    # 5. Scrape the data from every panel URL
    # --------------------------------------------------

    results = []

    for panel_info in panels:

        url = panel_info["url"]

        path = urlparse(url).path
        parts = path.strip("/").split("/")

        # /tests/panels/dermatology/panel-name/
        #                ↑ index 2
        category_slug = parts[2]

        category = category_slug.replace("-", " ").title()

        print("Scraping:", url)

        panel_response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        panel_response.raise_for_status()

        panel_soup = BeautifulSoup(
            panel_response.text,
            "html.parser"
        )

        # --------------------------------------------------
        # Panel metadata
        # --------------------------------------------------

        title = panel_soup.find("h1")

        if title:
            panel_name = title.get_text(
                strip=True
            )
        else:
            panel_name = None

        if panel_name is None:
            print(
                "No panel name found, skipping"
            )
            continue

        # --------------------------------------------------
        # Content last modified
        # --------------------------------------------------

        content_last_modified = None

        for div in panel_soup.find_all("div"):

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

        # --------------------------------------------------
        # Find Panel Content table
        # --------------------------------------------------

        header = panel_soup.find(
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

        # --------------------------------------------------
        # Build final panel result
        # --------------------------------------------------

        result = {

            "panel_name": panel_name,

            "source": "Blueprint Genetics",

            "category": category,

            "url": url,

            "content_last_modified":
                content_last_modified,

            "genes": genes
        }

        results.append(result)

    # --------------------------------------------------
    # 6. Return all currently acquired Blueprint data
    # --------------------------------------------------

    return results

def acquire_ontario():
    main_url = "https://www.ontariohealth.ca/clinical/genetics/test-directory"

    response = requests.get(
        main_url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Get all disease/panel URLs
    diseases = []

    articles = soup.find_all("article")

    for article in articles:

        title = article.find("h3")
        name = title.get_text(strip=True) if title else None

        link = article.find("a", href=True)
        url = urljoin(main_url, link["href"]) if link else None

        category = None

        category_div = article.find(
            "div",
            class_="cmp-contentfragment__element--category"
        )

        if category_div:
            tag = category_div.find(
                "span",
                class_="tag-item"
            )

            if tag:
                category = tag.get_text(strip=True)

        diseases.append({
            "name": name,
            "category": category,
            "url": url
        })

    # Scrape the details of every disease/panel
    results = []

    for disease in diseases:

        url = disease["url"]

        if not url:
            continue

        print("Scraping:", url)


        for attempt in range(1, 4):
            try:
                detail_response = requests.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=60
                )

                detail_response.raise_for_status()
                break

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout
            ) as error:
                print(
                    f"Attempt {attempt}/3 failed for {url}: "
                    f"{error}"
                )

                if attempt == 3:
                    raise

                time.sleep(5)



        detail_soup = BeautifulSoup(
            detail_response.text,
            "html.parser"
        )

        data = {
            "source": "Ontario Health",
            "url": url
        }

        elements = detail_soup.find_all(["dt", "dd"])

        for i in range(0, len(elements) - 1, 2):

            key = elements[i].get_text(strip=True)

            value = elements[i + 1].get_text(
                separator=" ",
                strip=True
            )

            data[key] = value

        # Last Updated
        last_updated = None

        for p in detail_soup.find_all("p"):

            text = p.get_text(strip=True)

            if "Last Updated" in text:
                last_updated = text.replace(
                    "Last Updated:",
                    ""
                ).strip()

                break

        result = {
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

        results.append(result)

        time.sleep(2)

    return results

def acquire_clingen():

    downloads_url = "https://search.clinicalgenome.org/kb/downloads"

    response = requests.get(downloads_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    link = soup.find(
        "a",
        href="https://search.clinicalgenome.org/kb/gene-validity/download"
    )

    if not link:
        raise RuntimeError("ClinicalGenom Gene-Disease Validity CSV link not found")

    csv_url = link["href"]

    csv_response = requests.get(csv_url)
    csv_response.raise_for_status()

    # Read CSV directly into a DataFrame
    df = pd.read_csv(
    BytesIO(csv_response.content),
    header=4,
    skiprows=[5]
    )

    return df

def acquire_gencc():

    url = "https://thegencc.org/download/action/submissions-export-tsv?format=new"

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    df = pd.read_csv(
        BytesIO(response.content),
        sep="\t"
    )

    return df













ORPHADATA_BASE_URL = "https://api.orphadata.com"
ORPHANET_EPIDEMIOLOGY_PATH = "/rd-epidemiology/orphacodes"
ORPHANET_NATURAL_HISTORY_PATH = "/rd-natural_history/orphacodes"


def _fetch_orphadata(session, path, *, allow_missing=False):
    response = session.get(
        f"{ORPHADATA_BASE_URL}{path}",
        params={"lang": "en"},
        timeout=(10, 60),
    )

    if allow_missing and response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def acquire_orphanet(limit=None):
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("limit must be a positive integer.")
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={"GET"},
        respect_retry_after_header=True,
    )

    with requests.Session() as session:
        session.mount(
            f"{ORPHADATA_BASE_URL}/",
            HTTPAdapter(max_retries=retries),
        )

        response = _fetch_orphadata(session, ORPHANET_EPIDEMIOLOGY_PATH)
        listing = response["data"]
        diseases = listing["results"]

        if not isinstance(diseases, list) or not diseases:
            raise ValueError("Orphadata returned an empty or invalid disease list.")

        if listing["__count"] != len(diseases):
            raise ValueError(
                f"Incomplete Orphadata list: expected {listing['__count']} "
                f"entries, received {len(diseases)}."
            )

        codes = [disease["ORPHAcode"] for disease in diseases]
        if any(type(code) is not int or code <= 0 for code in codes):
            raise ValueError("Orphadata returned an invalid ORPHAcode.")
        if len(set(codes)) != len(codes):
            raise ValueError("Orphadata returned duplicate ORPHAcodes.")


        if limit is not None:
         diseases = diseases[:limit]
        

        
        print(f"Fetching details for {len(diseases)} Orphanet entries.")
        records = []

        for index, disease in enumerate(diseases, start=1):
            code = disease["ORPHAcode"]

            epidemiology = _fetch_orphadata(
                session,
                f"{ORPHANET_EPIDEMIOLOGY_PATH}/{code}",
            )
            natural_history = _fetch_orphadata(
                session,
                f"{ORPHANET_NATURAL_HISTORY_PATH}/{code}",
                allow_missing=True,
            )

            for dataset, detail in (
                ("epidemiology", epidemiology),
                ("natural history", natural_history),
            ):
                if detail is not None and detail["data"]["results"]["ORPHAcode"] != code:
                    raise ValueError(
                        f"Unexpected ORPHAcode in {dataset} response for ORPHA:{code}."
                    )

            records.append({
                "orpha_code": code,
                "source": "Orphanet",
                "disease_list_entry": disease,
                "epidemiology": epidemiology,
                "natural_history": natural_history,
            })

            if index % 100 == 0 or index == len(diseases):
                print(f"Orphanet acquisition: {index}/{len(diseases)}", flush=True)

    return records










#uk_data = acquire_panelapp_uk()
#aus_data = acquire_panelapp_aus()
#ontario_data = acquire_ontario()
#blueprint_data = acquire_blueprint()
#clingen_data = acquire_clingen()
#gencc_data = acquire_gencc()


#processing genes of panel uk and aus only
def process_gene(gene):

    gene_data = gene.get("gene_data", {})
    origin_panel = gene.get("panel") or {}

    return {
        "gene_symbol": gene_data.get("gene_symbol"),
        "confidence_level": gene.get("confidence_level"),
        "phenotypes": gene.get("phenotypes", []),
        "origin_panel_id": origin_panel.get("id")
    }

#processing strs of panel uk and aus only 
def process_str(str_entity):

    gene_data = str_entity.get("gene_data", {})
    origin_panel = str_entity.get("panel") or {}

    return {
        "entity_name": str_entity.get("entity_name"),
        "gene_symbol": gene_data.get("gene_symbol"),
        "origin_panel_id": origin_panel.get("id"),
        "confidence_level": str_entity.get("confidence_level"),
        "phenotypes": str_entity.get("phenotypes", []),
        "repeated_sequence": str_entity.get("repeated_sequence")
    }

#processing panelapp uk and aus 
def process_panel(panel, source):
    
    processed_panel = {

        "source_panel_id": panel.get("id"),
        "child_panel_ids": panel.get("child_panel_ids"),
        "panel_name": panel.get("name"),
        "disease_group": panel.get("disease_group"),
        "disease_subgroup": panel.get("disease_sub_group"),
        "relevant_diseases": panel.get("relevant_disorders", []),

        "source": source,

        "version": panel.get("version"),
        "last_updated": None,

        "processed_date": datetime.today().strftime("%Y-%m-%d"),

        "genes": [],
        "strs": []
    }

    # Genes
    for gene in panel.get("genes", []):

        if gene.get("entity_type") == "gene":

            processed_panel["genes"].append(
                process_gene(gene)
            )

    # STRs
    for str_entity in panel.get("strs", []):

        if str_entity.get("entity_type") == "str":

            processed_panel["strs"].append(
                process_str(str_entity)
            )

    return processed_panel

def normalize_panelapp_aus(panels):

    normalized_panels = []

    for panel in panels:

        normalized_panels.append(
            process_panel(panel, "PanelApp AUS")
        )

    return normalized_panels

def normalize_panelapp_uk(panels):
    
    normalized_panels = []

    for panel in panels:

        normalized_panels.append(
            process_panel(panel, "PanelApp UK")
        )

    return normalized_panels



def process_blueprint_gene(gene):

    phenotypes = gene.get("phenotypes")

    if phenotypes:
        phenotypes = [
            p.strip()
            for p in phenotypes.split(",")
            if p.strip()
        ]
    else:
        phenotypes = None

    return {
        "gene_symbol": (gene.get("gene_symbol") or "").strip().rstrip("*#"),
        "confidence_level": "3",
        "phenotypes": phenotypes
    }


def normalize_blueprint_date(value):
    if not value:
        return None

    value = value.strip()

    for date_format in ("%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format).strftime("%Y-%m-%d")
        except ValueError:
            pass

    raise ValueError(f"Unrecognized Blueprint date: {value}")






def process_blueprint_panel(panel):

    return {
        "panel_id": None,

        "panel_name": panel.get("panel_name"),

        "disease_group": panel.get("category"),

        "disease_subgroup": None,

        "relevant_diseases": None,

        "source": panel.get("source"),

        "version": None,

        "last_updated": normalize_blueprint_date(panel.get("content_last_modified")),

        "processed_date": datetime.today().strftime("%Y-%m-%d"),

        "genes": [
            process_blueprint_gene(gene)
            for gene in panel.get("genes", [])
        ],

        "strs": []
    }

def normalize_blueprint(panels):

    normalized_panels = []

    for panel in panels:

        normalized_panels.append(
            process_blueprint_panel(panel)
        )

    return normalized_panels



def process_genes_ontario(gene_string):
    if not gene_string:
        return []

    entries = []
    current = ""
    depth = 0

    for char in gene_string:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1

        if char in ",;" and depth == 0:
            entries.append(current.strip())
            current = ""
        else:
            current += char

    entries.append(current.strip())

    genes = []
    seen = set()

    for entry in entries:
        symbol = entry.strip()
        # Remove a variant description and an allele suffix.
        # symbol = entry.split("(", 1)[0].split("*", 1)[0].strip()

        if symbol and symbol not in seen:
            seen.add(symbol)
            genes.append({
                "gene_symbol": symbol,
                "confidence_level": "3",
                "phenotypes": None,
            })

    return genes




def process_genes_ontariotodelete(gene_string):

    if not gene_string:
        return []

    genes = []

    for gene in gene_string.split(","):

        gene = gene.strip()

        if gene:
            genes.append({
                "gene_symbol": gene,
                "confidence_level": None,
                "phenotypes": None
            })

    return genes







def process_ontario_record(record):


    url = record.get("url") or ""
    query_parameters = parse_qs(urlparse(url).query)
    ontario_id = query_parameters.get("cf", [None])[0]

    if not ontario_id:
        raise ValueError(
            f"Ontario record has no cf identifier: {url}"
        )

    last_updated = record.get("last_updated")

    if last_updated:
        last_updated = datetime.strptime(
            last_updated.strip(),
            "%B %d, %Y"
        ).strftime("%Y-%m-%d")
    else:
        last_updated = None

    return {
        "panel_id": None,

        "panel_name": record.get("title"),

        "disease_group": record.get("category"),

        "disease_subgroup": record.get("subcategory"),

        "ontario_id": ontario_id,

        "lab_name": record.get("lab"),

        "relevant_diseases": [
            disease.strip()
            for disease in (record.get("disease_condition") or "").split(",")
            if disease.strip()
        ],

        "source": record.get("source"),

        "version": None,

        "last_updated": last_updated,

        "processed_date": datetime.today().strftime("%Y-%m-%d"),

        "genes": process_genes_ontario(
            record.get("gene_platform_region")
        ),

        "strs": []
    }

def normalize_ontario(records):

    normalized_records = []

    for record in records:

        normalized_records.append(
            process_ontario_record(record)
        )

    return normalized_records


def normalize_gencc(df):

    normalized_data = []

    for _, record in df.iterrows():

        normalized_data.append({

            "panel_id": None,

            "panel_name": record["disease_title"].strip(),

            "disease_group": None,

            "disease_subgroup": None,

            "relevant_diseases": [
                record["disease_title"].strip()
            ],

            "source": "GenCC",

            "version": record["version_number"],

            "last_updated": record["submitted_as_date"].split("T")[0].split(" ")[0],

            "processed_date": datetime.today().strftime("%Y-%m-%d"),

            "genes": [{
                "gene_symbol": record["gene_symbol"].strip(),

                "confidence_level": (
                    record["classification_title"].strip()
                ),

                "phenotypes": None,
                "moi": record["moi_title"].strip(),
                "submitter": record["submitter_title"].strip(),
                "sgc_id": record["sgc_id"].strip(),
            }],

            "strs": []
        })

    return normalized_data

def normalize_clingen(df):

    normalized_data = []

    for _, record in df.iterrows():

        normalized_data.append({

            "panel_id": None,

            "panel_name": record["DISEASE LABEL"].strip(),

            "disease_group": None,

            "disease_subgroup": None,

            "relevant_diseases": [
                record["DISEASE LABEL"].strip()
            ],

            "source": "ClinGen",

            "version": None,

            "last_updated": (
                record["CLASSIFICATION DATE"].split("T")[0]
            ),

            "processed_date": datetime.today().strftime("%Y-%m-%d"),

            "genes": [{
                "gene_symbol": record["GENE SYMBOL"].strip(),

                "confidence_level": (
                    record["CLASSIFICATION"].strip()
                ),

                "phenotypes": None,
                "moi": record["MOI"].strip(),
                "assertion_url":record["ONLINE REPORT"].strip(),

            }],

            "strs": []
        })

    return normalized_data







def normalize_disease(raw):
    epidemiology = raw["epidemiology"]["data"]["results"]
    history_response = raw.get("natural_history")
    natural_history = (
        history_response["data"]["results"] if history_response else {}
    )

    return {
        "orpha_code": raw["orpha_code"],
        "source": raw["source"],
        "orphanet_url": epidemiology.get("OrphanetURL"),
        "disease_name": epidemiology["Preferred term"],
        "epidemiology": epidemiology.get("Prevalence") or [],
        "age_at_onset": natural_history.get("AverageAgeOfOnset") or [],
        "disorder_group": (
            natural_history.get("DisorderGroup")
            or epidemiology.get("DisorderGroup")
        ),
        "inheritance": natural_history.get("TypeOfInheritance") or [],
    }


def normalize_orphanet(raw_records):
    if not isinstance(raw_records, list) or not raw_records:
        raise ValueError("Expected a non-empty list of Orphanet records.")

    return [normalize_disease(raw) for raw in raw_records]






# from acquire_data import acquire_orphanet

# raw_records = acquire_orphanet()
# print("Acquired:", len(raw_records))
# print("First ORPHAcode:", raw_records[0]["orpha_code"])