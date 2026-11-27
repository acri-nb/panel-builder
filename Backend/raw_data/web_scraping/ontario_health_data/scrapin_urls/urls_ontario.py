from bs4 import BeautifulSoup
import json


with open("Ontario Health.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")


results = []

articles = soup.find_all("article")


for article in articles:

    # -------------------------
    # Disease name
    # -------------------------
    title = article.find("h3")

    if title:
        name = title.get_text(strip=True)
    else:
        name = None


    # -------------------------
    # URL
    # -------------------------
    link = article.find("a", href=True)

    if link:
        url = link["href"]
    else:
        url = None


    # -------------------------
    # Category
    # -------------------------
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


    results.append({
        "name": name,
        "category": category,
        "url": url
    })


with open(
    "ontario_health_urls.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        indent=4,
        ensure_ascii=False
    )


print("Total diseases:", len(results))