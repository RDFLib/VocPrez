# VocPrez

![VocPrez logo](_media/VocPrez.300.png) 

A read-only web delivery system for Simple Knowledge Organization System (SKOS)-formulated RDF vocabularies.

# Introduction 

VocPrez is used by:

<a href="https://www.business.qld.gov.au/industries/mining-energy-water/resources/geoscience-information/gsq">
    <img src="_media/logo-gsq.jpg" alt="GSQ Logo" style="width:80px;" />
</a>

* [Geological Survey of Queensland](https://www.business.qld.gov.au/industries/mining-energy-water/resources/geoscience-information/gsq)
    * System link: <https://vocabs.gsq.digital> 

<a href="https://www.ga.gov.au">
    <img src="_media/logo-ga.jpg" alt="GA Logo" style="width:100px;" />
</a> 

* [Geoscience Australia](https://www.ga.gov.au)
    * System link (demo): <http://ga.surroundaustralia.com> 
    
<a href="http://www.cgi-iugs.org/">
    <img src="_media/logo-cgi.jpg" alt="CGI Logo" style="width:100px;" />
</a> 

* [Commission for the Management and Application of Geosceicne Information (CGI)](http://www.cgi-iugs.org/)
    * System link: <http://cgi.vocabs.ga.gov.au/>     
    

## VocPrez structure

![](_media/system.500.png)  
**Figure 1**: An overview diagram of where VocPrez fits in relation to sources of vocab data.

VocPrez can get vocabularies from one or more *sources* and any instance can be tuned to use any set of *sources*. This allows for use with a wide range of back-end vocabulary management.

Technically, the tool is a SKOS-specific implementation of the [pyLDAPI](https://github.com/rdflib/pyLDAPI). pyLDAPI is a generic tool for the deliver of [RDF](https://www.w3.org/RDF/) data online in both human- and machine-readable formats; it turns RDF data into *[Linked Data](https://www.w3.org/standards/semanticweb/data)*. 

## SKOS

pyLDAPI needs deployment-specific templates for registers & classes that present the data of interest in that deployment. VocPrez is pre-configured with templates for SKOS' core data classes - `ConceptScheme`, `Collection` & `Concept` - and registers of them. It also assumes that a `ConceptScheme` is synonymous with a *Vocabulary*.

This tool is *not* a SKOS data editor! It is expected to be used with a SKOS data source (any sort of datasource can be configured and three come pre-loaded) and its only role is to publish that SKOS data online as Linked Data.

The design goal for this tool was to provide an easily configurable template-based SKOS presenter since many of the other SKOS editing and presentation tools, available as of November 2018, are pretty complex instruments and make life difficult for normal web development tasks such as institutional branding of vocabulary data.

Since this tool is preconfigured for SKOS data, it is ready for use with SKOS-only vocabularies. Forks of this codebase can be made to enhance it for SKOS+ features. SKOS+ is a general term for SKOS data *plus some other bits*.


## API & Templates

As per other pyLDAPI deployments, this tool uses the [Jinja2 Python templating engine](http://jinja.pocoo.org/) to generate HTML and other files which are called fro use through Python's [Flask](http://flask.pocoo.org/), a small HTTP framework.

Standard templates for `ConceptScheme`, `Collection`, `Concept` & `Register` are contained within this repository, as is a Model-View-Controller-style deployment of Flask, pre-configures for SKOS.

# Installation

* follow the instructions as per pyLDAPI (see [its documentation](https://pyldapi.readthedocs.io))
* ensure your config file is correct
    * you need to copy the file `_config/template.py` to `_config/__init__.py` and configure carables within it. See the template.py` file for examples
* configure your data source(s)
    * you will need to supply this tool with SKOS data from any sort of data source: a triplestore, a relational database or even a local file
    * see the [Data Sources](README?id=data-sources) file for examples

## Data Sources

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

## Dependencies

See the [requirements.txt](https://github.com/RDFLib/VocPrez/blob/master/requirements.txt) standard Python dependency listing file.


## Releases

See [RELEASE_NOTES.md](RELEASE_NOTES.md) for notes on major releases and plans for future releases.


## License

This code is licensed using the GPL v3 licence. See the [LICENSE file](LICENSE) for the deed.


## Tests

We use [pytest](https://docs.pytest.org/en/latest/) as our testing framework. Tests live in the [tests directory](_tests). These tests ensure that the endpoints are functioning as intended. See the [README.md](_tests/README.md) for the tests for more information.

# Deployment

## Ansible

Coming Soon!

## AWS

Coming soon!

## Docker 

To override the endpoint in the template set the ENDPOINT environment variable. 

### Docker build

First we must build a container from the dockerfile. 

`sudo docker build -t vocprez . -f Dockerfile`

### Docker Run 

To run the container we need to copy the settings from `_config/template.py` to `_config/__init__.py` and set the port. 

 `docker run -it -v $PWD/vocprez/_config/template.py:/vocprez/_config/__init__.py -p 5000:5000 vocprez`

# Contacts
*Author*:  
**Nicholas Car**  
*Data Systems Architect*  
[SURROUND Australia Pty Ltd](http://surroundaustralia.com)  
<nicholas.car@surroundaustralia.com>
