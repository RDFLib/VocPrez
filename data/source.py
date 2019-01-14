import _config as config
import sys


class Source:
    VOC_TYPES = [
        'http://purl.org/vocommons/voaf#Vocabulary',
        'http://www.w3.org/2004/02/skos/core#ConceptScheme',
        'http://www.w3.org/2004/02/skos/core#ConceptCollection',
        'http://www.w3.org/2004/02/skos/core#Concept',
    ]

    def _delegator(self, function_name):
        """
        Delegates a call to this upper class to one of its specialised child classes

        :return: a call to a specialised method of a class inheriting from this class
        """
        # specialised sources that this instance knows about
        from data.source_RVA import RVA
        from data.source_FILE import FILE
        from data.source_VOCBENCH import VOCBENCH

        # for this vocab, identified by vocab_id, find its source type
        source_type = config.VOCABS[self.vocab_id].get('source')

        # delegate the constructor of this vocab's source the the specialised source, based on source_type
        if source_type == config.VocabSource.FILE:
            return getattr(FILE(self.vocab_id), function_name)
        elif source_type == config.VocabSource.RVA:
            return getattr(RVA(self.vocab_id), function_name)
        elif source_type == config.VocabSource.VOCBENCH:
            return getattr(VOCBENCH(self.vocab_id), function_name)

    def __init__(self, vocab_id):
        self.vocab_id = vocab_id

    @classmethod
    def list_vocabularies(self):
        pass

    def list_collections(self):
        return self._delegator(sys._getframe().f_code.co_name)()

    def list_concepts(self):
        return self._delegator(sys._getframe().f_code.co_name)()

    def get_vocabulary(self):
        return self._delegator(sys._getframe().f_code.co_name)()

    def get_collection(self, uri):
        return self._delegator(sys._getframe().f_code.co_name)(uri)

    def get_concept(self, uri):
        return self._delegator(sys._getframe().f_code.co_name)(uri)

    def get_concept_hierarchy(self):
        return self._delegator(sys._getframe().f_code.co_name)()

    def get_object_class(self, uri):
        """Gets the class of the object.

        Classes restricted to being one of voaf:Vocabulary, skos:ConceptScheme, skos:Collection or skos:Collection

        :param uri: the URI of the object

        :return: the URI of the class of the object
        :rtype: :class:`string`
        """
        return self._delegator(sys._getframe().f_code.co_name)(uri)
