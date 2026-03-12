from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts import extract


def test_extract_masks_cpf() -> None:
    assert extract.mask_cpf("52998224725") == "***.***.***-25"
    assert extract.mask_cpf("bad") == "***"


def test_extract_empty_dataset_writes_header_only(tmp_path, monkeypatch) -> None:
    output = tmp_path / "dataset.csv"

    class _FakeDB:
        pass

    class _FakeClient:
        def __getitem__(self, _name):
            return _FakeDB()

    class _FakeDataFrame:
        def __init__(self, data=None, columns=None):
            self.columns = columns or []

        def to_csv(self, path, index=False):
            Path(path).write_text(",".join(self.columns) + "\n", encoding="utf-8")

    fake_pd = types.SimpleNamespace(DataFrame=_FakeDataFrame)

    monkeypatch.setitem(sys.modules, "pandas", fake_pd)
    monkeypatch.setattr(extract, "MongoClient", lambda _uri: _FakeClient())
    monkeypatch.setattr(extract, "build_rows", lambda _db: [])

    code = extract.run("mongodb://test", "kodie", output)

    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "schema_version" in content
    assert "cpf_masked" in content
