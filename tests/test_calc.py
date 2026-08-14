import calc


def test_concentration_mg_ml():
    assert calc.concentration_mg_ml(5.0, 2.0) == 2.5
    assert calc.concentration_mg_ml(5.0, 0.0) == 0.0


def test_dose_to_mg():
    assert calc.dose_to_mg(250.0, "mcg") == 0.25
    assert calc.dose_to_mg(2.5, "mg") == 2.5


def test_draw_volume_ml():
    assert calc.draw_volume_ml(0.25, 2.5) == 0.1
    assert calc.draw_volume_ml(0.25, 0.0) == 0.0


def test_syringe_units():
    assert calc.syringe_units(0.1) == 10.0


def test_doses_per_vial():
    assert calc.doses_per_vial(5.0, 0.25) == 20.0
    assert calc.doses_per_vial(5.0, 0.0) == 0.0


def test_bpc157_known_good_numbers():
    # BPC-157: 5mg vial, 2mL water, 250mcg dose -> 2.5 mg/mL, 0.1 mL draw,
    # 10.0 Units, 20.0 doses/vial
    conc = calc.concentration_mg_ml(5.0, 2.0)
    dose_mg = calc.dose_to_mg(250.0, "mcg")
    volume = calc.draw_volume_ml(dose_mg, conc)
    units = calc.syringe_units(volume)
    per_vial = calc.doses_per_vial(5.0, dose_mg)

    assert conc == 2.5
    assert volume == 0.1
    assert units == 10.0
    assert per_vial == 20.0


def test_parse_weekly_frequency_daily_variants():
    assert calc.parse_weekly_frequency("daily") == 7.0
    assert calc.parse_weekly_frequency("daily (at bedtime)") == 7.0
    assert calc.parse_weekly_frequency("nightly (before bed)") == 7.0


def test_parse_weekly_frequency_weekly():
    assert calc.parse_weekly_frequency("weekly") == 1.0


def test_parse_weekly_frequency_nx_weekly():
    assert calc.parse_weekly_frequency("3x weekly") == 3.0
    assert calc.parse_weekly_frequency("2-3x weekly") == 2.5


def test_parse_weekly_frequency_unrecognized():
    assert calc.parse_weekly_frequency("as needed (PRN)") is None
    assert calc.parse_weekly_frequency("") is None
    assert calc.parse_weekly_frequency(None) is None


def test_adherence_percent_normal():
    # 1x/week expected, logged 2 doses over 14 days -> 100% (exactly on pace)
    assert calc.adherence_percent(2, 1.0, 14.0) == 100.0


def test_adherence_percent_partial():
    # 7x/week expected (daily), logged 3 doses over 7 days -> ~43%
    result = calc.adherence_percent(3, 7.0, 7.0)
    assert round(result, 1) == 42.9


def test_adherence_percent_capped_at_100():
    assert calc.adherence_percent(100, 1.0, 7.0) == 100.0


def test_adherence_percent_unmeasurable():
    assert calc.adherence_percent(5, None, 30.0) is None
    assert calc.adherence_percent(0, 7.0, 0.5) is None
