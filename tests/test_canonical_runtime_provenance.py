from pathlib import Path
import importlib


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_api_and_preview_imports_resolve_inside_canonical_repo():
    api = importlib.import_module("agent.api")
    engine = importlib.import_module("agent.floor_heating_engine")
    preview_api = importlib.import_module("agent.floor_heating_preview_api")
    preview = importlib.import_module("agent.ufh_routing_preview")
    for module in (api, engine, preview_api, preview):
        assert Path(module.__file__).resolve().is_relative_to(ROOT)
    assert preview_api.calculate_floor_heating is engine.calculate_floor_heating
    assert preview.calculate_floor_heating is engine.calculate_floor_heating


def test_real_plan_generator_uses_canonical_source_family():
    source = (ROOT / "scripts" / "build_real_floor_ufh_artifacts.py").read_text(encoding="utf-8")
    assert "agent.test01_geometry_only_ufh_preview" in source
    assert "agent.floor_heating_engine" in (ROOT / "agent" / "test01_geometry_only_ufh_preview.py").read_text(encoding="utf-8")
    assert "homeaura.floor_heating" not in source
