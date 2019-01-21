import _config as config
import sys
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
import markdown


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
            return getattr(FILE(self.vocab_id, self.request), function_name)
        elif source_type == config.VocabSource.RVA:
            return getattr(RVA(self.vocab_id, self.request), function_name)
        elif source_type == config.VocabSource.VOCBENCH:
            return getattr(VOCBENCH(self.vocab_id, self.request), function_name)

    def __init__(self, vocab_id, request):
        self.vocab_id = vocab_id
        self.request = request

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

    @staticmethod
    def get_prefLabel_from_uri(uri):
        return ' '.join(str(uri).split('#')[-1].split('/')[-1].split('_'))

    @staticmethod
    def get_narrowers(uri, depth):
        """
        Recursively get all skos:narrower properties as a list.

        :param uri: URI node
        :param depth: The current depth
        :param g: The graph
        :return: list of tuples(tree_depth, uri, prefLabel)
        :rtype: list
        """
        depth += 1

        # Some RVA sources won't load on first try, so ..
        # if failed, try load again.
        g = None
        max_attempts = 10
        for i in range(max_attempts):
            try:
                g = Graph().parse(uri + '.ttl', format='turtle')
                break
            except:
                print('Failed to load resource at URI {}. Attempt: {}.'.format(uri, i+1))
        if not g:
            raise Exception('Failed to load Graph from {}. Maximum attempts exceeded {}.'.format(uri, max_attempts))

        items = []
        for s, p, o in g.triples((None, SKOS.broader, URIRef(uri))):
            items.append((depth, str(s), Source.get_prefLabel_from_uri(s)))
        items.sort(key=lambda x: x[2])
        count = 0
        for item in items:
            count += 1
            new_items = Source.get_narrowers(item[1], item[0])
            items = items[:count] + new_items + items[count:]
            count += len(new_items)
        return items

    @staticmethod
    def draw_concept_hierarchy(hierarchy, request, id):
        tab = '\t'
        previous_length = 1

        text = ''
        tracked_items = []
        for item in hierarchy:
            mult = None

            if item[0] > previous_length + 2: # SPARQL query error on length value
                for tracked_item in tracked_items:
                    if tracked_item['name'] == item[3]:
                        mult = tracked_item['indent'] + 1

            if mult is None:
                found = False
                for tracked_item in tracked_items:
                    if tracked_item['name'] == item[3]:
                        found = True
                if not found:
                    mult = 0

            if mult is None:#else: # everything is normal
                mult = item[0] - 1

            tag = str(mult+1) # indent info to be displayed

            t = tab * mult + '* [' + item[2] + '](' + request.url_root + 'object?vocab_id=' + id + '&uri=' + item[1] + ') (' + tag + ')\n'
            text += t
            previous_length = mult
            tracked_items.append({'name': item[1], 'indent': mult})

        return markdown.markdown(text)
