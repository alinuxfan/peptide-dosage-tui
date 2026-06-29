import os
import sys
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
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

import db

# ASCII syringe drawing helper
def make_syringe_display(units: float) -> str:
    if units <= 0:
        filled = 0
    elif units > 100:
        filled = 50  # Cap at 100 units visually
    else:
        filled = int(round(units / 2.0))  # 50 character width (2 units per char)
        
    empty = 50 - filled
    
    # Plunger stick is '=', plunger rubber tip is '█', liquid is '░', empty is '.'
    stick_len = max(0, filled - 1)
    stick = "=" * stick_len
    rubber = "█" if filled > 0 else ""
    liquid = "░" * max(0, filled - stick_len - 1)
    barrel_content = f"{stick}{rubber}{liquid}{'.' * empty}"
    
    top_line = "            0   10   20   30   40   50   60   70   80   90  100 Units"
    mid_line = f" Needle ───┨ {barrel_content} ┠──══════ Plunger"
    
    marker_pos = 13 + filled
    bottom_line = " " * marker_pos + "▲"
    text_line = " " * max(0, marker_pos - 5) + f"{units:.1f} Units"
    
    warning_text = ""
    if units > 100:
        warning_text = "   [!] EXCEEDS 1.0mL SYRINGE CAPACITY!"
        
    return f"{top_line}\n{mid_line}\n{bottom_line}\n{text_line}{warning_text}"


CSS = """
Screen {
    background: #0f172a;
    color: #e2e8f0;
}

Header {
    background: #1e293b;
    color: #38bdf8;
    text-align: center;
    height: 3;
    border-bottom: solid #38bdf8;
}

Footer {
    background: #1e293b;
    color: #94a3b8;
}

TabbedContent {
    margin-top: 1;
}

.pane-container {
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 1fr;
    grid-gutter: 2;
    padding: 1 2;
}

.sidebar-panel {
    background: #1e293b;
    border: solid #334155;
    padding: 1 2;
}

.results-panel {
    background: #1e293b;
    border: solid #334155;
    padding: 1 2;
    layout: vertical;
}

.title-label {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 1;
    border-bottom: solid #334155;
    padding-bottom: 1;
}

.input-label {
    text-style: bold;
    margin-top: 1;
    color: #cbd5e1;
}

.preset-row {
    layout: horizontal;
    height: 3;
    margin-bottom: 1;
    margin-top: 1;
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
    margin-bottom: 1;
}

Input:focus {
    border: double #38bdf8;
}

Select {
    background: #0f172a;
    border: solid #475569;
    color: #f1f5f9;
    margin-bottom: 1;
}

Select:focus {
    border: double #38bdf8;
}

.result-row {
    layout: horizontal;
    height: 3;
    content-align: left middle;
    border-bottom: solid #334155;
}

.result-label {
    width: 25;
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
    padding: 1;
    margin-top: 1;
    margin-bottom: 1;
    height: 9;
    color: #38bdf8;
}

.help-box {
    background: #1e293b;
    border: solid #334155;
    padding: 1;
    margin-top: 1;
    color: #94a3b8;
}

.action-bar {
    layout: horizontal;
    height: 5;
    align: right middle;
    padding: 1 2;
    background: #1e293b;
    border-bottom: solid #334155;
}

.action-title {
    color: #38bdf8;
    text-style: bold;
}

DataTable {
    height: 1fr;
    border: solid #334155;
    background: #0f172a;
    margin: 1 2;
}

.info-pane {
    padding: 1 2;
    layout: vertical;
}

.info-section {
    background: #1e293b;
    border: solid #334155;
    padding: 1 2;
    margin-bottom: 1;
}

.info-title {
    color: #38bdf8;
    text-style: bold;
    margin-bottom: 1;
}

.info-text {
    color: #cbd5e1;
    margin-bottom: 1;
}

.source-link {
    color: #38bdf8;
    margin-left: 2;
}

#save-profile-protocol-btn {
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    margin-top: 1;
}

#save-schedule-btn, #export-patient-sheet-btn {
    background: #10b981;
    color: #0f172a;
    text-style: bold;
    min-width: 25;
    margin-left: 1;
}

#add-profile-btn {
    background: #38bdf8;
    color: #0f172a;
    text-style: bold;
    min-width: 15;
    margin-left: 1;
}

#delete-protocol-btn {
    background: #f43f5e;
    color: #ffffff;
    text-style: bold;
    min-width: 20;
    margin-left: 1;
}
"""


