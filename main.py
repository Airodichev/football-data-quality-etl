"""Сверка матчей Бундеслиги 2025/26 из двух API."""

import sqlite3
from datetime import timezone
from pathlib import Path

from openligadb import matches_normalized
from football_data import match_normalized
from team_matching import team_mapping, unmatched_teams

if len(set(team_mapping.values())) != len(team_mapping):
    raise ValueError("Несколько команд OpenLigaDB имеют один ID football-data.org")


def utc_text(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


# Проверки каждого источника. Пустой счёт допустим только для незавершённого матча.
checks = {}
for source, matches in (("openligadb", matches_normalized),
                        ("football_data", match_normalized)):
    seen_ids = set()
    seen_pairs = set()
    duplicate_ids = []
    duplicate_pairs = []
    missing_fields = []
    invalid_goals = []

    for match in matches:
        match_id = match["source_match_id"]
        pair = (match["home_team_id"], match["away_team_id"])

        if match_id in seen_ids:
            duplicate_ids.append(match_id)
        seen_ids.add(match_id)
        if pair in seen_pairs:
            duplicate_pairs.append(pair)
        seen_pairs.add(pair)

        required = ("source_match_id", "match_datetime_utc", "home_team_id",
                    "away_team_id", "home_team_name", "away_team_name", "is_finished")
        if any(match.get(field) is None or match.get(field) == "" for field in required):
            missing_fields.append(match_id)
        elif match["is_finished"] and (match["home_goals"] is None or match["away_goals"] is None):
            missing_fields.append(match_id)

        for goals in (match["home_goals"], match["away_goals"]):
            if goals is not None and (type(goals) is not int or goals < 0):
                invalid_goals.append(match_id)
                break

    checks[source] = {
        "duplicate_ids": duplicate_ids,
        "duplicate_pairs": duplicate_pairs,
        "missing_fields": missing_fields,
        "invalid_goals": invalid_goals,
    }


# Для каждой пары храним все матчи, чтобы не выбирать произвольный дубликат.
football_by_pair = {}
for match in match_normalized:
    pair = (match["home_team_id"], match["away_team_id"])
    if pair not in football_by_pair:
        football_by_pair[pair] = []
    football_by_pair[pair].append(match)

openliga_by_pair = {}
for match in matches_normalized:
    home_id = team_mapping.get(match["home_team_id"])
    away_id = team_mapping.get(match["away_team_id"])
    if home_id is not None and away_id is not None:
        pair = (home_id, away_id)
        if pair not in openliga_by_pair:
            openliga_by_pair[pair] = []
        openliga_by_pair[pair].append(match)

reconciliation = []
matched_football_ids = set()
for match in matches_normalized:
    home_id = team_mapping.get(match["home_team_id"])
    away_id = team_mapping.get(match["away_team_id"])
    other = None
    status = "missing_team_mapping"

    if home_id is not None and away_id is not None:
        pair = (home_id, away_id)
        candidates = football_by_pair.get(pair, [])
        if len(openliga_by_pair[pair]) > 1 or len(candidates) > 1:
            status = "ambiguous_match"
        elif len(candidates) == 0:
            status = "missing_match"
        else:
            status = "matched"
            other = candidates[0]
            matched_football_ids.add(other["source_match_id"])

    score_diff = None
    time_diff = None
    finished_diff = None
    if other is not None:
        if (match["home_goals"] is not None and match["away_goals"] is not None
                and other["home_goals"] is not None and other["away_goals"] is not None):
            score_diff = ((match["home_goals"], match["away_goals"]) !=
                          (other["home_goals"], other["away_goals"]))
        if match["match_datetime_utc"] is not None and other["match_datetime_utc"] is not None:
            time_diff = (utc_text(match["match_datetime_utc"]) !=
                         utc_text(other["match_datetime_utc"]))
        if match["is_finished"] is not None and other["is_finished"] is not None:
            finished_diff = match["is_finished"] != other["is_finished"]

    reconciliation.append({
        "openliga_id": match["source_match_id"],
        "football_id": other["source_match_id"] if other else None,
        "status": status,
        "score_diff": score_diff,
        "time_diff": time_diff,
        "finished_diff": finished_diff,
    })

db_path = Path(__file__).with_name("football.db")
with sqlite3.connect(db_path) as db:
    db.execute("""CREATE TABLE IF NOT EXISTS matches (
        source TEXT NOT NULL, source_match_id INTEGER NOT NULL,
        match_datetime_utc TEXT, home_team_id INTEGER, home_team_name TEXT,
        away_team_id INTEGER, away_team_name TEXT, home_goals INTEGER,
        away_goals INTEGER, is_finished INTEGER,
        PRIMARY KEY (source, source_match_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS reconciliation (
        openliga_id INTEGER PRIMARY KEY, football_id INTEGER, match_status TEXT NOT NULL,
        score_diff INTEGER, time_diff INTEGER, finished_diff INTEGER)""")

    for source, matches in (("openligadb", matches_normalized),
                            ("football_data", match_normalized)):
        for match in matches:
            db.execute("""INSERT OR REPLACE INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                source, match["source_match_id"], utc_text(match["match_datetime_utc"]),
                match["home_team_id"], match["home_team_name"],
                match["away_team_id"], match["away_team_name"],
                match["home_goals"], match["away_goals"], match["is_finished"],
            ))
    for item in reconciliation:
        db.execute("""INSERT OR REPLACE INTO reconciliation VALUES (?, ?, ?, ?, ?, ?)""", (
            item["openliga_id"], item["football_id"], item["status"],
            item["score_diff"], item["time_diff"], item["finished_diff"],
        ))

    stored_matches = db.execute("SELECT source, COUNT(*) FROM matches GROUP BY source").fetchall()
    stored_reconciliation = db.execute("SELECT COUNT(*) FROM reconciliation").fetchone()[0]


# Короткий отчёт также остаётся в файле после запуска.
report = [
    "Bundesliga 2025/26 — ETL report",
    f"OpenLigaDB: {len(matches_normalized)} матчей; football-data.org: {len(match_normalized)} матчей",
    f"Команд сопоставлено: {len(team_mapping)}; без соответствия: {len(unmatched_teams)}",
    f"Матчей сопоставлено: {sum(item['status'] == 'matched' for item in reconciliation)}",
    f"Без соответствия OpenLigaDB: {sum(item['status'] != 'matched' for item in reconciliation)}; "
    f"football-data.org: {len(match_normalized) - len(matched_football_ids)}",
]
for source, result in checks.items():
    report.append(f"{source}: дубли ID {len(result['duplicate_ids'])}, "
                  f"дубли пар {len(result['duplicate_pairs'])}, "
                  f"пропуски полей {len(result['missing_fields'])}, "
                  f"некорректный счёт {len(result['invalid_goals'])}")
for status in ("missing_team_mapping", "missing_match", "ambiguous_match"):
    report.append(f"{status}: {sum(item['status'] == status for item in reconciliation)}")
for field in ("score_diff", "time_diff", "finished_diff"):
    ids = [item["openliga_id"] for item in reconciliation if item[field] is True]
    report.append(f"{field}: {len(ids)}" + (f" (OpenLigaDB ID: {ids})" if ids else ""))
report.append(f"SQLite: {stored_matches}; строк сверки: {stored_reconciliation}")

report_text = "\n".join(report)
Path(__file__).with_name("report.txt").write_text(report_text + "\n", encoding="utf-8")
print(report_text)
