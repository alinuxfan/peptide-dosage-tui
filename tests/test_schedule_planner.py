import asyncio
import os
import pytest
from textual.widgets import Select, Label, DataTable, TabbedContent

import db
from main import PeptideCalculatorApp


def test_schedule_planner_lists_all_peptides_for_adam(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            # Switch active profile to Adam (id=4)
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            sched_select = app.query_one("#schedule-protocol-select", Select)
            options = [val for _, val in sched_select._options if isinstance(val, str)]
            assert "__all__" in options

            # Verify all 6 of Adam's protocols are present in the dropdown options
            protocol_options = [val for val in options if val.startswith("protocol_")]
            assert len(protocol_options) == 6

            # Check metadata banner identifies Adam and indicates multi-peptide view
            banner = app.query_one("#schedule-banner-text", Label)
            assert "All 6 Peptides for Adam" in str(banner.render())

            # Check that table lists all of Adam's peptides
            table = app.query_one("#schedule-table", DataTable)
            assert table.row_count >= 6
            peptides_in_table = {table.get_cell_at((r, 0)) for r in range(table.row_count)}
            expected = {"GLOW Blend", "Retatrutide", "Selank", "Semax", "Sermorelin", "NAD+"}
            assert expected <= peptides_in_table

    asyncio.run(run())


def test_schedule_planner_accurate_reconstitution_and_banner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            sched_select = app.query_one("#schedule-protocol-select", Select)
            banner = app.query_one("#schedule-banner-text", Label)
            table = app.query_one("#schedule-table", DataTable)

            # Select GLOW Blend (50mg / 3.0mL -> 16.67 mg/mL, target 1.5mg)
            glow_opt = next(val for _, val in sched_select._options if isinstance(val, str) and "GLOW Blend" in _)
            sched_select.value = glow_opt
            await pilot.pause()

            banner_text = str(banner.render())
            assert "GLOW Blend (Adam)" in banner_text
            assert "50.0 mg" in banner_text
            assert "3.0 mL" in banner_text
            assert "16.67 mg/mL" in banner_text

            # Verify exact draw volume and syringe units for GLOW Blend:
            # 1.5 mg / (50/3 mg/mL) = 0.090 mL = 9.0 Units
            assert table.get_cell_at((0, 2)) == "0.090 mL"
            assert table.get_cell_at((0, 3)) == "9.0 Units"

    asyncio.run(run())


def test_schedule_planner_syringe_draw_safety_warning(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            sched_select = app.query_one("#schedule-protocol-select", Select)
            table = app.query_one("#schedule-table", DataTable)

            # Select Retatrutide (5mg / 2.0mL, titration steps: 2mg, 4mg, 8mg, 12mg)
            ret_opt = next(val for _, val in sched_select._options if val == "catalog_Retatrutide")
            sched_select.value = ret_opt
            await pilot.pause()

            assert table.row_count == 4
            # 8mg dose requires 3.200 mL = 320.0 Units -> exceeds 100U capacity
            draw_8mg = table.get_cell_at((2, 3))
            safety_8mg = table.get_cell_at((2, 6))
            assert "⚠️" in draw_8mg
            assert "Exceeds 100U" in safety_8mg

    asyncio.run(run())


def test_schedule_planner_file_export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            sched_select = app.query_one("#schedule-protocol-select", Select)

            # Export all peptides
            sched_select.value = "__all__"
            await pilot.pause()
            app.save_schedule_to_file()
            assert os.path.exists("schedule_adam_all_peptides.txt")
            with open("schedule_adam_all_peptides.txt") as f:
                content = f.read()
                assert "COMPLETE PATIENT DOSING SCHEDULE" in content
                assert "ADAM" in content
                assert "GLOW BLEND" in content
                assert "RETATRUTIDE" in content
                assert "NAD+" in content

            # Export single peptide
            glow_opt = next(val for _, val in sched_select._options if isinstance(val, str) and "GLOW Blend" in _)
            sched_select.value = glow_opt
            await pilot.pause()
            app.save_schedule_to_file()
            assert os.path.exists("schedule_adam_glow_blend.txt")
            with open("schedule_adam_glow_blend.txt") as f:
                content = f.read()
                assert "GLOW BLEND" in content
                assert "16.67 mg/mL" in content
                assert "9.0 Units" in content

    asyncio.run(run())


def test_view_schedule_button_switches_to_protocol(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            app.active_profile_id = 4
            app.refresh_active_profile_display()
            await pilot.pause()

            tabbed = app.query_one(TabbedContent)
            tabbed.active = "patient-tab"
            patient_table = app.query_one("#patient-protocols-table", DataTable)
            patient_table.move_cursor(row=0, column=0)

            app.view_selected_protocol_schedule()
            await pilot.pause()

            assert tabbed.active == "schedule-tab"
            sched_select = app.query_one("#schedule-protocol-select", Select)
            assert str(sched_select.value).startswith("protocol_")

    asyncio.run(run())
