import asyncio
import pytest
from textual.widgets import Footer, TabbedContent
from textual.widgets._footer import FooterKey

from main import PeptideCalculatorApp, HelpScreen, LogDoseScreen


def test_footer_displays_keyboard_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            footer = app.query_one(Footer)
            keys = {}
            for child in footer.walk_children():
                if isinstance(child, FooterKey):
                    keys[child.key_display] = child.description

            # Verify visible keyboard shortcuts across the bottom footer
            assert "1" in keys and keys["1"] == "Calc"
            assert "2" in keys and keys["2"] == "Patients"
            assert "3" in keys and keys["3"] == "Schedule"
            assert "4" in keys and keys["4"] == "Dose Log"
            assert "5" in keys and keys["5"] == "Ref"
            assert "^p" in keys and keys["^p"] == "Next Person"
            assert "^s" in keys and keys["^s"] == "Save Schedule"
            assert "^l" in keys and keys["^l"] == "Log Dose"
            assert "?" in keys and keys["?"] == "Help"
            assert "^q" in keys and keys["^q"] == "Quit"

    asyncio.run(run())


def test_keyboard_tab_switching_and_focus(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            tabbed = app.query_one(TabbedContent)
            assert tabbed.active == "calc-tab"

            # Switch through tabs via actions
            app.action_switch_tab("patient-tab")
            await pilot.pause()
            assert tabbed.active == "patient-tab"

            app.action_switch_tab("schedule-tab")
            await pilot.pause()
            assert tabbed.active == "schedule-tab"

            app.action_switch_tab("dose-log-tab")
            await pilot.pause()
            assert tabbed.active == "dose-log-tab"

            app.action_switch_tab("reference-tab")
            await pilot.pause()
            assert tabbed.active == "reference-tab"

            app.action_switch_tab("calc-tab")
            await pilot.pause()
            assert tabbed.active == "calc-tab"

    asyncio.run(run())


def test_keyboard_cycle_profile_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            init_id = app.active_profile_id
            app.action_next_profile()
            await pilot.pause()
            assert app.active_profile_id != init_id

            # Cycle again to ensure it loops
            app.action_next_profile()
            await pilot.pause()
            assert app.active_profile_id == init_id

    asyncio.run(run())


def test_help_modal_screen_open_and_dismiss(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Open HelpScreen
            app.action_show_help()
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)

            # Dismiss HelpScreen
            app.screen.action_dismiss_help()
            await pilot.pause()
            assert not isinstance(app.screen, HelpScreen)

    asyncio.run(run())


def test_quick_log_dose_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            # Trigger quick log dose shortcut
            app.action_quick_log_dose()
            await pilot.pause()
            assert isinstance(app.screen, LogDoseScreen)

            app.screen.action_cancel()
            await pilot.pause()
            assert not isinstance(app.screen, LogDoseScreen)

    asyncio.run(run())


def test_quick_log_dose_logs_selected_peptide_on_calc_tab(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        from textual.widgets import Select
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            # Select Retatrutide in calculator
            peptide_select = app.query_one("#peptide-select", Select)
            peptide_select.value = "Retatrutide"
            await pilot.pause()

            # Trigger quick log dose shortcut
            app.action_quick_log_dose()
            await pilot.pause()
            assert isinstance(app.screen, LogDoseScreen)
            # Must log the selected peptide (Retatrutide), NOT Semax!
            assert "Retatrutide" in app.screen.message
            assert "Semax" not in app.screen.message

            app.screen.action_cancel()
            await pilot.pause()

    asyncio.run(run())


def test_quick_log_dose_logs_selected_protocol_on_schedule_tab(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        from textual.widgets import Select
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            app.action_switch_tab("schedule-tab")
            await pilot.pause()

            sched_select = app.query_one("#schedule-protocol-select", Select)
            glow_opt = next(val for _, val in sched_select._options if isinstance(val, str) and "GLOW Blend" in _)
            sched_select.value = glow_opt
            await pilot.pause()

            app.action_quick_log_dose()
            await pilot.pause()
            assert isinstance(app.screen, LogDoseScreen)
            assert "GLOW Blend" in app.screen.message
            assert "Semax" not in app.screen.message

            app.screen.action_cancel()
            await pilot.pause()

    asyncio.run(run())


def test_quick_log_dose_logs_selected_row_on_patient_tab(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        from textual.widgets import DataTable
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            app.action_switch_tab("patient-tab")
            await pilot.pause()

            table = app.query_one("#patient-protocols-table", DataTable)
            # Find row index for Retatrutide or Selank
            target_row = 1
            expected_pep = table.get_cell_at((target_row, 1))
            table.move_cursor(row=target_row)
            await pilot.pause()

            app.action_quick_log_dose()
            await pilot.pause()
            assert isinstance(app.screen, LogDoseScreen)
            assert expected_pep in app.screen.message

            app.screen.action_cancel()
            await pilot.pause()

    asyncio.run(run())
