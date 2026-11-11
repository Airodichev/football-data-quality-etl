from openligadb import teams_openligadb
from football_data import teams_football_data

team_mapping = {}
unmatched_teams = {}

for team_id, team_name in teams_openligadb.items():
    for team_id_data, team_name_data in teams_football_data.items():
        if team_name == team_name_data:
            team_mapping[team_id] = team_id_data
            break

for team_id, team_name in teams_openligadb.items():
    if team_id not in team_mapping:
        unmatched_teams[team_id] = team_name 



team_aliases = {
    "TSG Hoffenheim": "TSG 1899 Hoffenheim",
    "FC St. Pauli": "FC St. Pauli 1910"
}

for team_id, team_name in unmatched_teams.items():

    alias_name = team_aliases.get(team_name)

    if alias_name is None:
        continue

    for team_id_data, team_name_data in teams_football_data.items():

        if alias_name == team_name_data:
            team_mapping[team_id] = team_id_data
            break



unmatched_teams = {}

for team_id, team_name in teams_openligadb.items():
    if team_id not in team_mapping:
        unmatched_teams[team_id] = team_name

