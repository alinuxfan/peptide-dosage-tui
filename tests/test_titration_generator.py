import asyncio

from textual.widgets import Button, DataTable, Input

import db
from main import PeptideCalculatorApp, TitrationGeneratorScreen


def test_generate_titration_button_opens_modal_and_saves_schedule(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            pid = app.active_profile_id
            db.add_or_update_user_protocol(
                pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "notes",
                [("Prescribed Dose", 250.0, "mcg")], [],
            )
            app.refresh_patient_protocols_table()
            await pilot.pause()

            app.action_switch_tab("patient-tab")
            await pilot.pause()

            table = app.query_one("#patient-protocols-table", DataTable)
            table.move_cursor(row=0, column=0)
            await pilot.pause()

            app.generate_titration_for_selected_protocol()
            await pilot.pause()
            assert isinstance(app.screen, TitrationGeneratorScreen)

            app.screen.query_one("#titration-start-input", Input).value = "250"
            app.screen.query_one("#titration-target-input", Input).value = "1000"
            app.screen.query_one("#titration-step-input", Input).value = "250"
            app.screen.query_one("#titration-weeks-input", Input).value = "2"
            app.screen.regenerate_preview()
            await pilot.pause()

            preview = app.screen.query_one("#titration-preview-table", DataTable)
            assert preview.row_count == 4
            assert preview.get_cell_at((3, 1)) == "1000 mcg"

            save_btn = app.screen.query_one("#titration-save-btn", Button)
            save_btn.press()
            await pilot.pause()

            assert not isinstance(app.screen, TitrationGeneratorScreen)

            protocols = db.get_user_protocols(pid)
            saved = next(p for p in protocols if p["peptide_name"] == "BPC-157")
            assert saved["target_dose"] == 1000.0
            assert saved["schedule"][-1][1] == 1000.0
            assert len(saved["schedule"]) == 4

    asyncio.run(run())


def test_generate_titration_cancel_does_not_change_protocol(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            pid = app.active_profile_id
            db.add_or_update_user_protocol(
                pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "notes",
                [("Prescribed Dose", 250.0, "mcg")], [],
            )
            app.refresh_patient_protocols_table()
            await pilot.pause()

            app.action_switch_tab("patient-tab")
            await pilot.pause()

            table = app.query_one("#patient-protocols-table", DataTable)
            table.move_cursor(row=0, column=0)
            await pilot.pause()

            app.generate_titration_for_selected_protocol()
            await pilot.pause()

            cancel_btn = app.screen.query_one("#titration-cancel-btn", Button)
            cancel_btn.press()
            await pilot.pause()

            protocols = db.get_user_protocols(pid)
            saved = next(p for p in protocols if p["peptide_name"] == "BPC-157")
            assert saved["target_dose"] == 250.0

    asyncio.run(run())


def test_prefill_converts_schedule_step_unit_to_protocol_unit(tmp_path, monkeypatch):
    """A schedule step carries its own unit, which can differ from the
    protocol's dose_unit -- prefilling the raw value would be off by 1000x."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = app.active_profile_id
            # protocol dosed in mcg, but its first schedule step is written in mg
            db.add_or_update_user_protocol(
                pid, "UnitMismatch", 5.0, 2.0, 2000.0, "mcg", "daily", "n",
                [("Week 1", 1.0, "mg")], [],
            )
            app.refresh_patient_protocols_table()
            app.action_switch_tab("patient-tab")
            await pilot.pause()

            table = app.query_one("#patient-protocols-table", DataTable)
            row = next(r for r in range(table.row_count)
                       if table.get_cell_at((r, 1)) == "UnitMismatch")
            table.move_cursor(row=row)
            await pilot.pause()

            app.generate_titration_for_selected_protocol()
            await pilot.pause()
            assert isinstance(app.screen, TitrationGeneratorScreen)

            # 1.0 mg expressed in the protocol's mcg unit
            assert float(app.screen.query_one("#titration-start-input", Input).value) == 1000.0
            app.screen.action_cancel()
            await pilot.pause()

    asyncio.run(run())
