"""
theme.py – Omarchy-aware CSS generation for the Peptide Dosage TUI.

Reads the active Omarchy theme's ``colors.toml`` at startup and whenever the
theme changes.  ``PeptideCalculatorApp`` polls ``theme_changed_on_disk()``
every 2 seconds; when it returns True the app reloads CSS across all screens.

No hooks, sentinel files, or extra installs needed — works on any machine
that has Omarchy.  Falls back to the original hardcoded palette when running
outside Omarchy.
"""

import pathlib
import tomllib

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_OMARCHY_THEMES_USER  = pathlib.Path.home() / ".config" / "omarchy" / "themes"
_OMARCHY_THEMES_STOCK = pathlib.Path("/usr/share/omarchy/themes")

# Omarchy writes the raw slug (e.g. "tokyo-night") to this file when the
# theme changes.  Reading it directly is faster and more accurate than
# parsing the pretty-printed output of `omarchy theme current`.
_THEME_NAME_FILE = pathlib.Path.home() / ".local/state/omarchy/current/theme.name"


# ---------------------------------------------------------------------------
# Color loading
# ---------------------------------------------------------------------------

# Default fallback palette (original Slate/Sky hardcoded colors)
_DEFAULTS = {
    "background":         "#0f172a",
    "dark_background":    "#0f172a",
    "darker_background":  "#0f172a",
    "lighter_background": "#1e293b",
    "foreground":         "#e2e8f0",
    "dark_foreground":    "#94a3b8",
    "light_foreground":   "#cbd5e1",
    "bright_foreground":  "#f1f5f9",
    "accent":             "#38bdf8",
    "selection":          "#334155",
    "muted":              "#475569",
    "red":                "#f43f5e",
    "green":              "#10b981",
    "mode":               "dark",
}


def _current_theme_slug() -> str:
    """Return the active Omarchy theme slug (e.g. 'vikings'), or ''."""
    try:
        return _THEME_NAME_FILE.read_text().strip()
    except Exception:
        return ""


def load_colors() -> dict:
    """
    Read the active Omarchy theme's colors.toml and return a merged dict.

    Lookup order (first hit wins):
      1. ~/.config/omarchy/themes/<slug>/colors.toml  (user overlay / custom)
      2. /usr/share/omarchy/themes/<slug>/colors.toml (stock)
      3. Built-in fallback palette (runs fine outside Omarchy)
    """
    slug = _current_theme_slug()
    if slug:
        for base in (_OMARCHY_THEMES_USER, _OMARCHY_THEMES_STOCK):
            candidate = base / slug / "colors.toml"
            if candidate.exists():
                try:
                    with open(candidate, "rb") as fh:
                        raw = tomllib.load(fh)
                    # Merge over defaults so every key is always present
                    merged = dict(_DEFAULTS)
                    merged.update(raw)
                    return merged
                except Exception:
                    pass  # Malformed TOML → fall through to defaults
    return dict(_DEFAULTS)


# ---------------------------------------------------------------------------
# Live-reload helper — watch theme.name mtime
# ---------------------------------------------------------------------------

# Watching the mtime of theme.name is both faster (no subprocess) and
# correct — Omarchy rewrites this file whenever the theme changes.
_last_theme_name_mtime: float = 0.0
try:
    _last_theme_name_mtime = _THEME_NAME_FILE.stat().st_mtime
except Exception:
    pass


def theme_changed_on_disk() -> bool:
    """Return True if Omarchy has changed the active theme since the last call.
    Always returns False when running outside Omarchy."""
    global _last_theme_name_mtime
    try:
        mtime = _THEME_NAME_FILE.stat().st_mtime
    except Exception:
        return False
    if mtime != _last_theme_name_mtime:
        _last_theme_name_mtime = mtime
        return True
    return False



# ---------------------------------------------------------------------------
# CSS builders
# ---------------------------------------------------------------------------

