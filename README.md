ARCHIVED: VocPrez is now incorporated into [Prez!](https://github.com/RDFLib/Prez)

![](vocprez/view/style/VocPrez.300.png)  

VocPrez is a read-only web delivery system - web pages and API - for Simple Knowledge Organization System (SKOS)-formulated RDF vocabularies. It complies with [Content Negotiation by Profile](https://w3c.github.io/dx-connegp/connegp/).

## Introduction
VocPrez is used by:

| &nbsp;                                   | &nbsp;                                                                                                                                                                                       |
|------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ![](vocprez/view/style/logo-ogc-200.png) | The [Open Geospatial Consortium](https://www.ogc.org/) 's Definitions Server<br /><br />System link: <https://defs.opengis.net/vocprez/>                                                     |
| ![](vocprez/view/style/logo-bodc-bw.png) | The [British Oceanographic Data Centre](https://www.bodc.ac.uk/) 's NERC Vocabulary Server<br /><br />System link: <http://vocab.nerc.ac.uk>                                                 |
| ![](vocprez/view/style/logo-gsq-200.jpg) | [Geological Survey of Queensland](https://www.business.qld.gov.au/industries/mining-energy-water/resources/geoscience-information/gsq) <br /><br />System link: <https://vocabs.gsq.digital> |
| ![](vocprez/view/style/logo-ga-200.jpg)  | [Geoscience Australia](https://www.ga.gov.au) <br /><br />System link (demo): <http://ga.surroundaustralia.com>                                                                              |
| ![](vocprez/view/style/logo-cgi-200.jpg) | [Commission for the Management and Application of Geoscience Information (CGI)](http://www.cgi-iugs.org/) <br /><br />System link: <http://cgi.vocabs.ga.gov.au/>                            |
| ![](vocprez/view/style/logo-bgs-200.png) | [British Geological Survey (BGS)](https://bgs.ac.uk/) <br /><br />System link: <https://data.bgs.ac.uk/vocprez/>                                                                             |

## Documentation   

### Run locally

Run the WSGI application on a Linux/Mac command line from the repository root directory like this:

```
gunicorn wsgi:application
```

### Full documentation
     
See the documentation at <https://rdflib.dev/VocPrez/>.

## License

This code is licensed using the GPL v3 licence. See the [LICENSE file in this repository](LICENSE) for the deed. 

Regarding attribution as per the license: please ensure that the VocPrez logo is visible on all public instance of VocPrez.

## Contacts
*Lead Developer*:  
**Nicholas Car**  
*Data Architect*  
[KurrawongAI](https://kurrawong.ai)  
<nick@kurrawong.ai>
