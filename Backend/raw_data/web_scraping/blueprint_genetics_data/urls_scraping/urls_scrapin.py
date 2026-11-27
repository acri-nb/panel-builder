from bs4 import BeautifulSoup
import json

def count_subcategories(results):

    counts = {}

    for item in results:

        category = item["category"]

        if category not in counts:
            counts[category] = set()

        counts[category].add(item["name"])


    # convert sets to numbers
    for category in counts:
        counts[category] = len(counts[category])


    return counts

html_file = "Panels - Blueprint Genetics.html"


categories = [
    "cardiology",
    "dermatology",
    "ear-nose-throat",
    "endocrinology",
    "gastroenterology",
    "hematology",
    "hereditary-cancer",
    "immunology",
    "malformations",
    "metabolic-disorders",
    "nephrology",
    "neurology",
    "ophthalmology",
    "proactive",
    "pulmonology",
    "reproductive",
    "screening/screening-tests"
]


base_url = "https://www.blueprintgenetics.com"


with open(html_file, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")


results = []


for a in soup.find_all("a", href=True):

    href = a["href"]
    name = a.get_text(strip=True)

    href_lower = href.lower()


    for category in categories:

        if f"/{category}/" in href_lower:

            full_url = (
                href 
                if href.startswith("http")
                else base_url + href
            )


            results.append({
                "category": category,
                "name": name,
                "url": full_url
            })

            break

# remove duplicates
unique_results = {
    item["url"]: item 
    for item in results
}


results = list(unique_results.values())


print(f"Found {len(results)} URLs")


with open(
    "blueprint_selected_categories_urls.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        indent=4,
        ensure_ascii=False
    )

counts = count_subcategories(results)

for category, number in counts.items():
    print(category, ":", number)