class PeptideCalculatorApp(App):
    TITLE = "Peptide Dosage, Tracker & Reconstitution TUI"
    SUB_TITLE = "Multi-Person Protocol Tracker with Scientific Citations"
    CSS = CSS

    # Reactive variables
    active_profile_id = reactive(1)
    peptide = reactive("Custom / Other")
    vial_mg = reactive(5.0)
    water_ml = reactive(2.0)
    target_dose = reactive(250.0)
    dose_unit = reactive("mcg")

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Calculator & Syringe Visualizer"):
                with Grid(classes="pane-container"):
                    # Left Sidebar: Inputs
                    with Vertical(classes="sidebar-panel"):
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
                        yield Input(value="5.0", placeholder="Enter mg...", id="vial-size-input")
                        
                        yield Label("Bacteriostatic Water (mL added):", classes="input-label")
                        with Horizontal(classes="preset-row"):
                            yield Button("1mL", id="water-btn-1")
                            yield Button("2mL", id="water-btn-2")
                            yield Button("2.5mL", id="water-btn-2_5")
                            yield Button("3mL", id="water-btn-3")
                        yield Input(value="2.0", placeholder="Enter mL...", id="water-input")
                        yield Label(
                            "Guidelines: GLP-1s/2s/3s: 2mL-3mL | Peptides: 3mL\n"
                            "Note: Higher water = lower concentration, making small doses easier to draw.",
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

                    # Right Panel: Output & Visualizer
                    with Vertical(classes="results-panel"):
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

            with TabPane("Patient Tracker (Multi-Person)"):
                with Vertical():
                    with Container(classes="action-bar"):
                        yield Label("Active Person Profile:", classes="action-title")
                        yield Select(options=[("Default User", "1")], value="1", id="profile-select")
                        yield Input(placeholder="New person name...", id="new-profile-input")
                        yield Button("+ Add Profile", id="add-profile-btn")
                        yield Button("Export Patient Reference Sheet", id="export-patient-sheet-btn")
                        yield Button("Remove Selected Protocol", id="delete-protocol-btn")
                    yield DataTable(id="patient-protocols-table")

            with TabPane("Dosing Schedule Planner"):
                with Vertical():
                    with Container(classes="action-bar"):
                        yield Label("Peptide Titration Schedule Planner & Exporter", classes="action-title")
                        yield Button("Save Schedule to File", id="save-schedule-btn")
                    yield DataTable(id="schedule-table")

            with TabPane("Peptide Reference & Cited Sources"):
                with ScrollableContainer(classes="info-pane", id="reference-scroll-container"):
                    yield Label("Loading cited peptide database...", id="ref-loading-label")
        yield Footer()

    def on_mount(self) -> None:
        db.init_db()
        
        # Setup tables
        sched_table = self.query_one("#schedule-table", DataTable)
        sched_table.add_columns("Phase / Week", "Dose", "Volume (mL)", "Syringe Draw (Units)", "Est. Doses per Vial")
        
        patient_table = self.query_one("#patient-protocols-table", DataTable)
        patient_table.add_columns("ID", "Peptide Name", "Vial Strength", "BAC Water", "Target Dose", "Syringe Draw", "Frequency", "Last Updated")
        
        # Load profile options into dropdowns
        self.refresh_profiles()
        self.refresh_peptide_templates()
        self.refresh_patient_protocols_table()
        self.populate_reference_tab()
        self.recalculate()

    def refresh_profiles(self) -> None:
        profiles = db.get_profiles()
        if not profiles:
            return
        options = [(p["name"], str(p["id"])) for p in profiles]
        
        profile_select = self.query_one("#profile-select", Select)
        profile_select.set_options(options)
        
        # Set active profile label in calc tab
        current_prof_name = next((p["name"] for p in profiles if p["id"] == self.active_profile_id), profiles[0]["name"])
        self.query_one("#calc-active-profile", Label).update(current_prof_name)

    def refresh_peptide_templates(self) -> None:
        peptides = db.get_peptides()
        options = [(p["name"], p["name"]) for p in peptides]
        peptide_select = self.query_one("#peptide-select", Select)
        peptide_select.set_options(options)

    def refresh_patient_protocols_table(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        table.clear()
        
        protocols = db.get_user_protocols(self.active_profile_id)
        for p in protocols:
            conc = p['vial_mg'] / p['water_ml'] if p['water_ml'] > 0 else 0
            dose_mg = p['target_dose'] / 1000.0 if p['dose_unit'] == 'mcg' else p['target_dose']
            vol_ml = dose_mg / conc if conc > 0 else 0
            units = vol_ml * 100.0
            
            table.add_row(
                str(p['id']),
                p['peptide_name'],
                f"{p['vial_mg']:.1f} mg",
                f"{p['water_ml']:.1f} mL",
                f"{p['target_dose']} {p['dose_unit']}",
                f"{units:.1f} Units",
                p['frequency'],
                p['updated_at'][:10]
            )

    def populate_reference_tab(self) -> None:
        container = self.query_one("#reference-scroll-container", ScrollableContainer)
        container.remove_children()
        
        peptides = db.get_peptides()
        for p in peptides:
            children = [
                Label(f"{p['name']} Reference & Literature", classes="info-title"),
                Label(f"• Standard Vial: {p['vial_mg']} mg | Dilution: {p['water_ml']} mL | Target Dose: {p['dose']} {p['unit']} ({p['freq']})\n• Details: {p['notes']}", classes="info-text")
            ]
            if p['sources']:
                children.append(Label("Scientific Citations & PubMed Links:", classes="input-label"))
                for s in p['sources']:
                    cite_text = f"  - {s['title']} (PMID: {s['pmid']})\n    Link: {s['url']}"
                    children.append(Label(cite_text, classes="source-link"))
                    
            sec = Vertical(*children, classes="info-section")
            container.mount(sec)

    def watch_active_profile_id(self, old_val: int, new_val: int) -> None:
        profiles = db.get_profiles()
        current_prof_name = next((p["name"] for p in profiles if p["id"] == new_val), "Unknown")
        try:
            self.query_one("#calc-active-profile", Label).update(current_prof_name)
            self.refresh_patient_protocols_table()
        except Exception:
            pass

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
                self.active_profile_id = int(str(event.value))
            except (ValueError, TypeError):
                pass
            
        self.recalculate()
        self.update_schedule_table()

    def on_input_changed(self, event: Input.Changed) -> None:
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
        elif btn_id == "add-profile-btn":
            self.create_new_profile()
        elif btn_id == "export-patient-sheet-btn":
            self.export_patient_sheet()
        elif btn_id == "delete-protocol-btn":
            self.delete_selected_patient_protocol()
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
        self.notify(f"Saved {self.peptide} protocol to active profile!", timeout=3.0)

    def create_new_profile(self) -> None:
        input_widget = self.query_one("#new-profile-input", Input)
        name = input_widget.value.strip()
        if not name:
            self.notify("Please enter a person name.", severity="error")
            return
        prof_id = db.add_profile(name)
        if prof_id:
            input_widget.value = ""
            self.refresh_profiles()
            self.active_profile_id = prof_id
            self.notify(f"Created profile: {name}", timeout=3.0)
        else:
            self.notify("Profile name already exists.", severity="error")

    def export_patient_sheet(self) -> None:
        filename = db.export_person_reference_sheet(self.active_profile_id)
        if filename:
            self.notify(f"Exported patient summary to: {filename}", timeout=4.0)
        else:
            self.notify("Error exporting summary sheet.", severity="error")

    def delete_selected_patient_protocol(self) -> None:
        table = self.query_one("#patient-protocols-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.coordinate_to_cell_key((table.cursor_row, 0))
            protocol_id_str = table.get_cell_at((table.cursor_row, 0))
            try:
                db.delete_user_protocol(int(protocol_id_str))
                self.refresh_patient_protocols_table()
                self.notify("Removed protocol from patient profile.", timeout=3.0)
            except Exception as e:
                self.notify(f"Error deleting protocol: {e}", severity="error")
        else:
            self.notify("Select a row in the patient table to remove.", severity="warning")

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

            conc_mg_ml = vial_mg / water_ml
            conc_mcg_ml = conc_mg_ml * 1000.0
            dose_mg = dose / 1000.0 if unit == "mcg" else dose
            draw_volume_ml = dose_mg / conc_mg_ml
            syringe_units = draw_volume_ml * 100.0
            doses_per_vial = vial_mg / dose_mg if dose_mg > 0 else 0

            self.query_one("#calc-concentration", Label).update(f"{conc_mg_ml:.2f} mg/mL ({conc_mcg_ml:,.0f} mcg/mL)")
            self.query_one("#calc-dose-volume", Label).update(f"{draw_volume_ml:.3f} mL")
            
            if syringe_units > 100.0:
                self.query_one("#calc-syringe-draw", Label).update(f"{syringe_units:.1f} Units [bold red](Exceeds Syringe Capacity!)[/]")
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
            if vial_mg <= 0 or water_ml <= 0:
                return
                
            conc_mg_ml = vial_mg / water_ml
            p = db.get_peptide_by_name(self.peptide)
            schedule_steps = p["schedule"] if p and p["schedule"] else [("Custom Dose", self.target_dose, self.dose_unit)]
                
            for phase, dose_val, unit in schedule_steps:
                dose_mg = dose_val / 1000.0 if unit == "mcg" else dose_val
                dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"
                vol_ml = dose_mg / conc_mg_ml if conc_mg_ml > 0 else 0
                units = vol_ml * 100.0
                doses_per_vial = vial_mg / dose_mg if dose_mg > 0 else 0.0
                
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
                
            conc_mg_ml = vial_mg / water_ml
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
                f.write(f"{'Phase / Period':<22} | {'Dose':<12} | {'Volume (mL)':<12} | {'Syringe Draw (U-100)':<20}\n")
                f.write("-" * 68 + "\n")
                
                for phase, dose_val, unit in schedule_steps:
                    dose_mg = dose_val / 1000.0 if unit == "mcg" else dose_val
                    dose_str = f"{dose_val:.0f} mcg" if unit == "mcg" else f"{dose_val:.2f} mg"
                    vol_ml = dose_mg / conc_mg_ml if conc_mg_ml > 0 else 0
                    units = vol_ml * 100.0
                    f.write(f"{phase:<22} | {dose_str:<12} | {vol_ml:.3f} mL    | {units:.1f} Units\n")
                    
                if sources:
                    f.write("\n" + "-" * 68 + "\n")
                    f.write("SCIENTIFIC CITATIONS & SOURCES:\n")
                    for s in sources:
                        f.write(f"- {s['title']} (PMID: {s['pmid']})\n  URL: {s['url']}\n")
                        
                f.write("\n" + "=" * 68 + "\n")
                
            self.notify(f"Saved schedule to: {filename}", timeout=4.0)
        except Exception as e:
            self.notify(f"Error saving schedule: {str(e)}", severity="error")


if __name__ == "__main__":
    app = PeptideCalculatorApp()
    app.run()
