# ROUTE index
@app.route("/")
def index():
    import bs4

    def hierarchicalise(input: list):
        def traverse(set_hierarchy, roots):
            hierarchy = {}
            for name in roots:
                hierarchy[name] = traverse(set_hierarchy, set_hierarchy[name])
            return hierarchy

        def sorted_hierarchy(hierarchy, i=0):
            sorted_ls = []
            for k, v in sorted(hierarchy.items()):
                sorted_ls.append((k, i))
                sorted_ls.extend(sorted_hierarchy(v, i=i + 1))
            return sorted_ls

        set_hierarchy = {name: set() for el in input for name in el}
        has_parent = {name: False for el in input for name in el}

        for parent, child in input:
            # Add child
            set_hierarchy[parent].add(child)
            # Update has_parent dict
            has_parent[child] = True

        no_parents = []
        for name, parents in has_parent.items():
            if not parents:
                no_parents.append(name)

        # No parents
        roots = [name for name, parents in has_parent.items() if not parents]

        # Hierarchy
        hierarchy = traverse(set_hierarchy, roots)

        sorted_output = sorted_hierarchy(hierarchy)

        return sorted_output

    def test_hierarchicalise():
        test_input = [
            ("A", "B"),
            ("A", "C"),
            ("K", "D"),
            ("B", "D"),
            ("C", "E"),
            ("E", "F"),
            ("F", "G"),
            ("F", "H"),
            ("I", "J"),
            ("I", "X"),
            ("K", "L"),
            ("L", "M"),
            ("A", "X"),
            ("X", "Y"),
            ("M", "D")
        ]
        actual = hierarchicalise(test_input)
        expected = [
            ("A", 0),
            ("B", 1),
            ("D", 2),
            ("C", 1),
            ("E", 2),
            ("F", 3),
            ("G", 4),
            ("H", 4),
            ("X", 1),
            ("Y", 2),
            ("I", 0),
            ("J", 1),
            ("X", 1),
            ("Y", 2),
            ("K", 0),
            ("D", 1),
            ("L", 1),
            ("M", 2),
            ("D", 3),
        ]

        assert actual == expected

    def make_hierarchical_list_html(parent_child_label_list: list):
        pairs = [(parent_child[0], parent_child[1]) for parent_child in parent_child_label_list if
                 parent_child[0] is not None]
        labels = {}
        for (parent, child, label) in parent_child_label_list:
            labels[child] = label

        hierarchical_list = hierarchicalise(pairs)

        md = ""
        for i in hierarchical_list:
            md += "{}* [{}]({})\n".format(i[1] * "    ", labels[i[0]], i[0])

        return bs4.BeautifulSoup(markdown.markdown(md), features="html.parser").prettify()

    def test_hierarchical_list_html():
        test_input = [
            (None, "A", "Aa"),
            (None, "I", "Ii"),
            (None, "K", "Kk"),
            ("A", "B", "Bb"),
            ("A", "C", "Cc"),
            ("K", "D", "Dd"),
            ("B", "D", "Dd"),
            ("C", "E", "Ee"),
            ("E", "F", "Ff"),
            ("F", "G", "Gg"),
            ("F", "H", "Hh"),
            ("I", "J", "Ii"),
            ("I", "X", "Xx"),
            ("K", "L", "Ll"),
            ("L", "M", "Mm"),
            ("A", "X", "Xx"),
            ("X", "Y", "Yy"),
            ("M", "D", "Dd")
        ]
        expected = """<ul>
     <li>
      <a href="A">
       Aa
      </a>
      <ul>
       <li>
        <a href="B">
         Bb
        </a>
        <ul>
         <li>
          <a href="D">
           Dd
          </a>
         </li>
        </ul>
       </li>
       <li>
        <a href="C">
         Cc
        </a>
        <ul>
         <li>
          <a href="E">
           Ee
          </a>
          <ul>
           <li>
            <a href="F">
             Ff
            </a>
            <ul>
             <li>
              <a href="G">
               Gg
              </a>
             </li>
             <li>
              <a href="H">
               Hh
              </a>
             </li>
            </ul>
           </li>
          </ul>
         </li>
        </ul>
       </li>
       <li>
        <a href="X">
         Xx
        </a>
        <ul>
         <li>
          <a href="Y">
           Yy
          </a>
         </li>
        </ul>
       </li>
      </ul>
     </li>
     <li>
      <a href="I">
       Ii
      </a>
      <ul>
       <li>
        <a href="J">
         Ii
        </a>
       </li>
       <li>
        <a href="X">
         Xx
        </a>
        <ul>
         <li>
          <a href="Y">
           Yy
          </a>
         </li>
        </ul>
       </li>
      </ul>
     </li>
     <li>
      <a href="K">
       Kk
      </a>
      <ul>
       <li>
        <a href="D">
         Dd
        </a>
       </li>
       <li>
        <a href="L">
         Ll
        </a>
        <ul>
         <li>
          <a href="M">
           Mm
          </a>
          <ul>
           <li>
            <a href="D">
             Dd
            </a>
           </li>
          </ul>
         </li>
        </ul>
       </li>
      </ul>
     </li>
    </ul>"""
        actual = make_hierarchical_list_html(test_input)

        assert expected == actual

    q = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX policy: <http://www.opengis.net/def/metamodel/ogc-na/>
        SELECT DISTINCT ?parent ?parentlabel ?child ?childlabel
        WHERE {  
          BIND (<http://www.opengis.net/def> As ?this )
          GRAPH ?this {
            ?this a skos:ConceptScheme .
            ?parent a skos:Collection .
            ?parent skos:member ?child .
            OPTIONAL { ?parent skos:prefLabel ?ppl}
            OPTIONAL { ?parent rdfs:label ?pl }
            BIND(COALESCE(?ppl, ?pl, STR(?parent)) AS  ?parentlabel )
          }   
          ?cs2 policy:collectionView ?child .
          OPTIONAL { ?cs2 skos:prefLabel ?cpl}
          OPTIONAL { ?cs2 rdfs:label ?cl }
          BIND( COALESCE(?cpl, ?cl, STR(?cs2) ) AS  ?childlabel )
        }
        """

    parent_child_label_list = []
    seen = {}
    res = sparql_query(q)
    for r in res:
        p = str(r["parent"]["value"])
        pl = str(r["parentlabel"]["value"])
        c = str(r["child"]["value"])
        cl = str(r["childlabel"]["value"])
        parent_child_label_list.append(
            (p, c, cl)
        )
        seen[p] = pl
        if seen.get(c):
            del seen[c]

    # add in top Collections
    for p, pl in seen.items():
        parent_child_label_list.append(
            (None, p, pl)
        )

    h = make_hierarchical_list_html(parent_child_label_list)

    return render_template(
        "index.html",
        hierarchy=h
    )
# END ROUTE index