def build_main_css(c: dict) -> str:
    bg        = c["background"]
    bg_light  = c["lighter_background"]
    bg_dark   = c["dark_background"]
    sel       = c["selection"]
    muted     = c["muted"]
    fg        = c["foreground"]
    fg_muted  = c["dark_foreground"]
    fg_light  = c["light_foreground"]
    fg_bright = c["bright_foreground"]
    accent    = c["accent"]
    red       = c["red"]
    green     = c["green"]

    return f"""
Screen {{
    background: {bg};
    color: {fg};
}}

Header {{
    background: {bg_light};
    color: {accent};
    text-align: center;
    height: 1;
    border-bottom: solid {accent};
}}

Footer {{
    background: {bg_light};
    color: {fg_light};
    dock: bottom;
    height: 1;
}}

FooterKey {{
    background: {sel};
    color: {accent};
    text-style: bold;
}}

FooterLabel {{
    color: {fg_light};
}}

TabbedContent {{
    margin-top: 0;
    height: 1fr;
}}

TabPane {{
    padding: 0;
    height: 1fr;
}}

.pane-container {{
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 1fr;
    grid-gutter: 1;
    padding: 0 1;
    height: 1fr;
}}

.sidebar-panel {{
    background: {bg_light};
    border: solid {sel};
    padding: 0 1;
    height: 1fr;
}}

.results-panel {{
    background: {bg_light};
    border: solid {sel};
    padding: 0 1;
    layout: vertical;
    height: 1fr;
}}

.title-label {{
    color: {accent};
    text-style: bold;
    margin-bottom: 0;
    border-bottom: solid {sel};
}}

.input-label {{
    text-style: bold;
    margin-top: 1;
    color: {fg_light};
}}

.preset-row {{
    layout: horizontal;
    height: 3;
    margin-bottom: 0;
    margin-top: 0;
}}

.preset-row Button {{
    margin-right: 1;
    min-width: 6;
    height: 3;
    background: {sel};
    color: {fg_bright};
}}

.preset-row Button:hover {{
    background: {muted};
}}

Input {{
    background: {bg};
    border: solid {muted};
    color: {fg_bright};
    margin-bottom: 0;
    height: 3;
}}

Select {{
    margin-bottom: 0;
    height: 3;
}}

SelectCurrent {{
    background: {bg};
    border: solid {accent};
    color: {accent};
    text-style: bold;
    height: 3;
}}

.result-row {{
    layout: horizontal;
    height: 2;
    content-align: left middle;
    border-bottom: solid {sel};
}}

.result-label {{
    width: 24;
    text-style: bold;
    color: {fg_muted};
}}

.result-val {{
    color: {fg_bright};
    text-style: bold;
}}

#syringe-visual {{
    background: {bg};
    border: double {accent};
    padding: 0 1;
    margin-top: 0;
    margin-bottom: 0;
    height: 5;
    color: {accent};
}}

.help-box {{
    background: {bg_light};
    border: solid {sel};
    padding: 0 1;
    margin-top: 0;
    color: {fg_muted};
}}

.action-bar {{
    layout: horizontal;
    height: 3;
    align: right middle;
    padding: 0 1;
    background: {bg_light};
    border-bottom: solid {sel};
}}

.global-profile-bar {{
    layout: horizontal;
    height: 3;
    align: left middle;
    padding: 0 1;
    background: {bg_light};
    border-bottom: solid {accent};
}}

.global-profile-bar .action-title {{
    margin-right: 1;
}}

.patient-controls-bar {{
    layout: vertical;
    padding: 0 1;
    background: {bg_light};
    border-bottom: solid {sel};
    height: 10;
}}

.control-row {{
    layout: horizontal;
    height: 3;
    align: left middle;
    margin-bottom: 0;
}}

#profile-select {{
    width: 25;
    margin-right: 1;
}}

#patient-add-peptide-select {{
    width: 25;
    margin-right: 1;
}}

#new-profile-input {{
    width: 22;
    margin-right: 1;
}}

#schedule-protocol-select {{
    width: 48;
    margin-right: 1;
}}

.schedule-controls-bar {{
    layout: vertical;
    padding: 0 1;
    background: {bg_light};
    border-bottom: solid {sel};
    height: auto;
}}

.schedule-banner-row {{
    layout: horizontal;
    align: left middle;
    background: {bg};
    border: solid {sel};
    padding: 0 1;
    margin-top: 1;
    margin-bottom: 1;
    height: 3;
}}

#schedule-banner-text {{
    color: {accent};
    text-style: bold;
}}

.action-title {{
    color: {accent};
    text-style: bold;
    margin-right: 1;
}}

DataTable {{
    height: 1fr;
    border: solid {sel};
    background: {bg};
    margin: 0 1;
}}

.info-pane {{
    padding: 1 2;
    height: 100%;
}}

.info-section {{
    background: {bg_light};
    border: solid {sel};
    padding: 1 2;
    margin-bottom: 1;
    height: auto;
}}

.info-title {{
    color: {accent};
    text-style: bold;
    margin-bottom: 1;
}}

.info-text {{
    color: {fg_light};
    margin-bottom: 1;
    height: auto;
}}

.source-link {{
    color: {accent};
    margin-left: 2;
    margin-bottom: 1;
    height: auto;
}}

#save-target-profiles {{
    height: 6;
    border: solid {sel};
    background: {bg};
    margin-bottom: 1;
}}

#save-profile-protocol-btn {{
    background: {accent};
    color: {bg};
    text-style: bold;
    margin-top: 1;
    height: 3;
}}

#save-schedule-btn, #export-patient-sheet-btn, #export-dose-log-csv-btn {{
    background: {green};
    color: {bg};
    text-style: bold;
    min-width: 24;
    margin-left: 1;
    height: 3;
}}

#add-profile-btn, #quick-add-peptide-btn {{
    background: {accent};
    color: {bg};
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}}

#delete-protocol-btn, #remove-profile-btn, #delete-log-btn {{
    background: {red};
    color: {fg_bright};
    text-style: bold;
    min-width: 18;
    margin-left: 1;
    height: 3;
}}

#edit-protocol-btn, #log-dose-btn, #view-schedule-btn, #generate-titration-btn {{
    background: {accent};
    color: {bg};
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}}

#split-vial-btn {{
    background: {accent};
    color: {bg};
    text-style: bold;
    margin-top: 1;
    height: 3;
}}

.track-sources-btn {{
    background: {sel};
    color: {accent};
    text-style: bold;
    margin-top: 1;
    height: 3;
}}

#mark-reconstituted-btn, #edit-log-btn {{
    background: {accent};
    color: {bg};
    text-style: bold;
    min-width: 16;
    margin-left: 1;
    height: 3;
}}

#literature-peptide-filter {{
    width: 46;
    margin-left: 1;
}}

#adherence-table {{
    height: 10;
    margin: 0 1;
}}
"""


