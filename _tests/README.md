# Pytest Tests
Before running the tests, make sure that the config file contains an entry for `contact_type`
```python
VOCABS = {
    'contact_type': {
        'source': VocabSource.FILE,
        'title': 'Contact Type (file)'
    }
}
``` 

To run the tests, simply type `pytest <path-to-test-directory>` in your virtualenv. 

See [pytest](https://docs.pytest.org/en/latest/) for more information.

## Coverage

### Static Pages
- [x] `/index.html`
- [x] `/about.html`

### Vocabulary Register
- [x] CKAN view and its formats
- [x] Reg view and its formats
- [x] Alternates view and its formats
- [ ] Search

### File Source

#### Vocabulary Instance
- [x] DCAT view and its formats
- [x] Alternates view and its formats

#### Vocabulary Instance's Concept Register
- [x] CKAN view and its formats
- [x] Reg view and its formats
- [x] Alternates view and its formats
- [ ] Search

#### Concept Instance
- [x] SKOS view and its formats
- [x] Alternates view and its formats


### RVA Source

#### Vocabulary Instance
- [ ] DCAT view and its formats
- [ ] Alternates view and its formats

#### Vocabulary Instance's Concept Register
- [ ] CKAN view and its formats
- [ ] Reg view and its formats
- [ ] Alternates view and its formats
- [ ] Search

#### Concept Instance
- [ ] SKOS view and its formats
- [ ] Alternates view and its formats


### VocBench Source

#### Vocabulary Instance
- [ ] DCAT view and its formats
- [ ] Alternates view and its formats

#### Vocabulary Instance's Concept Register
- [ ] CKAN view and its formats
- [ ] Reg view and its formats
- [ ] Alternates view and its formats
- [ ] Search

#### Concept Instance
- [ ] SKOS view and its formats
- [ ] Alternates view and its formats


### GitHub Source

#### Vocabulary Instance
- [ ] DCAT view and its formats
- [ ] Alternates view and its formats

#### Vocabulary Instance's Concept Register
- [ ] CKAN view and its formats
- [ ] Reg view and its formats
- [ ] Alternates view and its formats
- [ ] Search

#### Concept Instance
- [ ] SKOS view and its formats
- [ ] Alternates view and its formats


### Error Handling
- [ ] Invalid vocab_id
- [ ] VocBench exception
- [ ] Invalid Object Class URI type