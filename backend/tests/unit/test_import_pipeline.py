from pathlib import Path

from app.engine.import_pipeline.pipeline import ImportPipeline

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def test_import_pipeline_writes_col_files(tmp_path):
    out = tmp_path / "out"
    pipeline = ImportPipeline(
        source_path=SAMPLES / "basic.csv",
        output_dir=out,
        import_mode="strict",
        target_block_bytes=512,
    )
    result = pipeline.run()
    assert result.row_count == 5
    assert len(result.columns) == 5
    for col in result.columns:
        assert col.path.exists()
        assert col.path.read_bytes().startswith(b"CLCOL001")