def build_confirm_css(c: dict) -> str:
    bg_light  = c["lighter_background"]
    fg_bright = c["bright_foreground"]
    sel       = c["selection"]
    red       = c["red"]

    return f"""
ConfirmScreen {{
    align: center middle;
}}

#confirm-dialog {{
    width: 60;
    height: auto;
    background: {bg_light};
    border: solid {red};
    padding: 1 2;
}}

#confirm-message {{
    color: {fg_bright};
    margin-bottom: 1;
    height: auto;
}}

#confirm-buttons {{
    layout: horizontal;
    height: 3;
    align: right middle;
}}

#confirm-buttons Button {{
    margin-left: 1;
    min-width: 10;
}}

#confirm-yes {{
    background: {red};
    color: {fg_bright};
}}

#confirm-no {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_log_dose_css(c: dict) -> str:
    bg        = c["background"]
    bg_light  = c["lighter_background"]
    fg_light  = c["light_foreground"]
    fg_bright = c["bright_foreground"]
    sel       = c["selection"]
    accent    = c["accent"]
    red       = c["red"]

    return f"""
LogDoseScreen {{
    align: center middle;
}}

#logdose-dialog {{
    width: 60;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#logdose-message {{
    color: {fg_bright};
    margin-bottom: 1;
    height: auto;
}}

#logdose-notes {{
    margin-bottom: 1;
}}

#logdose-taken-at {{
    margin-bottom: 1;
}}

.logdose-field-label {{
    color: {fg_light};
    height: 1;
}}

#logdose-status {{
    color: {red};
    height: auto;
}}

#logdose-buttons {{
    layout: horizontal;
    height: 3;
    align: right middle;
}}

#logdose-buttons Button {{
    margin-left: 1;
    min-width: 10;
}}

#logdose-yes {{
    background: {accent};
    color: {bg};
}}

