from rdflib import URIRef, Literal


class Property(object):
    def __init__(self, uri: str, label: str, value: URIRef or Literal, value_label: str = None):
        self.uri = uri
        self.label = label
        self.value = value
        self.value_label = value_label
