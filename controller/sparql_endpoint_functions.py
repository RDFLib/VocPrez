import requests
import io
from rdflib import Graph
from pyldapi import Renderer
import _config as config
import logging


def get_sparql_service_description(rdf_format='turtle'):
    """Return an RDF description of PROMS' read only SPARQL endpoint in a requested format

    :param rdf_format: 'turtle', 'n3', 'xml', 'json-ld'
    :return: string of RDF in the requested format
    """
    sd_ttl = '''
        @prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sd:     <http://www.w3.org/ns/sparql-service-description#> .
        @prefix sdf:    <http://www.w3.org/ns/formats/> .
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <http://gnafld.net/sparql>
            a                       sd:Service ;
            sd:endpoint             <%(BASE_URI)s/function/sparql> ;
            sd:supportedLanguage    sd:SPARQL11Query ; # yes, read only, sorry!
            sd:resultFormat         sdf:SPARQL_Results_JSON ;  # yes, we only deliver JSON results, sorry!
            sd:feature sd:DereferencesURIs ;
            sd:defaultDataset [
                a sd:Dataset ;
                sd:defaultGraph [
                    a sd:Graph ;
                    void:triples "100"^^xsd:integer
                ]
            ]
        .
    '''
    g = Graph().parse(io.StringIO(sd_ttl), format='turtle')
    rdf_formats = list(set([x for x in Renderer.RDF_SERIALIZER_TYPES_MAP]))
    if rdf_format[0][1] in rdf_formats:
        return g.serialize(format=rdf_format[0][1])
    else:
        raise ValueError('Input parameter rdf_format must be one of: ' + ', '.join(rdf_formats))


def sparql_query(query, format_mimetype='application/json'):
    """ Make a SPARQL query"""
    data = query
    
    headers = {
        'Content-Type': 'application/sparql-query',
        'Accept': format_mimetype,
        'Accept-Encoding': 'UTF-8',
    }
    if hasattr(config, 'SPARQL_USERNAME') and hasattr(config, 'SPARQL_PASSWORD'):
        auth = (config.SPARQL_USERNAME, config.SPARQL_PASSWORD)
    else:
        auth = None
        
    try:
        logging.debug('endpoint={}\ndata={}\nheaders={}'.format(config.SPARQL_ENDPOINT, data, headers))
        r = requests.post(config.SPARQL_ENDPOINT, auth=auth, data=data, headers=headers, timeout=60)
        logging.debug('response: {}'.format(r.__dict__))
        return r.content.decode('utf-8')
    except Exception as e:
        raise e


if __name__ == '__main__':
    q = '''
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT * WHERE {?s a skos:ConceptScheme .}
        '''