#logdose-no {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_edit_dose_css(c: dict) -> str:
    bg        = c["background"]
    bg_light  = c["lighter_background"]
    fg_light  = c["light_foreground"]
    fg_bright = c["bright_foreground"]
    sel       = c["selection"]
    accent    = c["accent"]
    red       = c["red"]

    return f"""
EditDoseScreen {{
    align: center middle;
}}

#editdose-dialog {{
    width: 64;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#editdose-title {{
    color: {accent};
    text-style: bold;
    margin-bottom: 1;
}}

.editdose-field-label {{
    color: {fg_light};
    height: 1;
}}

#editdose-status {{
    color: {red};
    height: auto;
}}

#editdose-buttons {{
    layout: horizontal;
    height: 3;
    align: right middle;
}}

#editdose-buttons Button {{
    margin-left: 1;
    min-width: 12;
}}

#editdose-save {{
    background: {accent};
    color: {bg};
}}

#editdose-cancel {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_titration_css(c: dict) -> str:
    bg        = c["background"]
    bg_light  = c["lighter_background"]
    fg_light  = c["light_foreground"]
    fg_bright = c["bright_foreground"]
    sel       = c["selection"]
    accent    = c["accent"]
    red       = c["red"]

    return f"""
TitrationGeneratorScreen {{
    align: center middle;
}}

#titration-dialog {{
    width: 78;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#titration-title {{
    color: {accent};
    text-style: bold;
    margin-bottom: 1;
}}

.titration-input-row {{
    layout: horizontal;
    height: 3;
    margin-bottom: 1;
}}

.titration-input-row Label {{
    width: 22;
    content-align: left middle;
    color: {fg_light};
}}

.titration-input-row Input {{
    width: 1fr;
}}

#titration-status {{
    color: {red};
    height: auto;
    margin-bottom: 1;
}}

#titration-preview-table {{
    height: 10;
    border: solid {sel};
    margin-bottom: 1;
}}

#titration-buttons {{
    layout: horizontal;
    height: 3;
    align: right middle;
}}

#titration-buttons Button {{
    margin-left: 1;
    min-width: 14;
}}

#titration-save-btn {{
    background: {accent};
    color: {bg};
}}

#titration-cancel-btn {{
    background: {sel};
    color: {fg_bright};
}}
"""


def build_split_css(c: dict) -> str:
    bg_light  = c["lighter_background"]
    fg        = c["foreground"]
    fg_light  = c["light_foreground"]
    sel       = c["selection"]
    accent    = c["accent"]
    red       = c["red"]
    bg        = c["background"]

    return f"""
VialSplitScreen {{
    align: center middle;
}}

#split-dialog {{
    width: 70;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#split-title {{
    color: {accent};
    text-style: bold;
    margin-bottom: 1;
}}

#split-parent-info {{
    color: {fg_light};
    margin-bottom: 1;
    height: auto;
}}

.split-input-row {{
    layout: horizontal;
    height: 3;
    margin-bottom: 1;
}}

.split-input-row Label {{
    width: 22;
    content-align: left middle;
    color: {fg_light};
}}

.split-input-row Input {{
    width: 1fr;
}}

#split-status {{
    color: {red};
    height: auto;
    margin-bottom: 1;
}}

#split-results {{
    color: {fg};
    height: auto;
    margin-bottom: 1;
    border: solid {sel};
    padding: 1 2;
}}

#split-close-btn {{
    background: {accent};
    color: {bg};
    width: 100%;
}}
"""


def build_help_css(c: dict) -> str:
    bg        = c["background"]
    bg_light  = c["lighter_background"]
    fg        = c["foreground"]
    accent    = c["accent"]

    return f"""
HelpScreen {{
    align: center middle;
}}

#help-dialog {{
    width: 74;
    height: auto;
    background: {bg_light};
    border: solid {accent};
    padding: 1 2;
}}

#help-title {{
    color: {accent};
    text-style: bold;
    margin-bottom: 1;
    text-align: center;
}}

.help-cmd-row {{
    layout: horizontal;
    height: 1;
    margin-bottom: 0;
}}

.help-cmd-key {{
    width: 20;
    color: {accent};
    text-style: bold;
}}

.help-cmd-desc {{
    color: {fg};
}}

#help-close-btn {{
    margin-top: 1;
    background: {accent};
    color: {bg};
    text-style: bold;
    width: 100%;
}}
"""


def build_all_css() -> dict[str, str]:
    """Load current Omarchy colors and return all CSS strings keyed by name."""
    c = load_colors()
    return {
        "main":      build_main_css(c),
        "confirm":   build_confirm_css(c),
        "log_dose":  build_log_dose_css(c),
        "edit_dose": build_edit_dose_css(c),
        "titration": build_titration_css(c),
        "split":     build_split_css(c),
        "help":      build_help_css(c),
    }
