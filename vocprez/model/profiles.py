from pyldapi.profile import Profile
from pyldapi.renderer import Renderer

profile_skos = Profile(
    "https://www.w3.org/TR/skos-reference/",
    label="SKOS",
    comment="Simple Knowledge Organization System (SKOS)is a W3C-authored, common data model for sharing "
    "and linking knowledge organization systems "
    "via the Web.",
    mediatypes=["text/html", "application/json"] + Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_vocpub = Profile(
    "https://w3id.org/profile/vocpub",
    label="VocPub",
    comment="A profile of SKOS for the publication of Vocabularies. This profile mandates the use of one Concept "
            "Scheme per vocabulary",
    mediatypes=["text/html", "application/json"] + Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_dcat = Profile(
    "https://www.w3.org/TR/vocab-dcat/",
    label="DCAT",
    comment="Dataset Catalogue Vocabulary (DCAT) is a W3C-authored RDF vocabulary designed to "
    "facilitate interoperability between data catalogs "
    "published on the Web.",
    mediatypes=["text/html"] + Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_void = Profile(
    "https://www.w3.org/TR/vocab-dcat/",
    label="VoID",
    comment="The Vocabulary of Interlinked Datasets (VoID) is an RDF Schema vocabulary for expressing metadata about "
            "RDF datasets.",
    mediatypes=Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/turtle",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)

profile_ckan = Profile(
    "https://ckan.org/",
    "CKAN",
    comment="The Comprehensive Knowledge Archive Network (CKAN) is a web-based open-source management system for "
    "the storage and distribution of open data. This profile it it's native data model",
    mediatypes=["application/json"],
    default_mediatype="application/json",
    languages=["en"],
    default_language="en",
)

profile_dd = Profile(
    "https://w3id.org/profile/dd",
    "Drop-Down List",
    comment="A simple data model to provide items for form drop-down lists. The basic information is an ID & name tuple "
            "and the optional extra value is an item's parent. For vocabularies, this is then URI, prefLabel or URI, "
            "prefLabel & broader Concept",
    mediatypes=["application/json"],
    default_mediatype="application/json",
    languages=["en"],
    default_language="en",
)

profile_sdo = Profile(
    "https://schema.org",
    label="schema.org",
    comment="Schema.org is a collaborative, community activity with a mission to create, maintain, and promote schemas "
            "for structured data on the Internet, on web pages, in email messages, and beyond.",
    mediatypes=["text/html"] + Renderer.RDF_MEDIA_TYPES,
    default_mediatype="text/html",
    languages=["en"],  # default 'en' only for now
    default_language="en",
)
