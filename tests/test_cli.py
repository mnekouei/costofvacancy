import json

from cost_of_vacancy.cli import main


def test_cli_demo_json_output(capsys):
    exit_code = main(["--hospital", "Springfield General Hospital", "--specialty", "Cardiology", "--demo", "--json"])
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hospital"] == "Springfield General Hospital"
    assert out["matched_provider_count"] == 3
    assert out["total_cost_of_vacancy"] > 0


def test_cli_demo_text_report_contains_total(capsys):
    exit_code = main(["--hospital", "Springfield General Hospital", "--specialty", "Cardiology", "--demo"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "TOTAL COST OF VACANCY" in out


def test_cli_overrides_change_output(capsys):
    main(["--hospital", "Springfield General Hospital", "--specialty", "Cardiology", "--demo", "--json",
          "--vacant-days", "30", "--locum-daily-rate", "1000", "--recruitment-cost", "5000"])
    out = json.loads(capsys.readouterr().out)
    assert out["vacant_days"] == 30
    assert out["locum_coverage_component"] == 30000.0
    assert out["recruitment_component"] == 5000.0
