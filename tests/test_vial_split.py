import asyncio

from textual.widgets import Button, Input, Label, Select, Static

import db
from main import PeptideCalculatorApp, VialSplitScreen


def test_split_vial_button_opens_modal_with_correct_math(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            app.query_one("#vial-size-input", Input).value = "10.0"
            app.query_one("#water-input", Input).value = "2.0"
            app.query_one("#dose-input", Input).value = "250.0"
            app.query_one("#dose-unit-select", Select).value = "mcg"
            app.vial_mg = 10.0
            app.water_ml = 2.0
            app.target_dose = 250.0
            app.dose_unit = "mcg"
            await pilot.pause()

            app.open_vial_split_calculator()
            await pilot.pause()
            assert isinstance(app.screen, VialSplitScreen)

            app.screen.query_one("#split-count-input", Input).value = "4"
            app.screen.regenerate_results()
            await pilot.pause()

            results = str(app.screen.query_one("#split-results", Static).content)
            # 10mg / 2mL split 4 ways -> 2.5mg / 0.5mL per aliquot, same 5.0 mg/mL concentration
            assert "2.50 mg / 0.50 mL" in results
            assert "5.00 mg/mL" in results
            # 250mcg dose at 5.0 mg/mL -> 0.05 mL draw, unchanged by splitting
            assert "0.050 mL" in results

            close_btn = app.screen.query_one("#split-close-btn", Button)
            close_btn.press()
            await pilot.pause()
            assert not isinstance(app.screen, VialSplitScreen)

    asyncio.run(run())


def test_split_vial_invalid_count_shows_status_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_peptides.db"))

    async def run():
        app = PeptideCalculatorApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            app.vial_mg = 10.0
            app.water_ml = 2.0
            app.target_dose = 250.0
            app.dose_unit = "mcg"

            app.open_vial_split_calculator()
            await pilot.pause()

            app.screen.query_one("#split-count-input", Input).value = "0"
            app.screen.regenerate_results()
            await pilot.pause()

            status = str(app.screen.query_one("#split-status", Label).content)
            assert "at least 1" in status
            results = str(app.screen.query_one("#split-results", Static).content)
            assert results == ""

    asyncio.run(run())
