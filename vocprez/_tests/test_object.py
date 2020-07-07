import requests


def test_no_uri_or_vocab_uri():
    r = requests.get(
        "http://localhost:5000/object"
    )

    assert r.status_code == 400

    r = requests.get(
        "http://localhost:5000/object?uri="
    )

    assert r.status_code == 400

    r = requests.get(
        "http://localhost:5000/object?vocab_uri="
    )

    assert r.status_code == 400

    r = requests.get(
        "http://localhost:5000/object?vocab_uri=&uri="
    )

    assert r.status_code == 400

    r = requests.get(
        "http://localhost:5000/object?vocab_id&uri"
    )

    assert r.status_code == 400


def test_no_uri_but_vocab_uri():
    r = requests.get(
        "http://localhost:5000/object",
        params={
            "vocab_uri": "http://resource.geosciml.org/classifierscheme/cgi/2016.01/boreholedrillingmethod"
        }
    )

    assert r.status_code == 200


if __name__ == "__main__":
    # test_no_uri_or_vocab_uri()
    test_no_uri_but_vocab_uri()
