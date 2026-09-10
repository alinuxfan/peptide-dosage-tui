import os
import sys
from datetime import datetime, timezone
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Header,
    Footer,
    Input,
    Label,
    Button,
    Select,
    Static,
    DataTable,
    TabbedContent,
    TabPane,
)
from textual.reactive import reactive

import calc
import db

# Compact ASCII syringe drawing helper
def make_syringe_display(units: float) -> str:
    BARREL_WIDTH = 40  # character width of the barrel gauge
    BARREL_START = len("Needle ──┨ ")  # column where the barrel content begins

    if units <= 0:
        filled = 0
    elif units > 100:
        filled = BARREL_WIDTH  # Cap at 100 units visually
    else:
        filled = int(round((units / 100.0) * BARREL_WIDTH))

    empty = BARREL_WIDTH - filled

    stick_len = max(0, filled - 1)
    stick = "=" * stick_len
    rubber = "█" if filled > 0 else ""
    liquid = "░" * max(0, filled - stick_len - 1)
    barrel_content = f"{stick}{rubber}{liquid}{'.' * empty}"

    # Build the ruler so its tick marks line up with the same BARREL_START +
    # units-to-column scale used by the marker below, instead of a fixed
    # string that drifted out of sync with the barrel width.
    ruler_chars = [" "] * BARREL_START
    for label_units in (0, 20, 40, 60, 80, 100):
        pos = BARREL_START + round(label_units / 100.0 * BARREL_WIDTH)
        label = str(label_units)
        if pos + len(label) > len(ruler_chars):
            ruler_chars.extend([" "] * (pos + len(label) - len(ruler_chars)))
        ruler_chars[pos:pos + len(label)] = label
    top_line = "".join(ruler_chars) + " Units"

    mid_line = f"Needle ──┨ {barrel_content} ┠─════ Plunger"

    marker_pos = BARREL_START + filled
    bottom_line = " " * marker_pos + f"▲ {units:.1f}U"
    if units > 100:
        bottom_line += " [!] EXCEEDS 1mL CAPACITY"

    return f"{top_line}\n{mid_line}\n{bottom_line}"


CSS = """
Screen {
    background: #0f172a;
    color: #e2e8f0;
}

Header {
    background: #1e293b;
    color: #38bdf8;
    text-align: center;
    height: 1;
    border-bottom: solid #38bdf8;
}

Footer {
    background: #1e293b;
    color: #94a3b8;
    height: 1;
}

TabbedContent {
    margin-top: 0;
    height: 1fr;
}

TabPane {
    padding: 0;
    height: 1fr;
}

.pane-container {
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 1fr;
    grid-gutter: 1;
    padding: 0 1;
    height: 1fr;
}

.sidebar-panel {
    background: #1e293b;
    border: solid #334155;
    padding: 0 1;
    height: 1fr;
}

.results-panel {
    background: #1e293b;
    border: solid #334155;
    padding: 0 1;
    layout: vertical;
    height: 1fr;
}

.title-label {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 0;
    border-bottom: solid #334155;
}

.input-label {
    text-style: bold;
    margin-top: 1;
    color: #cbd5e1;
}

.preset-row {
    layout: horizontal;
    height: 3;
    margin-bottom: 0;
    margin-top: 0;
}

.preset-row Button {
    margin-right: 1;
    min-width: 6;
    height: 3;
    background: #334155;
    color: #f1f5f9;
}

.preset-row Button:hover {
    background: #475569;
}

Input {
    background: #0f172a;
    border: solid #475569;
    color: #f1f5f9;
    margin-bottom: 0;
    height: 3;
}

Select {
    margin-bottom: 0;
    height: 3;
}

SelectCurrent {
    background: #0f172a;
    border: solid #38bdf8;
    color: #38bdf8;
    text-style: bold;
    height: 3;
}

.result-row {
    layout: horizontal;
    height: 2;
    content-align: left middle;
    border-bottom: solid #334155;
}

.result-label {
    width: 24;
    text-style: bold;
    color: #94a3b8;
}

.result-val {
    color: #f8fafc;
    text-style: bold;
}

#syringe-visual {
    background: #0f172a;
    border: double #38bdf8;
    padding: 0 1;
    margin-top: 0;
    margin-bottom: 0;
    height: 5;
    color: #38bdf8;
}

.help-box {
    background: #1e293b;
    border: solid #334155;
    padding: 0 1;
    margin-top: 0;
    color: #94a3b8;
}

.action-bar {
    layout: horizontal;
    height: 3;
    align: right middle;
    padding: 0 1;
    background: #1e293b;
    border-bottom: solid #334155;
}

.patient-controls-bar {
    layout: vertical;
    padding: 0 1;
    background: #1e293b;
    border-bottom: solid #334155;
    height: 10;
}

.control-row {
    layout: horizontal;
    height: 3;
    align: left middle;
    margin-bottom: 0;
}

#profile-select {
    width: 25;
    margin-right: 1;
}

#patient-add-peptide-select {
    width: 25;
    margin-right: 1;
}

#new-profile-input {
    width: 22;
    margin-right: 1;
}

.action-title {
    color: #38bdf8;
    text-style: bold;
    margin-right: 1;
}

DataTable {
    height: 1fr;
    border: solid #334155;
    background: #0f172a;
    margin: 0 1;
}

.info-pane {
    padding: 1 2;
    height: 100%;
}

.info-section {
    background: #1e293b;
    border: solid #334155;
    padding: 1 2;
    margin-bottom: 1;
    height: auto;
}

.info-title {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 1;
}

.info-text {
    color: #cbd5e1;
    margin-bottom: 1;
    height: auto;
}

.source-link {
    color: #38bdf8;
    margin-left: 2;
    margin-bottom: 1;
    height: auto;
}

#save-profile-protocol-btn {
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    margin-top: 1;
    height: 3;
}

#save-schedule-btn, #export-patient-sheet-btn, #export-dose-log-csv-btn {
    background: #10b981;
    color: #0f172a;
    text-style: bold;
    min-width: 24;
    margin-left: 1;
    height: 3;
}

#add-profile-btn, #quick-add-peptide-btn {
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}

#delete-protocol-btn, #remove-profile-btn, #delete-log-btn {
    background: #f43f5e;
    color: #ffffff;
    text-style: bold;
    min-width: 18;
    margin-left: 1;
    height: 3;
}

#edit-protocol-btn, #log-dose-btn {
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}

#adherence-table {
    height: 10;
    margin: 0 1;
}
"""

