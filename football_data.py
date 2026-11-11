import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

api_token = os.getenv("API_football_token")

if not api_token:
    raise ValueError("API токен не получен")
    
headers = {
    "X-Auth-Token": api_token
}

response = requests.get("https://api.football-data.org/v4/competitions/BL1/matches?season=2025", headers = headers, timeout=15)

response.raise_for_status()


json_data = response.json()
# print(type(json_data))
# print(json_data.keys())

# print(first_match)

match_normalized = []
for match in json_data["matches"]:
    match_data = {}
    match_data['source'] = 'football_data'
    match_data['source_match_id'] = match['id']
    match_data['match_datetime_utc'] = datetime.fromisoformat(match['utcDate'])
    match_data['home_team_id'] = match['homeTeam']['id']
    match_data['home_team_name'] = match['homeTeam']['name']
    match_data['away_team_id'] = match['awayTeam']['id']
    match_data['away_team_name'] = match['awayTeam']['name']
    match_data['home_goals'] = match['score']['fullTime']['home']
    match_data['away_goals'] = match['score']['fullTime']['away']
    match_data['status'] = match['status']
    match_data['is_finished'] = match['status'] == 'FINISHED'
    match_normalized.append(match_data)


teams_football_data = {}
for matches in match_normalized:
    teams_football_data[matches['home_team_id']] = matches['home_team_name']
    teams_football_data[matches['away_team_id']] = matches['away_team_name']

