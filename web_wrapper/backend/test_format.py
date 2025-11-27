from pathlib import Path
import json

# Mock the function from main.py
def construct_discord_payload(json_path: Path) -> dict:
    import json
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            players = json.load(f)
            
        if not players:
            return {"content": "No player info available."}

        # Group by relation
        teams = {}
        for player in players:
            relation = player.get('relation', 2)
            if relation not in teams:
                teams[relation] = []
            teams[relation].append(player)
            
        # Identify "Player In Render" (Neutral / Relation 2)
        main_players = teams.get(2, [])
        other_players = []
        for r, p_list in teams.items():
            if r != 2:
                other_players.extend(p_list)
        
        # Sort other players by name
        other_players.sort(key=lambda x: x.get('name', ''))

        embed = {
            "title": "Render Complete",
            "color": 0x57F287, # Discord Green
            "fields": []
        }

        # Field 1: Player In Render
        if main_players:
            names = [f"{p.get('name', 'Unknown')} ({p.get('ship', 'Unknown Ship')})" for p in main_players]
            embed["fields"].append({
                "name": "Player In Render",
                "value": "\n".join(names),
                "inline": False
            })
        else:
             embed["fields"].append({
                "name": "Player In Render",
                "value": "Unknown",
                "inline": False
            })

        # Field 2: Other Players
        if other_players:
            names = [p.get('name', 'Unknown') for p in other_players]
            value = ", ".join(names)
            if len(value) > 1024:
                value = value[:1021] + "..."
            
            embed["fields"].append({
                "name": "Other Players",
                "value": value,
                "inline": False
            })

        return {"embeds": [embed]}

    except Exception as e:
        print(f"Error formatting Discord message: {e}")
        return {"content": "Error formatting player info."}

# Create dummy JSON
dummy_data = [
    {"name": "Player1", "ship": "Yamato", "relation": 0, "clan": "CLAN1", "build_url": "http://example.com/build1"},
    {"name": "Player2", "ship": "Montana", "relation": 0, "clan": "", "build_url": ""},
    {"name": "Enemy1", "ship": "Shimakaze", "relation": 1, "clan": "BAD", "build_url": "http://example.com/build2"},
    {"name": "Hero", "ship": "Des Moines", "relation": 2, "clan": "GOOD", "build_url": ""},
]

json_path = Path("test_players.json")
with open(json_path, "w") as f:
    json.dump(dummy_data, f)

# Test formatting
payload = construct_discord_payload(json_path)
print(json.dumps(payload, indent=2))

# Cleanup
json_path.unlink()
