"""Load some of the CGI vocabs into an in-memory Fuseki store"""
import os
from urllib.parse import urljoin
import requests
from requests.auth import HTTPBasicAuth

FUSEKI_HOST = os.environ.get('FUSEKI_HOST','http://fuseki:3030/')

# "Assembler file" to HTTP POST create new dataset in Fuseki
DB = """PREFIX tdb:     <http://jena.hpl.hp.com/2008/tdb#>
PREFIX rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ja:      <http://jena.hpl.hp.com/2005/11/Assembler#>

<#dataset> rdf:type         tdb:DatasetTDB ;
    tdb:location "DB" ;"""

# Vocabularies that we want in our test dataset
VOCABS = [
        "http://resource.geosciml.org/classifierscheme/cgi/2016.01/boreholedrillingmethod",
        "http://resource.geosciml.org/classifier/cgi/contacttype"]


def create_db(name='db'):
    response = requests.post(urljoin(FUSEKI_HOST, '$/datasets'),
                             data=DB,
                             auth=HTTPBasicAuth('admin', 'admin'),
                             params={'dbType': 'mem',
                                     'dbName': 'db'})

    response.raise_for_status()


def add_vocab(url):
    headers = {'Accept': 'application/n-triples'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.content.decode('utf-8')
    print(data)
    status = requests.put(
            urljoin(FUSEKI_HOST, 'db/data?default'),
            headers={'Content-type': 'application/n-triples'},
            data=response.content)
    status.raise_for_status()


if __name__ == '__main__':
    create_db()
    for url in VOCABS:
        add_vocab(url)