CONFIRM_CSS = """
ConfirmScreen {
    align: center middle;
}

#confirm-dialog {
    width: 60;
    height: auto;
    background: #1e293b;
    border: solid #f43f5e;
    padding: 1 2;
}

#confirm-message {
    color: #f1f5f9;
    margin-bottom: 1;
    height: auto;
}

#confirm-buttons {
    layout: horizontal;
    height: 3;
    align: right middle;
}

#confirm-buttons Button {
    margin-left: 1;
    min-width: 10;
}

#confirm-yes {
    background: #f43f5e;
    color: #ffffff;
}

#confirm-no {
    background: #334155;
    color: #f1f5f9;
}
"""

LOG_DOSE_CSS = """
LogDoseScreen {
    align: center middle;
}

#logdose-dialog {
    width: 60;
    height: auto;
    background: #1e293b;
    border: solid #38bdf8;
    padding: 1 2;
}

#logdose-message {
    color: #f1f5f9;
    margin-bottom: 1;
    height: auto;
}

#logdose-notes {
    margin-bottom: 1;
}

#logdose-buttons {
    layout: horizontal;
    height: 3;
    align: right middle;
}

#logdose-buttons Button {
    margin-left: 1;
    min-width: 10;
}

#logdose-yes {
    background: #38bdf8;
    color: #0f172a;
}

#logdose-no {
    background: #334155;
    color: #f1f5f9;
}
"""


class ConfirmScreen(ModalScreen[bool]):
    """A simple Yes/No confirmation modal. Dismisses with True (confirmed) or False (cancelled)."""

    CSS = CONFIRM_CSS
    BINDINGS = [Binding("escape", "cancel", show=False)]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel", id="confirm-no")
                yield Button("Confirm", id="confirm-yes")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "confirm-yes")

    def action_cancel(self) -> None:
        self.dismiss(False)


