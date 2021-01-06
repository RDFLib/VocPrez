from vocprez import utils


def test_get_absolute_uri():
    uri = "http%3A//resource.geosciml.org/def/voc/"
    assert utils.get_absolute_uri(uri, {}) == "http://resource.geosciml.org/def/voc/"

    uri = "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/"
    assert utils.get_absolute_uri(uri, {}) == "http://resource.geosciml.org/def/voc/"

    uri = "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/&_profile=x&_mediatype=y"
    assert utils.get_absolute_uri(uri, {}) == "http://resource.geosciml.org/def/voc/?_mediatype=y&_profile=x"

    uri = "http://localhost:5000/object?_profile=x&uri=http%3A//resource.geosciml.org/def/voc/&_mediatype=y"
    assert utils.get_absolute_uri(uri, {}) == "http://resource.geosciml.org/def/voc/?_mediatype=y&_profile=x"

    uri = "http://resource.geosciml.org/def/voc/"
    assert utils.get_absolute_uri(uri, {}) == "http://resource.geosciml.org/def/voc/"

    uri = "http://resource.geosciml.org/def/voc/?_profile=x"
    assert utils.get_absolute_uri(uri, {}) == "http://resource.geosciml.org/def/voc/?_profile=x"

    uri = "http://resource.geosciml.org/def/voc/?_profile=x&_mediatype=y"
    assert utils.get_absolute_uri(uri) == "http://resource.geosciml.org/def/voc/?_mediatype=y&_profile=x"

    uri = "http%3A//resource.geosciml.org/def/voc/"
    assert utils.get_absolute_uri(uri, {"_profile": "alt"}) == "http://resource.geosciml.org/def/voc/?_profile=alt"

    uri = "http://resource.geosciml.org/def/voc/?_profile=x&_mediatype=y"
    assert utils.get_absolute_uri(uri, {"_profile": "alt"}) == \
           "http://resource.geosciml.org/def/voc/?_mediatype=y&_profile=alt"


def test_get_system_uri():
    uri = "http%3A//resource.geosciml.org/def/voc/"
    assert utils.get_system_uri(uri) == "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/"

    uri = "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/"
    assert utils.get_system_uri(uri) == \
           "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/"

    uri = "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/&_profile=x&_mediatype=y"
    assert utils.get_system_uri(uri) == \
           "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/&_mediatype=y&_profile=x"

    uri = "http://localhost:5000/object?_profile=a&uri=http%3A//resource.geosciml.org/def/voc/&_mediatype=b"
    assert utils.get_system_uri(uri, {}) == \
           "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/&_mediatype=b&_profile=a"

    uri = "http://resource.geosciml.org/def/voc/"
    assert utils.get_system_uri(uri, {}) == "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/"

    uri = "http://resource.geosciml.org/def/voc/?_profile=x"
    assert utils.get_system_uri(uri, {}) == \
           "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/&_profile=x"

    uri = "http://resource.geosciml.org/def/voc/?_profile=x&_mediatype=y"
    assert utils.get_system_uri(uri) == \
           "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/&_mediatype=y&_profile=x"

    uri = "http://resource.geosciml.org/def/voc/"
    assert utils.get_system_uri(uri, {"_profile": "alt"}) == \
           "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/&_profile=alt"

    uri = "http://resource.geosciml.org/def/voc/?_profile=x&_mediatype=y"
    assert utils.get_system_uri(uri, {"_profile": "alt"}) == \
           "http://localhost:5000/object?uri=http%3A//resource.geosciml.org/def/voc/&_mediatype=y&_profile=alt"
