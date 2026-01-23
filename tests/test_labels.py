import json

from easymapping import DockerLabelHandler


def test_label_generation():
    label = DockerLabelHandler("foo")

    assert label.create("bar") == "foo.bar"
    assert label.create(["bar", "foobar"]) == "foo.bar.foobar"


def test_label_data():
    label = DockerLabelHandler("base")
    label.set_data(json.loads('{"base.definitions":"h2"}'))

    label_name = label.create("definitions")
    assert label_name == "base.definitions"
    assert label.has_label(label_name)
    assert label.get(label_name) == "h2"


def test_label_complex_key():
    label = DockerLabelHandler("till")
    
    data = dict()
    data["till.definitions"] = "h2"
    data["till.host.h2"] = "fqdn.example.org"
    data["till.mode.h2"] = "tcp"
    label.set_data(json.loads(json.dumps(data)))

    assert label.get(label.create(["host", "h2"])) == "fqdn.example.org"
    assert label.get(label.create(["mode", "h2"])) == "tcp"