class LogDoseScreen(ModalScreen[str | None]):
    """Prompts for optional notes (injection site, side effects, etc.) when logging
    a dose. Dismisses with the entered notes string on confirm, or None on cancel."""

    CSS = LOG_DOSE_CSS
    BINDINGS = [Binding("escape", "cancel", show=False)]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="logdose-dialog"):
            yield Label(self.message, id="logdose-message")
            yield Input(placeholder="Notes (injection site, side effects, etc.) - optional", id="logdose-notes")
            with Horizontal(id="logdose-buttons"):
                yield Button("Cancel", id="logdose-no")
                yield Button("Log Dose", id="logdose-yes")

    def on_mount(self) -> None:
        self.query_one("#logdose-notes", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "logdose-yes":
            self.dismiss(self.query_one("#logdose-notes", Input).value.strip())
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.dismiss(event.value.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


class PeptideCalculatorApp(App):
    TITLE = "Peptide Dosage & Reconstitution TUI"
    SUB_TITLE = "Multi-Person Protocol Tracker with Scientific Citations"
    CSS = CSS

    active_profile_id = reactive(1)
    peptide = reactive("Custom / Other")
    vial_mg = reactive(5.0)
    water_ml = reactive(2.0)
    target_dose = reactive(250.0)
    dose_unit = reactive("mcg")

    def compose(self) -> ComposeResult:
        db.init_db()
        yield Header()
        with TabbedContent():
            with TabPane("Calculator & Syringe Visualizer", id="calc-tab"):
                with Grid(classes="pane-container"):
                    # Left Sidebar: Inputs in Scrollable Container
                    with ScrollableContainer(classes="sidebar-panel"):
                        yield Label("PEPTIDE CONFIGURATION", classes="title-label")
                        
                        yield Label("Select Peptide Template:", classes="input-label")
                        yield Select(
                            options=[("Custom / Other", "Custom / Other")],
                            value="Custom / Other",
                            id="peptide-select"
                        )
                        
                        yield Label("Vial Size (mg of peptide):", classes="input-label")
                        with Horizontal(classes="preset-row"):
                            yield Button("5mg", id="vial-btn-5")
                            yield Button("10mg", id="vial-btn-10")
                            yield Button("25mg", id="vial-btn-25")
                            yield Button("30mg", id="vial-btn-30")
                            yield Button("50mg", id="vial-btn-50")
                            yield Button("60mg", id="vial-btn-60")
                        yield Input(value="5.0", placeholder="Enter mg...", id="vial-size-input")
                        
                        yield Label("Bacteriostatic Water (mL added):", classes="input-label")
                        with Horizontal(classes="preset-row"):
                            yield Button("1mL", id="water-btn-1")
                            yield Button("2mL", id="water-btn-2")
                            yield Button("2.5mL", id="water-btn-2_5")
                            yield Button("3mL", id="water-btn-3")
                        yield Input(value="2.0", placeholder="Enter mL...", id="water-input")
                        yield Label(
                            "GLP-1/2/3: 2mL-3mL | Peptides: 3mL\n"
                            "Higher water = lower conc, making small doses easier to draw.",
                            classes="help-box"
                        )
                        
                        yield Label("Target Dose Amount:", classes="input-label")
                        yield Input(value="250.0", placeholder="Enter target dose...", id="dose-input")
                        yield Label("Target Dose Unit:", classes="input-label")
                        yield Select(
                            options=[("mcg", "mcg"), ("mg", "mg")],
                            value="mcg",
                            id="dose-unit-select"
                        )
                        
                        yield Button("💾 Save Protocol to Active Profile", id="save-profile-protocol-btn")

                    # Right Panel: Output & Visualizer in Scrollable Container
                    with ScrollableContainer(classes="results-panel"):
                        yield Label("DILUTION & CALCULATED DOSES", classes="title-label")
                        
                        with Horizontal(classes="result-row"):
                            yield Label("Active Profile:", classes="result-label")
                            yield Label("Default User", id="calc-active-profile", classes="result-val highlight-val")

                        with Horizontal(classes="result-row"):
                            yield Label("Solution Concentration:", classes="result-label")
                            yield Label("Enter valid inputs...", id="calc-concentration", classes="result-val")
                            
                        with Horizontal(classes="result-row"):
                            yield Label("Single Dose Volume (mL):", classes="result-label")
                            yield Label("Enter valid inputs...", id="calc-dose-volume", classes="result-val")
                            
                        with Horizontal(classes="result-row"):
                            yield Label("U-100 Syringe Draw:", classes="result-label")
                            yield Label("Enter valid inputs...", id="calc-syringe-draw", classes="result-val highlight-val")
                            
                        with Horizontal(classes="result-row"):
                            yield Label("Total Doses per Vial:", classes="result-label")
                            yield Label("Enter valid inputs...", id="calc-doses-per-vial", classes="result-val")
                        
                        yield Label("INSULIN SYRINGE DRAW VISUALIZER (U-100 Syringe)", classes="title-label")
                        yield Label("  Syringe representation will appear here when inputs are valid.", id="syringe-visual")

            with TabPane("Patient Tracker (Multi-Person)", id="patient-tab"):
                with Vertical():
                    with Container(classes="patient-controls-bar"):
                        with Horizontal(classes="control-row"):
                            yield Label("Active Person Profile:", classes="action-title")
                            yield Select(options=[("Default User", "1")], value="1", id="profile-select")
                            yield Input(placeholder="New person name...", id="new-profile-input")
                            yield Button("+ Add Person", id="add-profile-btn")
                            yield Button("❌ Remove Person", id="remove-profile-btn")
                        with Horizontal(classes="control-row"):
                            yield Label("Quick Add Peptide:", classes="action-title")
                            yield Select(options=[("BPC-157", "BPC-157")], value="BPC-157", id="patient-add-peptide-select")
                            yield Button("+ Add to Person", id="quick-add-peptide-btn")
                            yield Button("🖨️ Export Printable Sheet", id="export-patient-sheet-btn")
                            yield Button("❌ Remove Selected", id="delete-protocol-btn")
                        with Horizontal(classes="control-row"):
                            yield Button("✏️ Edit Selected", id="edit-protocol-btn")
                            yield Button("💊 Log Dose Taken", id="log-dose-btn")
                    yield DataTable(id="patient-protocols-table")

            with TabPane("Dosing Schedule Planner", id="schedule-tab"):
                with Vertical():
                    with Container(classes="action-bar"):
                        yield Label("Peptide Titration Schedule Planner & Exporter", classes="action-title")
                        yield Button("Save Schedule to File", id="save-schedule-btn")
                    yield DataTable(id="schedule-table")

            with TabPane("Dose Log", id="dose-log-tab"):
                with Vertical():
                    with Container(classes="action-bar"):
                        yield Label("Dose History & Adherence (Active Profile)", classes="action-title")
                        yield Button("📄 Export CSV", id="export-dose-log-csv-btn")
                        yield Button("🗑️ Delete Entry", id="delete-log-btn")
                    yield Label("Adherence Summary", classes="title-label")
                    yield DataTable(id="adherence-table")
                    yield Label("Recent Dose Log", classes="title-label")
                    yield DataTable(id="dose-log-table")

            with TabPane("Peptide Reference & Cited Sources", id="reference-tab"):
                with Vertical():
                    with Container(classes="action-bar"):
                        yield Label("Search Peptide Reference:", classes="action-title")
                        yield Input(placeholder="Filter by name or notes (e.g. GLP-1, weight loss, sleep)...", id="reference-search-input")
                    with ScrollableContainer(classes="info-pane", id="reference-scroll-container"):
                        yield Label("Loading reference database...", classes="info-title")
        yield Footer()

    def on_mount(self) -> None:
        sched_table = self.query_one("#schedule-table", DataTable)
        sched_table.add_columns("Phase / Week", "Dose", "Volume (mL)", "Syringe Draw (Units)", "Est. Doses per Vial")
        
        patient_table = self.query_one("#patient-protocols-table", DataTable)
        patient_table.add_columns("ID", "Peptide Name", "Vial Strength", "BAC Water", "Target Dose", "Syringe Draw", "Frequency", "Next Dose Due", "Last Updated")

        adherence_table = self.query_one("#adherence-table", DataTable)
        adherence_table.add_columns("Peptide", "Frequency", "Doses Logged", "Adherence %", "Next Dose Due")

        dose_log_table = self.query_one("#dose-log-table", DataTable)
        dose_log_table.add_columns("ID", "Peptide", "Dose", "Taken At", "Notes")

        self.refresh_profiles()
        self.refresh_peptide_templates()
        self.refresh_patient_protocols_table()
        self.refresh_dose_log_tables()
        self.populate_reference_tab()
        self.recalculate()

    def refresh_profiles(self) -> None:
        profiles = db.get_profiles()
        if not profiles:
            return
        options = [(p["name"], str(p["id"])) for p in profiles]
        
        profile_select = self.query_one("#profile-select", Select)
        profile_select.set_options(options)
        profile_select.value = str(self.active_profile_id)
        
        self.refresh_active_profile_display()

    def refresh_active_profile_display(self) -> None:
        profiles = db.get_profiles()
        current_prof_name = next((p["name"] for p in profiles if p["id"] == self.active_profile_id), "Unknown")
        try:
            self.query_one("#calc-active-profile", Label).update(current_prof_name)
            prof_select = self.query_one("#profile-select", Select)
            if str(prof_select.value) != str(self.active_profile_id):
                prof_select.value = str(self.active_profile_id)
        except Exception:
            pass
        self.refresh_patient_protocols_table()
        self.refresh_dose_log_tables()

    def refresh_peptide_templates(self) -> None:
        peptides = db.get_peptides()
        options = [(p["name"], p["name"]) for p in peptides]
        names = {p["name"] for p in peptides}

        # Select.set_options() always resets the current selection to blank,
        # so restore a sensible value afterward (previous selection if it
        # still exists, else a fallback) rather than leaving the dropdown empty.
        peptide_select = self.query_one("#peptide-select", Select)
        prior_peptide = peptide_select.value if peptide_select.value != Select.BLANK else self.peptide
        peptide_select.set_options(options)
        peptide_select.value = prior_peptide if prior_peptide in names else "Custom / Other"

        patient_add_select = self.query_one("#patient-add-peptide-select", Select)
        prior_patient_add = patient_add_select.value
        patient_add_select.set_options(options)
        if prior_patient_add in names:
            patient_add_select.value = prior_patient_add
        elif "BPC-157" in names:
            patient_add_select.value = "BPC-157"
        elif names:
            patient_add_select.value = sorted(names)[0]

    def refresh_patient_protocols_table(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        table.clear()

        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, to match db.py's next_due_at
        due_by_protocol_id = {
            entry['protocol_id']: entry['next_due_at']
            for entry in db.get_protocol_adherence(self.active_profile_id)
        }

        protocols = db.get_user_protocols(self.active_profile_id)
        for p in protocols:
            conc = calc.concentration_mg_ml(p['vial_mg'], p['water_ml'])
            dose_mg = calc.dose_to_mg(p['target_dose'], p['dose_unit'])
            vol_ml = calc.draw_volume_ml(dose_mg, conc)
            units = calc.syringe_units(vol_ml)
            due_label = calc.format_due_label(due_by_protocol_id.get(p['id']), now)

            table.add_row(
                str(p['id']),
                p['peptide_name'],
                f"{p['vial_mg']:.1f} mg",
                f"{p['water_ml']:.1f} mL",
                f"{p['target_dose']} {p['dose_unit']}",
                f"{units:.1f} Units",
                p['frequency'],
                due_label,
                p['updated_at'][:10]
            )

    def refresh_dose_log_tables(self) -> None:
        try:
            adherence_table = self.query_one("#adherence-table", DataTable)
            dose_log_table = self.query_one("#dose-log-table", DataTable)
        except Exception:
            return  # tables not mounted yet

        adherence_table.clear()
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, to match db.py's next_due_at
        for entry in db.get_protocol_adherence(self.active_profile_id):
            pct_str = f"{entry['adherence_pct']:.0f}%" if entry['adherence_pct'] is not None else "N/A"
            due_label = calc.format_due_label(entry['next_due_at'], now)
            adherence_table.add_row(
                entry['peptide_name'],
                entry['frequency'] or "-",
                str(entry['logged_count']),
                pct_str,
                due_label,
            )

        dose_log_table.clear()
        for log in db.get_dose_log(self.active_profile_id):
            dose_log_table.add_row(
                str(log['id']),
                log['peptide_name'],
                f"{log['dose_amount']} {log['dose_unit']}",
                log['taken_at'],
                log['notes'] or "",
            )

    def delete_selected_dose_log_entry(self) -> None:
        table = self.query_one("#dose-log-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the dose log to remove.", severity="warning")
            return

        try:
            log_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected log entry.", severity="error")
            return

        def handle_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            db.delete_dose_log_entry(log_id)
            self.refresh_dose_log_tables()
            self.notify("Removed dose log entry.", timeout=3.0)

        self.push_screen(ConfirmScreen("Delete this dose log entry?"), handle_confirm)

    def populate_reference_tab(self, filter_text: str = "") -> None:
        container = self.query_one("#reference-scroll-container", ScrollableContainer)
        container.remove_children()

        peptides = db.get_peptides()
        needle = filter_text.strip().lower()
        if needle:
            peptides = [
                p for p in peptides
                if needle in p['name'].lower() or needle in (p['notes'] or "").lower()
            ]

        if not peptides:
            container.mount(Label(f"No peptides match '{filter_text.strip()}'.", classes="info-title"))
            return

        for p in peptides:
            children = [
                Label(f"🔬 {p['name']} Reference & Clinical Guidelines", classes="info-title"),
                Static(f"• Standard Vial: {p['vial_mg']} mg | Recommended BAC Water: {p['water_ml']} mL\n• Target Dose: {p['dose']} {p['unit']} ({p['freq']})\n• Details: {p['notes']}", classes="info-text")
            ]
            if p['sources']:
                children.append(Label("Scientific Citations & PubMed Literature:", classes="input-label"))
                for s in p['sources']:
                    cite_md = f"  - {s['title']} (PMID: {s['pmid']})\n    URL: {s['url']}"
                    children.append(Static(cite_md, classes="source-link"))
                    
            sec = Vertical(*children, classes="info-section")
            container.mount(sec)

    def watch_active_profile_id(self, old_val: int, new_val: int) -> None:
        self.refresh_active_profile_display()

    def on_select_changed(self, event: Select.Changed) -> None:
        if not event.value or event.value == Select.BLANK:
            return
            
        if event.select.id == "peptide-select":
            self.peptide = str(event.value)
            p = db.get_peptide_by_name(self.peptide)
            if p:
                self.query_one("#vial-size-input", Input).value = f"{p['vial_mg']}"
                self.query_one("#water-input", Input).value = f"{p['water_ml']}"
                self.query_one("#dose-input", Input).value = f"{p['dose']}"
                self.query_one("#dose-unit-select", Select).value = p["unit"]
                
                self.vial_mg = p['vial_mg']
                self.water_ml = p['water_ml']
                self.target_dose = p['dose']
                self.dose_unit = p['unit']
        elif event.select.id == "dose-unit-select":
            self.dose_unit = str(event.value)
        elif event.select.id == "profile-select":
            try:
                val = int(str(event.value))
                if val != self.active_profile_id:
                    self.active_profile_id = val
                    self.refresh_active_profile_display()
            except (ValueError, TypeError):
                pass
            
        self.recalculate()
        self.update_schedule_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "reference-search-input":
            self.populate_reference_tab(event.value)
            return

        try:
            val = float(event.input.value) if event.input.value else 0.0
            if event.input.id == "vial-size-input":
                self.vial_mg = val
            elif event.input.id == "water-input":
                self.water_ml = val
            elif event.input.id == "dose-input":
                self.target_dose = val
        except ValueError:
            pass
            
        self.recalculate()
        self.update_schedule_table()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if not btn_id:
            return
            
        if btn_id.startswith("vial-btn-"):
            val = btn_id.replace("vial-btn-", "")
            self.query_one("#vial-size-input", Input).value = val
            self.vial_mg = float(val)
        elif btn_id.startswith("water-btn-"):
            val = btn_id.replace("water-btn-", "")
            val_clean = val.replace("_", ".")
            self.query_one("#water-input", Input).value = val_clean
            self.water_ml = float(val_clean)
        elif btn_id == "save-profile-protocol-btn":
            self.save_current_to_profile()
        elif btn_id == "quick-add-peptide-btn":
            self.quick_add_peptide_to_patient()
        elif btn_id == "add-profile-btn":
            self.create_new_profile()
        elif btn_id == "export-patient-sheet-btn":
            self.export_patient_sheet()
        elif btn_id == "delete-protocol-btn":
            self.delete_selected_patient_protocol()
        elif btn_id == "remove-profile-btn":
            self.delete_selected_profile()
        elif btn_id == "edit-protocol-btn":
            self.load_selected_protocol_for_edit()
        elif btn_id == "log-dose-btn":
            self.log_selected_protocol_dose()
        elif btn_id == "delete-log-btn":
            self.delete_selected_dose_log_entry()
        elif btn_id == "export-dose-log-csv-btn":
            self.export_dose_log_csv()
        elif btn_id == "save-schedule-btn":
            self.save_schedule_to_file()

        self.recalculate()
        self.update_schedule_table()

    def save_current_to_profile(self) -> None:
        p = db.get_peptide_by_name(self.peptide)
        freq = p["freq"] if p else "daily"
        notes = p["notes"] if p else "User custom calculation"
        sched = p["schedule"] if p else [("Custom", self.target_dose, self.dose_unit)]
        sources = p["sources"] if p else []
        
        db.add_or_update_user_protocol(
            self.active_profile_id,
            self.peptide,
            self.vial_mg,
            self.water_ml,
            self.target_dose,
            self.dose_unit,
            freq,
            notes,
            sched,
            sources
        )
        self.refresh_patient_protocols_table()
        profiles = db.get_profiles()
        prof_name = next((prof["name"] for prof in profiles if prof["id"] == self.active_profile_id), "Person")
        self.notify(f"Saved {self.peptide} protocol to {prof_name}'s list!", timeout=3.0)

    def quick_add_peptide_to_patient(self) -> None:
        select_widget = self.query_one("#patient-add-peptide-select", Select)
        if not select_widget.value or select_widget.value == Select.BLANK:
            self.notify("Please select a peptide template.", severity="warning")
            return
            
        peptide_name = str(select_widget.value)
        p = db.get_peptide_by_name(peptide_name)
        if p:
            db.add_or_update_user_protocol(
                self.active_profile_id,
                p["name"],
                p["vial_mg"],
                p["water_ml"],
                p["dose"],
                p["unit"],
                p["freq"],
                p["notes"],
                p["schedule"],
                p["sources"]
            )
            self.refresh_patient_protocols_table()
            profiles = db.get_profiles()
            prof_name = next((prof["name"] for prof in profiles if prof["id"] == self.active_profile_id), "Person")
            self.notify(f"Added {peptide_name} to {prof_name}'s protocol list!", timeout=3.0)

    def create_new_profile(self) -> None:
        input_widget = self.query_one("#new-profile-input", Input)
        name = input_widget.value.strip()
        if not name:
            self.notify("Please enter a person name.", severity="error")
            return
        prof_id = db.add_profile(name)
        if prof_id:
            input_widget.value = ""
            self.active_profile_id = prof_id
            self.refresh_profiles()
            self.notify(f"Created & selected profile: {name}", timeout=3.0)
        else:
            self.notify("Profile name already exists.", severity="error")

    def export_patient_sheet(self) -> None:
        filename = db.export_person_reference_sheet(self.active_profile_id)
        if filename:
            self.notify(f"Exported patient summary to: {filename}", timeout=4.0)
        else:
            self.notify("Error exporting summary sheet.", severity="error")

    def export_dose_log_csv(self) -> None:
        filename = db.export_dose_log_csv(self.active_profile_id)
        if filename:
            self.notify(f"Exported dose log to: {filename}", timeout=4.0)
        else:
            self.notify("Error exporting dose log.", severity="error")

    def delete_selected_patient_protocol(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the patient table to remove.", severity="warning")
            return

        try:
            protocol_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected protocol.", severity="error")
            return

        def handle_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            db.delete_user_protocol(protocol_id)
            self.refresh_patient_protocols_table()
            self.refresh_dose_log_tables()
            self.notify("Removed protocol from patient profile.", timeout=3.0)

        self.push_screen(ConfirmScreen("Remove this protocol from the patient's list?"), handle_confirm)

    def delete_selected_profile(self) -> None:
        profiles = db.get_profiles()
        if len(profiles) <= 1:
            self.notify("Cannot remove the only remaining profile.", severity="warning")
            return

        profile_id = self.active_profile_id
        prof_name = next((p["name"] for p in profiles if p["id"] == profile_id), "this profile")

        def handle_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            if db.delete_profile(profile_id):
                remaining = db.get_profiles()
                self.active_profile_id = remaining[0]["id"]
                self.refresh_profiles()
                self.refresh_dose_log_tables()
                self.notify(f"Removed profile: {prof_name}", timeout=3.0)
            else:
                self.notify("Cannot remove the only remaining profile.", severity="warning")

        self.push_screen(
            ConfirmScreen(f"Remove person '{prof_name}' and all their saved protocols/dose history? This cannot be undone."),
            handle_confirm,
        )

    def load_selected_protocol_for_edit(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the patient table to edit.", severity="warning")
            return

        try:
            protocol_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected protocol.", severity="error")
            return

        protocol = db.get_user_protocol_by_id(protocol_id)
        if not protocol:
            self.notify("Protocol not found.", severity="error")
            return

        peptide_select = self.query_one("#peptide-select", Select)
        dose_unit_select = self.query_one("#dose-unit-select", Select)

        # Bypass on_select_changed's auto-refill-from-template side effect --
        # we want this protocol's exact saved values, not the master template's.
        with peptide_select.prevent(Select.Changed):
            peptide_select.value = protocol["peptide_name"]
        with dose_unit_select.prevent(Select.Changed):
            dose_unit_select.value = protocol["dose_unit"]

        self.query_one("#vial-size-input", Input).value = f"{protocol['vial_mg']}"
        self.query_one("#water-input", Input).value = f"{protocol['water_ml']}"
        self.query_one("#dose-input", Input).value = f"{protocol['target_dose']}"

        self.peptide = protocol["peptide_name"]
        self.vial_mg = protocol["vial_mg"]
        self.water_ml = protocol["water_ml"]
        self.target_dose = protocol["target_dose"]
        self.dose_unit = protocol["dose_unit"]

        self.query_one(TabbedContent).active = "calc-tab"
        # TabbedContent re-syncs `active` to whichever tab contains the
        # focused widget (see TabPane._on_descendant_focus), and the button
        # that triggered this handler is still focused inside patient-tab --
        # that resync would otherwise revert the tab switch above on the next
        # message cycle. Moving focus into the new tab keeps them in sync.
        self.set_focus(self.query_one("#vial-size-input", Input))
        self.recalculate()
        self.update_schedule_table()
        self.notify(
            f"Loaded {protocol['peptide_name']} into the calculator for editing. Adjust and Save to update.",
            timeout=4.0,
        )

    def log_selected_protocol_dose(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("Select a row in the patient table to log a dose.", severity="warning")
            return

        try:
            protocol_id = int(table.get_cell_at((table.cursor_row, 0)))
        except (TypeError, ValueError):
            self.notify("Error reading selected protocol.", severity="error")
            return

        protocol = db.get_user_protocol_by_id(protocol_id)
        if not protocol:
            self.notify("Protocol not found.", severity="error")
            return

        dose_desc = f"{protocol['peptide_name']} {protocol['target_dose']} {protocol['dose_unit']}"

        def handle_notes(notes: str | None) -> None:
            if notes is None:
                return  # cancelled
            db.log_dose(
                self.active_profile_id,
                protocol_id,
                protocol["peptide_name"],
                protocol["target_dose"],
                protocol["dose_unit"],
                notes,
            )
            self.refresh_dose_log_tables()
            self.notify(f"Logged dose: {dose_desc}", timeout=3.0)

        self.push_screen(LogDoseScreen(f"Log dose: {dose_desc}"), handle_notes)

    def recalculate(self) -> None:
        try:
            vial_mg = self.vial_mg
            water_ml = self.water_ml
            dose = self.target_dose
            unit = self.dose_unit

            if vial_mg <= 0 or water_ml <= 0 or dose <= 0:
                self.query_one("#calc-concentration", Label).update("Enter positive numbers...")
                self.query_one("#calc-dose-volume", Label).update("Enter positive numbers...")
                self.query_one("#calc-syringe-draw", Label).update("Enter positive numbers...")
                self.query_one("#calc-doses-per-vial", Label).update("Enter positive numbers...")
                self.query_one("#syringe-visual", Label).update("  Syringe representation will appear here when inputs are valid.")
                return

            conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
            conc_mcg_ml = conc_mg_ml * 1000.0
            dose_mg = calc.dose_to_mg(dose, unit)
            draw_volume_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
            syringe_units = calc.syringe_units(draw_volume_ml)
            doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)

            self.query_one("#calc-concentration", Label).update(f"{conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)")
            self.query_one("#calc-dose-volume", Label).update(f"{draw_volume_ml:.3f} mL")
            
            if syringe_units > 100.0:
                self.query_one("#calc-syringe-draw", Label).update(f"{syringe_units:.1f} Units [bold red](Exceeds Capacity!)[/]")
            else:
                self.query_one("#calc-syringe-draw", Label).update(f"{syringe_units:.1f} Units")
                
            self.query_one("#calc-doses-per-vial", Label).update(f"{doses_per_vial:.1f} doses")
            
            syringe_ascii = make_syringe_display(syringe_units)
            self.query_one("#syringe-visual", Label).update(syringe_ascii)
        except Exception:
            pass

    def update_schedule_table(self) -> None:
        try:
            table = self.query_one("#schedule-table", DataTable)
            table.clear()
            
            vial_mg = self.vial_mg
            water_ml = self.water_ml
            if vial_mg <= 0 or water_ml <= 0 or self.target_dose <= 0:
                return

            conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
            p = db.get_peptide_by_name(self.peptide)
            schedule_steps = p["schedule"] if p and p["schedule"] else [("Custom Dose", self.target_dose, self.dose_unit)]

            for phase, dose_val, unit in schedule_steps:
                dose_mg = calc.dose_to_mg(dose_val, unit)
                dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"
                vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                units = calc.syringe_units(vol_ml)
                doses_per_vial = calc.doses_per_vial(vial_mg, dose_mg)

                table.add_row(phase, dose_str, f"{vol_ml:.3f} mL", f"{units:.1f} Units", f"{doses_per_vial:.1f} doses")
        except Exception:
            pass

    def save_schedule_to_file(self) -> None:
        try:
            peptide_name = self.peptide
            vial_mg = self.vial_mg
            water_ml = self.water_ml
            if vial_mg <= 0 or water_ml <= 0:
                self.notify("Cannot save schedule: Invalid inputs.", severity="error")
                return
                
            conc_mg_ml = calc.concentration_mg_ml(vial_mg, water_ml)
            conc_mcg_ml = conc_mg_ml * 1000.0
            p = db.get_peptide_by_name(peptide_name)
            schedule_steps = p["schedule"] if p and p["schedule"] else [("Custom Dose", self.target_dose, self.dose_unit)]
            notes = p["notes"] if p else "Custom protocol."
            sources = p["sources"] if p else []
                
            filename = f"peptide_{peptide_name.lower().replace(' ', '_')}_schedule.txt"
            filepath = os.path.join(os.getcwd(), filename)
            
            with open(filepath, "w") as f:
                f.write("=" * 68 + "\n")
                f.write(" PEPTIDE DOSING SCHEDULE & RECONSTITUTION PROTOCOL\n")
                f.write("=" * 68 + "\n")
                f.write(f"Peptide Name:         {peptide_name}\n")
                f.write(f"Date Generated:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Vial Strength:        {vial_mg:.1f} mg\n")
                f.write(f"Reconstitution Water: {water_ml:.1f} mL (Bacteriostatic Water)\n")
                f.write(f"Concentration:        {conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)\n")
                f.write(f"Syringe Standard:     U-100 Insulin Syringe (100 Units = 1.0 mL)\n")
                f.write("-" * 68 + "\n")
                f.write("Notes & Details:\n")
                f.write(f"{notes}\n")
                f.write("-" * 68 + "\n\n")
                
                f.write("DOSING SCHEDULE:\n")
                phase_width = max(22, max((len(phase) for phase, _, _ in schedule_steps), default=22))
                header = f"{'Phase / Period':<{phase_width}} | {'Dose':<12} | {'Volume (mL)':<12} | {'Syringe Draw (U-100)':<20}"
                f.write(header + "\n")
                f.write("-" * len(header) + "\n")

                for phase, dose_val, unit in schedule_steps:
                    dose_mg = calc.dose_to_mg(dose_val, unit)
                    dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"
                    vol_ml = calc.draw_volume_ml(dose_mg, conc_mg_ml)
                    units = calc.syringe_units(vol_ml)
                    vol_str = f"{vol_ml:.3f} mL"
                    f.write(f"{phase:<{phase_width}} | {dose_str:<12} | {vol_str:<12} | {units:.1f} Units\n")
                    
                if sources:
                    f.write("\n" + "-" * 68 + "\n")
                    f.write("SCIENTIFIC CITATIONS & SOURCES:\n")
                    for s in sources:
                        f.write(f"- {s['title']} (PMID: {s['pmid']})\n  URL: {s['url']}\n")
                        
                f.write("\n" + "=" * 68 + "\n")
                
            self.notify(f"Saved schedule to: {filename}", timeout=4.0)
        except Exception as e:
            self.notify(f"Error saving schedule: {str(e)}", severity="error")


def run() -> None:
    app = PeptideCalculatorApp()
    app.run()


if __name__ == "__main__":
    run()
