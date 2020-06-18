from bs4 import BeautifulSoup


def render_concept_tree(html_doc):
    soup = BeautifulSoup(html_doc, "html.parser")

    # concept_hierarchy = soup.find(id='concept-hierarchy')

    uls = soup.find_all("ul")

    for i, ul in enumerate(uls):
        # Don't add HTML class nested to the first 'ul' found.
        if not i == 0:
            ul["class"] = "nested"
            if ul.parent.name == "li":
                temp = BeautifulSoup(str(ul.parent.a.extract()), "html.parser")
                ul.parent.insert(
                    0, BeautifulSoup('<span class="caret">', "html.parser")
                )
                ul.parent.span.insert(0, temp)
    return soup