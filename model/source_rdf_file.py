from model.source import Source


class RDFFile(Source):
    def list_vocabularies(self):
        pass

    def list_collections(self, vocab_id):
        pass

    def list_concepts(self, vocab_id):
        pass

    def get_vocabulary(self, vocab_id):
        pass

    def get_collection(self, vocab_id, collection_id):
        pass

    def get_concept(self, vocab_id, concept_id):
        pass

    def get_concept_hierarchy(self, concept_id):
        pass
