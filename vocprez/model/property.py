from rdflib import URIRef, Literal


class Property(object):
    def __init__(self, uri: str, label: str, value: URIRef or Literal):
        self.uri = uri
        self.label = label
        self.value = value