class Source:
    VOC_TYPES = [
        'http://purl.org/vocommons/voaf#Vocabulary'
        'http://www.w3.org/2004/02/skos/core#ConceptScheme',
        'http://www.w3.org/2004/02/skos/core#ConceptCollection',
        'http://www.w3.org/2004/02/skos/core#Concept'
    ]

    def list_vocabularies(self):
        pass

    def list_collections(self, vocab):
        pass

    def list_concepts(self, vocab):
        pass

    def get_vocabulary(self, vocab):
        pass

    def get_collection(self, vocab, uri):
        pass

    def get_concept(self, vocab, uri):
        pass

    def get_concept_hierarchy(self, vocab):
        pass

    def get_object_class(self, vocab, uri):
        """Gets the class of the object.

        Classes restricted to being one of voaf:Vocabulary, skos:ConceptScheme, skos:Collection or skos:Collection

        :param uri: the URI of the object

        :return: the URI of the class of the object
        :rtype: :class:`string`
        """
        pass
