import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import db


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_peptides.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    db.init_db()
    return db


def test_init_db_seeds_default_profiles(fresh_db):
    profiles = fresh_db.get_profiles()
    names = {p["name"] for p in profiles}
    assert {"Default User", "Alice", "Bob"} <= names


def test_init_db_seeds_peptides_and_fixes_tesamorelin(fresh_db):
    names = {p["name"] for p in fresh_db.get_peptides()}
    assert "Tesamorelin" in names
    assert "Tesemorelin" not in names


def test_tesemorelin_migration_updates_existing_user_protocol(fresh_db):
    profiles = fresh_db.get_profiles()
    pid = profiles[0]["id"]

    conn = fresh_db.get_connection()
    conn.execute(
        "INSERT INTO user_protocols (profile_id, peptide_name, vial_mg, water_ml, target_dose, dose_unit) "
        "VALUES (?, 'Tesemorelin', 2.0, 2.0, 2.0, 'mg')",
        (pid,),
    )
    conn.commit()
    conn.close()

    fresh_db.init_db()  # re-run migration

    protocols = fresh_db.get_user_protocols(pid)
    assert protocols[0]["peptide_name"] == "Tesamorelin"


def test_add_profile_and_duplicate_rejected(fresh_db):
    new_id = fresh_db.add_profile("Charlie")
    assert new_id is not None
    assert fresh_db.add_profile("Charlie") is None


def test_delete_profile(fresh_db):
    new_id = fresh_db.add_profile("Charlie")
    assert fresh_db.delete_profile(new_id) is True
    names = {p["name"] for p in fresh_db.get_profiles()}
    assert "Charlie" not in names


def test_delete_profile_refuses_last_profile(fresh_db):
    profiles = fresh_db.get_profiles()
    for p in profiles[:-1]:
        assert fresh_db.delete_profile(p["id"]) is True

    last = fresh_db.get_profiles()
    assert len(last) == 1
    assert fresh_db.delete_profile(last[0]["id"]) is False
    assert len(fresh_db.get_profiles()) == 1


def test_delete_profile_cascades_protocols_and_dose_log(fresh_db):
    pid = fresh_db.add_profile("Charlie")
    fresh_db.add_or_update_user_protocol(
        pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "notes", [], []
    )
    protocol_id = fresh_db.get_user_protocols(pid)[0]["id"]
    fresh_db.log_dose(pid, protocol_id, "BPC-157", 250.0, "mcg")

    fresh_db.delete_profile(pid)

    conn = fresh_db.get_connection()
    remaining_protocols = conn.execute(
        "SELECT COUNT(*) as c FROM user_protocols WHERE profile_id = ?", (pid,)
    ).fetchone()["c"]
    remaining_logs = conn.execute(
        "SELECT COUNT(*) as c FROM dose_log WHERE profile_id = ?", (pid,)
    ).fetchone()["c"]
    conn.close()
    assert remaining_protocols == 0
    assert remaining_logs == 0


def test_add_update_get_by_id_delete_user_protocol(fresh_db):
    pid = fresh_db.get_profiles()[0]["id"]
    fresh_db.add_or_update_user_protocol(
        pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "notes", [("Week 1", 250.0, "mcg")], []
    )
    protocol = fresh_db.get_user_protocols(pid)[0]
    fetched = fresh_db.get_user_protocol_by_id(protocol["id"])
    assert fetched["peptide_name"] == "BPC-157"
    assert fetched["schedule"] == [["Week 1", 250.0, "mcg"]]

    # Update by re-adding same peptide name -> upsert, not duplicate row
    fresh_db.add_or_update_user_protocol(
        pid, "BPC-157", 5.0, 2.0, 500.0, "mcg", "daily", "notes", [], []
    )
    protocols = fresh_db.get_user_protocols(pid)
    assert len(protocols) == 1
    assert protocols[0]["target_dose"] == 500.0

    fresh_db.delete_user_protocol(protocol["id"])
    assert fresh_db.get_user_protocols(pid) == []


def test_dose_log_add_list_delete(fresh_db):
    pid = fresh_db.get_profiles()[0]["id"]
    fresh_db.log_dose(pid, None, "BPC-157", 250.0, "mcg", notes="left thigh")
    log = fresh_db.get_dose_log(pid)
    assert len(log) == 1
    assert log[0]["notes"] == "left thigh"

    fresh_db.delete_dose_log_entry(log[0]["id"])
    assert fresh_db.get_dose_log(pid) == []


def test_get_protocol_adherence_measurable(fresh_db):
    pid = fresh_db.get_profiles()[0]["id"]
    fresh_db.add_or_update_user_protocol(
        pid, "BPC-157", 5.0, 2.0, 250.0, "mcg", "daily", "notes", [], []
    )
    protocol_id = fresh_db.get_user_protocols(pid)[0]["id"]

    # Backdate created_at 7 days so adherence math has a window to measure against
    conn = fresh_db.get_connection()
    week_ago = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE user_protocols SET created_at = ? WHERE id = ?", (week_ago, protocol_id))
    conn.commit()
    conn.close()

    for _ in range(3):
        fresh_db.log_dose(pid, protocol_id, "BPC-157", 250.0, "mcg")

    adherence = fresh_db.get_protocol_adherence(pid)
    entry = next(a for a in adherence if a["protocol_id"] == protocol_id)
    assert entry["logged_count"] == 3
    # daily -> 7 expected over 7 days, 3 logged -> ~42.9%
    assert round(entry["adherence_pct"], 1) == 42.9


def test_get_protocol_adherence_unmeasurable_for_unparseable_frequency(fresh_db):
    pid = fresh_db.get_profiles()[0]["id"]
    fresh_db.add_or_update_user_protocol(
        pid, "PT-141", 10.0, 2.0, 1.0, "mg", "as needed (PRN)", "notes", [], []
    )
    adherence = fresh_db.get_protocol_adherence(pid)
    entry = next(a for a in adherence if a["peptide_name"] == "PT-141")
    assert entry["adherence_pct"] is None
