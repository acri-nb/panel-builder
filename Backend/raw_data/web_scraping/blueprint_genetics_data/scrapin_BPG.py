import requests
from bs4 import BeautifulSoup
import json
import os

#sraping_Blue_print from urls *add content last modified *

class BlueprintScraper:

    def __init__(self, url, category):
        self.url = url
        self.category = category
        self.soup = None


    def download_page(self):
        """
        Download the HTML page.
        """

        response = requests.get(
            self.url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        return response.text



    def parse_page(self):
        """
        Convert HTML into BeautifulSoup.
        """

        html = self.download_page()

        self.soup = BeautifulSoup(
            html,
            "html.parser"
        )



    def extract_panel_info(self):
        """
        Extract general panel information.
        """

        panel = {}

        title = self.soup.find("h1")

        if title:
            panel["panel_name"] = title.get_text(
                strip=True
            )
        else:
            panel["panel_name"] = None


        panel["source"] = "Blueprint Genetics"

        panel["category"] = self.category

        panel["url"] = self.url

        panel["content_last_modified"] = self.extract_last_modified()


        return panel

    
    def extract_last_modified(self):
        """
        Extract the 'Content last modified' date.
        """

        for div in self.soup.find_all("div"):

            text = div.get_text(
                separator=" ",
                strip=True
            )

            if text.startswith("Content last modified:"):

                return text.replace(
                    "Content last modified:",
                    ""
                ).strip()

        return None



    def find_panel_content_table(self):
        """
        Find the table located under 'Panel Content'.
        """

        header = self.soup.find(
            lambda tag:
            tag.name in ["h1", "h2", "h3", "h4"]
            and "Panel Content" in tag.get_text(strip=True)
        )


        if not header:
            print("Panel Content header not found")
            return None



        table = header.find_next("table")


        if not table:
            print("No table found after Panel Content")
            return None


        return table




    def extract_gene_table(self):
        """
        Extract genes from Panel Content table.
        """

        genes = []


        table = self.find_panel_content_table()


        if table is None:
            return genes



        tbody = table.find("tbody")


        if not tbody:
            print("No tbody found")
            return genes



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



        return genes




    def scrape(self):

        self.parse_page()


        panel = self.extract_panel_info()


        panel["genes"] = self.extract_gene_table()


        return panel





def save_json(data, filename):
    """
    Save data as JSON.
    """

    folder = os.path.dirname(filename)


    if folder and not os.path.exists(folder):
        os.makedirs(folder)



    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )





def extract_urls(json_file):

    """
    Extract URL + category from JSON file.
    """

    with open(
        json_file,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    urls = []


    for item in data:

        urls.append(
            {
                "url": item["url"],
                "category": item["category"]
            }
        )


    return urls





# ============================
# MAIN
# ============================


urls = extract_urls(
    "blueprint_selected_categories_urls.json"
)



base_folder = (
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\blueprint_genetics_UPDATED"
)



for item in urls:


    url = item["url"]

    category = item["category"]



    print("\nScraping:")
    print(url)



    scraper = BlueprintScraper(
        url,
        category
    )


    panel = scraper.scrape()



    if panel["panel_name"] is None:

        print("No panel name found, skipping")
        continue



    filename = (
        panel["panel_name"]
        .replace(" ", "_")
        .replace("/", "_")
        .lower()
        + ".json"
    )

    filepath = os.path.join(
    base_folder,
    filename
    )


    save_json(
        panel,
        filepath
    )



    print(
        "Saved:",
        filepath
    )


    print(
        "Genes extracted:",
        len(panel["genes"])
    )