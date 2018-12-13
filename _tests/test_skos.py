# this file contains standard tests for SKOS content delivery that should pass for all SKOS Styler implementations

# load the application home page

# load the vocabulary register
    # test for a register property

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