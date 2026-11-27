from bs4 import BeautifulSoup
import requests
import json
import time

#scraping O_H from urls (*add the last updated)

def scrape_ontario_detail(url):

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    data = {
        "source": "Ontario Health",
        "url": url
    }


    # find all dt/dd pairs
    elements = soup.find_all(["dt", "dd"])


    for i in range(0, len(elements)-1, 2):

        key = elements[i].get_text(
            strip=True
        )

        value = elements[i+1].get_text(
            separator=" ",
            strip=True
        )


        data[key] = value

    # extract Last Updated date
    last_updated = None

    for p in soup.find_all("p"):
        text = p.get_text(
            strip=True
        )

        if "Last Updated" in text:
            last_updated = text.replace(
                "Last Updated:",
                ""
            ).strip()

            break

    # fields needed

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


    return result


with open(
    "ontario_health_urls.json",
    "r",
    encoding="utf-8"
) as file:

    diseases = json.load(file)



results = []




for disease in diseases:

    url = disease["url"]

    print("Scraping:", url)

    data = scrape_ontario_detail(url)


    if data:
        results.append(data)


    time.sleep(2)



with open(
    "ontario_health_details_LAST_UPDATE_ADDED.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        results,
        file,
        indent=4,
        ensure_ascii=False
    )