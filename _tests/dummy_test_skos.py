# this file contains standard tests for SKOS content delivery that should pass for all SKOS Styler implementations

# load the application home page
    # test it for HTML (title)

# load the vocabulary register
    # test vocabulary register alternated view
    # test vocabulary register for HTML (title)
    # test vocabulary register for RDF (title)

    # select random vocab
        # test vocab alternated view
        # test vocab HTML (title)
        '''<h1>Vocabulary: GA Data Classification</h1>'''
        # test vocab RDF
        '''
        <http://pid.geoscience.gov.au/def/voc/ga/gadata> a rdfs:Resource , skos:ConceptScheme ;
            rdfs:label "GA Data Classification"@en ;
        '''

        # select any Collections in the vocab
            # test Collection alternated view
            # test Collection HTML (title)
            # test Collection RDF

        # select random Concept from the vocab
            # test Concept alternated view
            # test Concept HTML (title)
            # test Concept RDF