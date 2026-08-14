# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Terminal User Interface (TUI) built with Python + Textual + SQLite for calculating peptide reconstitution dilutions, U-100 insulin syringe draws, titration schedules, multi-person patient protocol tracking, and dose-history/adherence logging, with PubMed literature citations. Research/educational tool — not medical advice (see README disclaimer).

## Commands

Uses `uv` for dependency management (Python >=3.13; runtime dependency: `textual`; dev dependency: `pytest`).

```bash
uv run python main.py     # Run the TUI application
uv run peptide-tui         # Same, via the installed console-script entry point
python main.py             # Run directly if venv is already active

python db.py                # Initialize/verify the SQLite schema standalone (creates peptides.db, prints confirmation)

uv run pytest               # Run the test suite (tests/test_calc.py, tests/test_db.py)
uv run pytest tests/test_calc.py -k test_bpc157_known_good_numbers  # Run a single test
```

There is no linter configured in this repo.

## Architecture

- **`main.py`** — `PeptideCalculatorApp(App)`, a single Textual `App` subclass containing all UI composition, CSS-in-Python styling, and event handlers, plus a `ConfirmScreen(ModalScreen[bool])` for destructive-action confirmation. Five tabs inside one `TabbedContent` (each `TabPane` has an explicit `id` — `calc-tab`, `patient-tab`, `schedule-tab`, `dose-log-tab`, `reference-tab` — used for programmatic tab switching):
  1. **Calculator & Syringe Visualizer** (`calc-tab`) — dilution math + ASCII syringe gauge (`make_syringe_display`), driven by reactive attributes.
  2. **Patient Tracker (Multi-Person)** (`patient-tab`) — profile switcher (add/remove) + `DataTable` of a patient's saved protocols, with edit-selected, log-dose, and delete-selected actions.
  3. **Dosing Schedule Planner** (`schedule-tab`) — multi-phase titration table for the currently selected peptide, exportable to a text file.
  4. **Dose Log** (`dose-log-tab`) — adherence summary table + raw chronological dose-log table for the active profile, with delete-entry.
  5. **Peptide Reference & Cited Sources** (`reference-tab`) — read-only Rich/Static rendering of the master peptide database and PubMed citations.

- **`db.py`** — all persistence. Owns `DEFAULT_PEPTIDES` (the seed data: vial size, water volume, target dose, titration schedule, PubMed sources per peptide) and every SQLite read/write function. `init_db()` creates four tables (`profiles`, `peptides`, `user_protocols`, `dose_log`), runs idempotent migrations (an ALTER-TABLE-guarded `created_at` column add, a one-time peptide-name rename fix), and seeds master peptides via `INSERT OR IGNORE` on every startup — `main.py` calls `db.init_db()` at the top of `compose()`. `schedule` and `sources` are stored as JSON text columns and (de)serialized in Python; call sites work with them as native lists/dicts. Foreign keys are enforced (`PRAGMA foreign_keys = ON` in `get_connection()`), so deleting a profile cascades to its protocols and dose log.

- **`calc.py`** — pure functions, no I/O. The single source of truth for dosing math (`concentration_mg_ml`, `dose_to_mg`, `draw_volume_ml`, `syringe_units`, `doses_per_vial`) shared by `main.py`'s live calculator/schedule views and `db.py`'s file export — do not reinline this formula elsewhere. Also owns the adherence heuristic (`parse_weekly_frequency`, `adherence_percent`) used by `db.get_protocol_adherence`.

### Data flow / state model

- Core UI state lives in Textual `reactive` attributes on the App (`active_profile_id`, `peptide`, `vial_mg`, `water_ml`, `target_dose`, `dose_unit`). Changing an `Input`/`Select` updates the matching reactive, then handlers explicitly call `self.recalculate()` and `self.update_schedule_table()` — there's no automatic reactive-to-reactive derivation, so any new input field must call these itself.
- `watch_active_profile_id` re-renders the active-profile label, patient table, and dose-log tables whenever the profile changes.
- "Master" peptide templates (`db.peptides` table) are the read-only catalog; "Quick Add" or "Save Protocol" copies a template's values into a per-profile row in `user_protocols`, which is what the Patient Tracker tab and file exports actually read. Editing a template does not retroactively change already-saved patient protocols.
- `user_protocols` tracks the *planned* protocol; `dose_log` tracks *actual* logged doses (denormalized `peptide_name` snapshot, so history survives protocol edits/deletes). Adherence % is a best-effort heuristic (`calc.parse_weekly_frequency` regex-parses free-text frequency strings like `"3x weekly"`) — unparseable frequencies report `None`/`"N/A"` rather than guessing.
- File exports (`db.export_person_reference_sheet`, `save_schedule_to_file` in `main.py`) write plain-text `.txt` reports to the current working directory, not a fixed output folder. The patient summary export includes a trailing "Recent Dose Log" section.
- `Select.set_options()` always resets the widget's selection to blank — `refresh_peptide_templates()` explicitly restores a sensible value afterward. Any new code that calls `set_options()` on a `Select` needs the same treatment or the dropdown silently goes blank.
- Destructive actions (delete protocol/profile/dose-log-entry) route through `ConfirmScreen` via `self.push_screen(ConfirmScreen("..."), callback)` — reuse this pattern for future destructive actions rather than deleting on a single click.
- Programmatically switching `TabbedContent.active` right after a click also moves focus (e.g. `load_selected_protocol_for_edit` calls `self.set_focus(...)` after switching tabs) — `TabPane._on_descendant_focus` re-syncs `active` to whichever tab contains the currently-focused widget, so a stale-focused button in the old tab can silently revert the switch on the next message cycle if focus isn't also moved.

### Adding a new peptide

Add an entry to `DEFAULT_PEPTIDES` in `db.py` (vial_mg, water_ml, dose, unit, freq, notes, schedule tuples, PubMed sources) — it will be picked up by `INSERT OR IGNORE` on next run without a migration. Existing `peptides.db` files won't retroactively update an already-seeded row with the same name; delete/edit the row or the `.db` file if template values need correcting after seeding.
