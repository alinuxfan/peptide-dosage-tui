import asyncio

from textual.widgets import Button, DataTable

import db
from main import ConfirmScreen, PeptideCalculatorApp


def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))


def _column_labels(table):
    return [str(col.label) for col in table.columns.values()]


def test_mark_reconstituted_starts_bud_and_shows_in_patient_table(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = app.active_profile_id
            db.add_or_update_user_protocol(
                pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "n", [], []
            )
            app.refresh_patient_protocols_table()
            app.action_switch_tab("patient-tab")
            await pilot.pause()

            table = app.query_one("#patient-protocols-table", DataTable)
            labels = _column_labels(table)
            bud_col = labels.index("Vial BUD / Expiry")
            vial_col = labels.index("Doses Left")

            table.move_cursor(row=0)
            await pilot.pause()
            assert table.get_cell_at((0, bud_col)) == "Not reconstituted"

            app.mark_selected_protocol_reconstituted()
            await pilot.pause()
            assert isinstance(app.screen, ConfirmScreen)
            app.screen.query_one("#confirm-yes", Button).press()
            await pilot.pause()

            assert "Fresh" in table.get_cell_at((0, bud_col))
            assert "20.0" in table.get_cell_at((0, vial_col))

            protocol = db.get_user_protocols(pid)[0]
            assert protocol["reconstituted_at"] is not None

    asyncio.run(run())


def test_mark_reconstituted_cancel_leaves_protocol_untouched(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = app.active_profile_id
            db.add_or_update_user_protocol(
                pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "n", [], []
            )
            app.refresh_patient_protocols_table()
            app.action_switch_tab("patient-tab")
            await pilot.pause()

            app.query_one("#patient-protocols-table", DataTable).move_cursor(row=0)
            await pilot.pause()
            app.mark_selected_protocol_reconstituted()
            await pilot.pause()
            app.screen.query_one("#confirm-no", Button).press()
            await pilot.pause()

            assert db.get_user_protocols(pid)[0]["reconstituted_at"] is None

    asyncio.run(run())


def test_adherence_table_shows_inventory_and_reason_for_unmeasurable(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            pid = app.active_profile_id
            db.add_or_update_user_protocol(
                pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "n", [], []
            )
            protocol_id = db.get_user_protocols(pid)[0]["id"]
            db.set_protocol_reconstituted(protocol_id, when="2026-01-01 08:00:00")
            db.log_dose(pid, protocol_id, "BPC-157", 250.0, "mcg", taken_at="2026-01-02 08:00:00")
            app.refresh_dose_log_tables()
            await pilot.pause()

            table = app.query_one("#adherence-table", DataTable)
            labels = _column_labels(table)
            row = [table.get_cell_at((0, c)) for c in range(len(labels))]
            cells = dict(zip(labels, row))

            # 20 doses per vial, 1 drawn since this vial was reconstituted
            assert "19.0" in cells["Doses Left"]
            # brand-new protocol -> says *why* adherence is unmeasurable
            assert cells["Adherence"] == "Too new"
            # reconstituted 2026-01-01 with a 28-day BUD -> long expired by now
            assert "Expired" in cells["Vial BUD / Expiry"]

    asyncio.run(run())
