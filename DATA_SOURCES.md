# Data Sources

VocPrez is designed to be able to read vocabulary information from a number of sources. Currently, the following sources have been configured:

* [Research Vocabularies Australia](http://vocabs.ands.org.au) (RVA)
* local RDF files
* [VocBench3](http://vocbench.uniroma2.it/)

VocPrez requires a static index of vocabularies you want it to display to be created in your installation's config file stored at `_config/__init__.py`. An example list looks like this: 

```
VOCABS = {
    'rva-50': {
        'source': VocabSource.RVA,
        'title': 'Geologic Unit Type'
    },
    'rva-52': {
        'source': VocabSource.RVA,
        'title': 'Contact Type'
    },
    
    ...

    'tenement_type': {
        'source': VocabSource.FILE,
        'title': 'Tenement Type'
    },
    'Test_Rock_Types_Vocabulary': {
        'source': VocabSource.VOCBENCH,
        'title': 'Test Rock Types'
    }
}
```

Here you see vocabularies with IDs 'rva-50', 'rva-52', 'tenement_type' & 'Test_Rock_Types_Vocabulary' with both titles and sources for them given. The first two are drawn from RVA, the 3rd, a file and the last from a VocBench installation. 

The controlled list of source types (`VocabSource.FILE`, `VocabSource.VOCBENCH` etc.) are handled by dedicated *source* Python code classes that present a standard set of methods for each type. The files currently implemented, all in the `data/` folder, are:

* `source_RVA.py` - RVA
* `source_FILE.py` - FILE
* `source_VOCBENCH.py` - VOCBENCH

Additional source files for other vocabulary data sources can be made by creating new `source_*.py` files inheriting from `source.py`.

The specific requirements for each source are contained within their particular files but, summarising the requirements for the sources already catered for, Vocabularies from RVA need to have endpoints specified in the vocab source file `data/source_RVA.py` so VocPrez knows where to get info from. RDF files in `data/` will automatically be picked up by VocPrez so don;t need any more config than a title, provided the ID matched the file name, minus file extension. Vocabs from VocBench require that a `VB_ENDPOINT`, `VB_USER` & `VB_PASSWORD` are all given in the config file.
