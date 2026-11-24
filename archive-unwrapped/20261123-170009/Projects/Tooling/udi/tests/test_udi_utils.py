from uditool.udi_utils import slugify, parse_udi, build_udi, validate_udi


def test_slugify_basic():
    assert slugify("My Example Name") == "my-example-name"


def test_parse_and_build():
    u = build_udi("prismata", "demo", "schema", "my-slug")
    p = parse_udi(u)
    assert p["namespace"] == "prismata"
    assert p["kind"] == "schema"


def test_validate_good():
    ok, errs = validate_udi("prismata.demo.schema.my-slug")
    assert ok
