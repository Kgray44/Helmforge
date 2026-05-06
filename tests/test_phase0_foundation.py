from pathlib import Path
import importlib


def test_phase0_product_identity_and_window_title():
    main = importlib.import_module("v3_app.main")

    assert main.APP_NAME == "HelmForge"
    assert main.TECHNICAL_SUBTITLE == "HOTAS Control Panel V3"
    assert main.WINDOW_TITLE == "HelmForge — HOTAS Control Panel V3"


def test_recovery_references_are_documented():
    project_root = Path(__file__).resolve().parents[1]
    recovery_readme = project_root / "docs" / "recovery" / "README.md"
    forensic_spec_set = project_root / "HOTAS Control Panel Forensic Spec Set"
    recovered_png_evidence = forensic_spec_set / "Recovered PNG Evidence"

    assert forensic_spec_set.exists()
    assert recovered_png_evidence.exists()
    assert recovery_readme.exists()

    text = recovery_readme.read_text(encoding="utf-8")
    assert "HOTAS Control Panel Forensic Spec Set" in text
    assert "Recovered PNG Evidence" in text
    assert "governing reconstruction references" in text
