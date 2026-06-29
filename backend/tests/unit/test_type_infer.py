from app.engine.import_pipeline.type_infer import infer_from_samples, parse_logical_type


def test_infer_basic_types():
    header = ["id", "name", "flag"]
    rows = [["1", "alice", "true"], ["2", "bob", "false"]]
    inferred = infer_from_samples(header, rows)
    assert inferred[0].logical_type.type_id.name == "INT64"
    assert inferred[1].logical_type.type_id.name == "UTF8"
    assert inferred[2].logical_type.type_id.name == "BOOLEAN"


def test_parse_logical_type_override():
    lt = parse_logical_type("FLOAT64")
    assert lt.type_id.name == "FLOAT64"
