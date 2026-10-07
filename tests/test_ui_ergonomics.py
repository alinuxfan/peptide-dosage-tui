import asyncio
from textual.widgets import DataTable, Label, Select, TabbedContent
from textual.containers import ScrollableContainer
from main import PeptideCalculatorApp, LogDoseScreen
import db


def test_ambient_status_chips_and_empty_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            chips = app.query_one("#global-status-chips", Label)
            empty_banner = app.query_one("#patient-empty-state-banner", Label)

            # Initially fresh DB has 0 protocols for Default User
            assert empty_banner.display is True
            assert "No active protocols" in str(empty_banner.content)
            assert "0 Protocol(s)" in str(chips.content)

            # Add a protocol
            pid = app.active_profile_id
            db.add_or_update_user_protocol(
                pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "n", [], []
            )
            app.refresh_active_profile_display()
            await pilot.pause()

            # Now banner is hidden and chips show 1 protocol
            assert empty_banner.display is False
            assert "1 Protocol(s)" in str(chips.content)

    asyncio.run(run())


def test_hero_card_and_edit_banner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Hero draw and safety badge
            draw_lbl = app.query_one("#calc-syringe-draw", Label)
            safety_lbl = app.query_one("#calc-safety-badge", Label)
            assert "Units" in str(draw_lbl.content)
            assert "✓" in str(safety_lbl.content) or "⚠️" in str(safety_lbl.content)

            # Add protocol to test edit flow
            pid = app.active_profile_id
            db.add_or_update_user_protocol(
                pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "n", [], []
            )
            app.refresh_patient_protocols_table()
            app.action_switch_tab("patient-tab")
            await pilot.pause()

            table = app.query_one("#patient-protocols-table", DataTable)
            table.move_cursor(row=0)
            await pilot.pause()
            app.load_selected_protocol_for_edit()
            await pilot.pause()

            edit_banner = app.query_one("#calc-edit-mode-banner", Label)
            assert "Editing Protocol" in str(edit_banner.content)

            # Switching template to a different peptide clears the edit banner
            app.query_one("#peptide-select", Select).value = "Semaglutide"
            await pilot.pause()
            assert str(edit_banner.content) == ""

    asyncio.run(run())


def test_table_keyboard_hotkeys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Seed a protocol
            pid = app.active_profile_id
            db.add_or_update_user_protocol(
                pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "n", [], []
            )
            app.refresh_patient_protocols_table()

            app.action_switch_tab("patient-tab")
            await pilot.pause()
            table = app.query_one("#patient-protocols-table", DataTable)
            app.set_focus(table)
            table.move_cursor(row=0)
            await pilot.pause()

            # Press 'l' to log dose
            await pilot.press("l")
            await pilot.pause()
            assert isinstance(app.screen, LogDoseScreen)
            app.screen.action_cancel()
            await pilot.pause()
            assert not isinstance(app.screen, LogDoseScreen)

            # Press 't' to view schedule
            await pilot.press("t")
            await pilot.pause()
            tabbed = app.query_one(TabbedContent)
            assert tabbed.active == "schedule-tab"

    asyncio.run(run())


def test_adherence_progress_bar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            app.action_switch_tab("dose-log-tab")
            await pilot.pause()

            prog_lbl = app.query_one("#adherence-progress-bar", Label)
            assert "Overall Adherence:" in str(prog_lbl.content)

    asyncio.run(run())


def test_tab_visibility_and_reference_tab_population(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            # Active tab should have text visible (height > 0)
            calc_tab = app.query_one("#--content-tab-calc-tab")
            assert "-active" in calc_tab.classes
            assert calc_tab.size.height > 0

            # Switch to Peptide Reference Tab
            app.action_switch_tab("reference-tab")
            await pilot.pause()

            ref_tab = app.query_one("#--content-tab-reference-tab")
            assert "-active" in ref_tab.classes
            assert ref_tab.size.height > 0

            # Reference tab should display all reference sections with height > 0 without needing search
            container = app.query_one("#reference-scroll-container", ScrollableContainer)
            assert len(container.children) > 0
            # Virtual size should accommodate all reference cards
            assert container.virtual_size.height > 500
            for sec in container.children[:5]:
                assert sec.size.height > 0

    asyncio.run(run())
