import asyncio

from textual.widgets import Button, DataTable, Input, Label

import db
from main import EditDoseScreen, LogDoseScreen, PeptideCalculatorApp


def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))


def _seed_protocol(app):
    pid = app.active_profile_id
    db.add_or_update_user_protocol(
        pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "n", [], []
    )
    app.refresh_patient_protocols_table()
    return pid


def test_log_dose_can_be_backdated(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = _seed_protocol(app)
            app.action_switch_tab("patient-tab")
            await pilot.pause()
            app.query_one("#patient-protocols-table", DataTable).move_cursor(row=0)
            await pilot.pause()

            app.log_selected_protocol_dose()
            await pilot.pause()
            assert isinstance(app.screen, LogDoseScreen)
            app.screen.query_one("#logdose-notes", Input).value = "left thigh"
            app.screen.query_one("#logdose-taken-at", Input).value = "2026-01-05 08:30"
            app.screen.query_one("#logdose-yes", Button).press()
            await pilot.pause()

            log = db.get_dose_log(pid)
            assert len(log) == 1
            assert log[0]["taken_at"] == "2026-01-05 08:30:00"
            assert log[0]["notes"] == "left thigh"

    asyncio.run(run())


def test_log_dose_rejects_bad_date_without_closing(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = _seed_protocol(app)
            app.action_switch_tab("patient-tab")
            await pilot.pause()
            app.query_one("#patient-protocols-table", DataTable).move_cursor(row=0)
            await pilot.pause()

            app.log_selected_protocol_dose()
            await pilot.pause()
            app.screen.query_one("#logdose-taken-at", Input).value = "not-a-date"
            app.screen.query_one("#logdose-yes", Button).press()
            await pilot.pause()

            # modal stays open with an explanation, nothing written
            assert isinstance(app.screen, LogDoseScreen)
            assert "YYYY-MM-DD" in str(app.screen.query_one("#logdose-status", Label).content)
            assert db.get_dose_log(pid) == []

            app.screen.action_cancel()
            await pilot.pause()

    asyncio.run(run())


def test_edit_logged_dose_corrects_amount_date_and_notes(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = _seed_protocol(app)
            protocol_id = db.get_user_protocols(pid)[0]["id"]
            db.log_dose(pid, protocol_id, "BPC-157", 250.0, "mcg", "typo",
                        taken_at="2026-01-05 08:30:00")
            app.refresh_dose_log_tables()
            app.action_switch_tab("dose-log-tab")
            await pilot.pause()

            app.query_one("#dose-log-table", DataTable).move_cursor(row=0)
            await pilot.pause()
            app.edit_selected_dose_log_entry()
            await pilot.pause()
            assert isinstance(app.screen, EditDoseScreen)

            app.screen.query_one("#editdose-amount", Input).value = "500"
            app.screen.query_one("#editdose-taken-at", Input).value = "2026-01-06 09:15"
            app.screen.query_one("#editdose-notes", Input).value = "corrected"
            app.screen.query_one("#editdose-save", Button).press()
            await pilot.pause()

            entry = db.get_dose_log(pid)[0]
            assert entry["dose_amount"] == 500.0
            assert entry["taken_at"] == "2026-01-06 09:15:00"
            assert entry["notes"] == "corrected"

    asyncio.run(run())


def test_edit_dose_validates_amount_and_unit(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = _seed_protocol(app)
            protocol_id = db.get_user_protocols(pid)[0]["id"]
            db.log_dose(pid, protocol_id, "BPC-157", 250.0, "mcg", taken_at="2026-01-05 08:30:00")
            app.refresh_dose_log_tables()
            app.action_switch_tab("dose-log-tab")
            await pilot.pause()
            app.query_one("#dose-log-table", DataTable).move_cursor(row=0)
            await pilot.pause()

            app.edit_selected_dose_log_entry()
            await pilot.pause()
            status = app.screen.query_one("#editdose-status", Label)

            app.screen.query_one("#editdose-amount", Input).value = "-5"
            app.screen.query_one("#editdose-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, EditDoseScreen)
            assert "greater than 0" in str(status.content)

            app.screen.query_one("#editdose-amount", Input).value = "250"
            app.screen.query_one("#editdose-unit", Input).value = "grams"
            app.screen.query_one("#editdose-save", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, EditDoseScreen)
            assert "mcg" in str(status.content)

            # original row untouched throughout
            assert db.get_dose_log(pid)[0]["dose_amount"] == 250.0
            app.screen.action_cancel()
            await pilot.pause()

    asyncio.run(run())
