import requests
from datetime import datetime

response = requests.get("https://api.openligadb.de/getmatchdata/bl1/2025", timeout=15)

response.raise_for_status()

data_json = response.json()

matches_normalized = []

for match in data_json:
    match_data = {
        "source": 'openligadb',
        "source_match_id": None,
        "match_datetime_utc": None,
        "home_team_id": None,
        "home_team_name": None,
        "away_team_id": None,
        "away_team_name": None,
        "home_goals": None,
        "away_goals": None,
        "is_finished": None}
    match_data["source_match_id"] = match["matchID"]
    match_data["match_datetime_utc"] = datetime.fromisoformat(match["matchDateTimeUTC"])
    match_data['home_team_id'] = match['team1']["teamId"]
    match_data['home_team_name'] = match['team1']["teamName"]
    match_data['away_team_id'] = match['team2']["teamId"]
    match_data['away_team_name'] = match['team2']["teamName"]
    match_data["is_finished"] = match["matchIsFinished"]
    for result in match["matchResults"]:
        if result["resultTypeKind"] == "After90Minutes":
            match_data['home_goals'] = result['pointsTeam1']
            match_data['away_goals'] = result["pointsTeam2"]
    matches_normalized.append(match_data)

# print(matches_normalized) 
matches_missing_score = 0
unique_id = set()
invalid_goals = []
finished_missing_score = []
for match_data in matches_normalized:
    if match_data["home_goals"] is None or match_data["away_goals"] is None:
        matches_missing_score += 1
    unique_id.add(match_data["source_match_id"])
    if (match_data["home_goals"] is not None and match_data["home_goals"] < 0) or (match_data["away_goals"] is not None and match_data["away_goals"] < 0):
        invalid_goals.append(match_data['source_match_id'])
    if (match_data["is_finished"] == True) and (match_data["home_goals"] is None or match_data["away_goals"] is None):
        finished_missing_score.append(match_data["source_match_id"])
# print(f"Количество матчей из API: {len(data_json)}")
# print(f"Количество матчей после нормализации: {len(matches_normalized)}")
# print(f"Количество пропущенных значений: {matches_missing_score}")
# print(f"Количество уникальных id:{len(unique_id)}")
# print(f"Матчи с некорректными голами:{invalid_goals}")
# print(f"Завершенные матчи с пустыми голами: {finished_missing_score}")

teams_openligadb = {}

for matches in matches_normalized:
    teams_openligadb[matches['home_team_id']] = matches['home_team_name']
    teams_openligadb[matches['away_team_id']] = matches['away_team_name']

