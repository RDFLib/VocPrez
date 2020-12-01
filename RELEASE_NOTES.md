# Release Notes

## 3.0 - next, late 2020
* improved profile configurability

See the [Issues list](https://github.com/RDFLib/VocPrez/issues) for issues tagged 3.0.


## 2.5 - current, late November 2020
* implemented a new Vocabularies model, instead of default pyLDAPI Container for list of vocabs
* updated SPARQL GUI
    * folded /endpoint into /sparql
* tidied app.py by moving some functions to utils.py
* implemented get_content_uri() in all templates
* tidied template HTML & CSS
* whole-system DCAT & SDO view


## 2.4
* improved caching
* vocabulary class extension for other_properties
* config file not backwards compatible due to need for CACHE_FILE, not CACHE_DIR property


## 2.3
* cache purge function added


## 2.2
* search page added
* minor improvements


## 2.1 - July 2020
* consistent absolute URI / local URIs everywhere
* UI fixes
* prettier documentation


## 2.0 - June 2020
Current release. A Major code refactoring of 1.0 although minimal functionality changes.

Skins for different organisation's instances were factored out. See [SURROUND Australia's code repos](https://github.com/surroundaustralia/) for a number of organisation's skins.


## 1.0 - legacy
Previous release, no longer supported, soon to have no instances online.

Code for this release preserved in [1.0 branch](https://github.com/RDFLib/VocPrez/tree/1.0).