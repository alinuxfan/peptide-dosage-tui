"""Regressions for export filename handling.

A profile name containing "/" used to crash the app outright (the export
handlers had no error handling), and five catalog peptides contain "/" --
including "Custom / Other", the default calculator selection -- which made
"Save Schedule to File" fail silently.
"""
import asyncio
import os

from textual.widgets import Input, Select

import db
from main import PeptideCalculatorApp


def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))


def _seed(pid, name="BPC-157"):
    p = db.get_peptide_by_name(name)
    db.add_or_update_user_protocol(
        pid, p["name"], p["vial_mg"], p["water_ml"], p["dose"],
        p["unit"], p["freq"], p["notes"], p["schedule"], p["sources"],
    )


def test_patient_sheet_and_csv_export_with_slash_in_profile_name(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    db.init_db()
    pid = db.add_profile("Adam/Bob")
    _seed(pid)
    db.log_dose(pid, db.get_user_protocols(pid)[0]["id"], "BPC-157", 250.0, "mcg")

    sheet = db.export_person_reference_sheet(pid)
    csv_file = db.export_dose_log_csv(pid)

    assert sheet == "patient_adam_bob_peptides_summary.txt"
    assert csv_file == "dose_log_adam_bob.csv"
    assert os.path.exists(sheet) and os.path.exists(csv_file)


def test_export_handlers_report_errors_instead_of_crashing(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            _seed(app.active_profile_id)
            app.refresh_patient_protocols_table()
            await pilot.pause()

            messages = []
            app.notify = lambda msg, **kw: messages.append((kw.get("severity", "information"), str(msg)))

            def boom(_profile_id):
                raise OSError("disk full")

            monkeypatch.setattr(db, "export_person_reference_sheet", boom)
            monkeypatch.setattr(db, "export_dose_log_csv", boom)

            app.export_patient_sheet()
            app.export_dose_log_csv()

            assert len(messages) == 2
            assert all(sev == "error" for sev, _ in messages)
            assert all("disk full" in text for _, text in messages)

    asyncio.run(run())


def test_schedule_export_works_for_peptide_name_with_slash(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = app.active_profile_id
            _seed(pid, "CJC-1295 / Ipamorelin Blend")
            app.refresh_schedule_selector()
            app.action_switch_tab("schedule-tab")
            await pilot.pause()

            messages = []
            app.notify = lambda msg, **kw: messages.append((kw.get("severity", "information"), str(msg)))

            sched_select = app.query_one("#schedule-protocol-select", Select)
            sched_select.value = next(
                v for label, v in sched_select._options
                if isinstance(label, str) and "CJC-1295 / Ipamorelin" in label
            )
            await pilot.pause()

            app.save_schedule_to_file()
            await pilot.pause()

            assert not any(sev == "error" for sev, _ in messages), messages
            expected = "schedule_default_user_cjc-1295_ipamorelin_blend.txt"
            assert os.path.exists(expected)

    asyncio.run(run())


def test_calculator_rejects_absurd_vial_size_instead_of_rendering_garbage(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        from textual.widgets import Label
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            conc = app.query_one("#calc-concentration", Label)

            app.query_one("#vial-size-input", Input).value = "1e99"
            await pilot.pause()
            assert "10,000 mg or less" in str(conc.content)

            app.query_one("#vial-size-input", Input).value = "5"
            await pilot.pause()
            assert "2.50 mg/mL" in str(conc.content)

    asyncio.run(run())
