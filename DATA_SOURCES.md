# Data Sources

VocPrez is designed to be able to read vocabulary information from a number of sources. Currently, the following sources have been configured:

* [Research Vocabularies Australia](http://vocabs.ands.org.au) (RVA)
* [VocBench3](http://vocbench.uniroma2.it/)
* genric SPARQL endpoint
* local RDF files

VocPrez generates a cached index of vocabularies you want it to display. It gets the vocab information from a `VOCAB_SOURCES varaible` in the [_config/__init__.py](config/) file you set up. An example list of two sources, RVA & SPRAQL are given in the [template config file](_config/template.py), also copied below.

```
VOCAB_SOURCES = {
    # an example of a SPARQL endpoint - here supplied by an instance of GrpahDB
    'gsq-graphdb': {
        'source': VocabSource.SPARQL,
        'sparql_endpoint': 'http://graphdb.gsq.digital:7200/repositories/GSQ_Vocabularies_core'
    },
    # an example of querying the ARDC RVA vocab system (https://vocabs.ands.org.au)
    'rva': {
        'source': VocabSource.RVA,
        'api_endpoint': 'https://vocabs.ands.org.au/registry/api/resource/vocabularies/{}?includeAccessPoints=true',
        'vocabs': [
            {
                'ardc_id': 50,
                'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/geologicunittype',
            },
            {
                'ardc_id': 52,
                'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/contacttype',
            },
            {
                'ardc_id': 57,
                'uri': 'http://resource.geosciml.org/classifierscheme/cgi/2016.01/stratigraphicrank',
            }
        ]
    }
}
```

Here you see the first source is a SPARQL endpoint. All that's neede here, as specified in the data/source/SPARQL.py file, is a source type ("VocabSource.SPARQL") and a sparql endpoint.

Next is the "RVA" endpoint for which an API endpoint is needed and also a list of vocab IDs and the vocab's URIs. These are neede by data/source/RVA.py to get all the information it needs about vocabularies from RVA.

### New Sources
Additional source files for other vocabulary data sources can be made by creating new `source_*.py` files inheriting from `source.py`. You will need to supply a static `collect()` method that gets all the vocabs and their metadata from the source for the cached vocab index and either make do with or overload the functions in Source.py (such as `get_vocabylary()`) to supply all the other required forms of access to your source's vocabularies.
