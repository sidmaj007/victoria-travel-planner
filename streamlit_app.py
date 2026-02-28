import streamlit as st
import anthropic
import requests
from datetime import datetime, date

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Victoria Travel Planner",
    page_icon="🗺️",
    layout="centered"
)

st.title("🗺️ Victoria Travel Planner")
st.caption("Your AI travel assistant for Melbourne & Regional Victoria")

# ============================================================
# API KEY — reads from Streamlit secrets (safe, not hardcoded)
# ============================================================

try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error("⚠️ API key not found. Add it to `.streamlit/secrets.toml` or Streamlit Cloud secrets.")
    st.stop()

# ============================================================
# TOOL 1: GET WEATHER
# ============================================================

locations_coords = {
    "melbourne":        {"lat": -37.8136, "lon": 144.9631},
    "mornington":       {"lat": -38.2167, "lon": 145.0333},
    "phillip island":   {"lat": -38.4833, "lon": 145.2333},
    "healesville":      {"lat": -37.6500, "lon": 145.5167},
    "yarra valley":     {"lat": -37.7833, "lon": 145.5667},
    "dandenong ranges": {"lat": -37.8833, "lon": 145.3667},
    "ballarat":         {"lat": -37.5622, "lon": 143.8503},
    "geelong":          {"lat": -38.1499, "lon": 144.3617},
    "great ocean road": {"lat": -38.6667, "lon": 143.5000},
    "lorne":            {"lat": -38.5500, "lon": 143.9833},
    "apollo bay":       {"lat": -38.7500, "lon": 143.6667},
    "torquay":          {"lat": -38.3333, "lon": 144.3167},
    "bendigo":          {"lat": -36.7570, "lon": 144.2794},
    "castlemaine":      {"lat": -37.0667, "lon": 144.2167},
    "daylesford":       {"lat": -37.3500, "lon": 144.1333},
    "macedon ranges":   {"lat": -37.3667, "lon": 144.5667},
    "wilson promontory":{"lat": -38.9500, "lon": 146.3667},
}

def get_weather(location: str) -> str:
    key = location.lower().strip()
    coords = locations_coords.get(key)
    if not coords:
        for name, c in locations_coords.items():
            if key in name or name in key:
                coords = c
                break
    if not coords:
        return f"Location '{location}' not found."

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "current": "temperature_2m,apparent_temperature,precipitation,weathercode,windspeed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,precipitation_probability_max",
        "timezone": "Australia/Melbourne",
        "forecast_days": 7
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        current = data["current"]
        daily = data["daily"]
        weather_codes = {
            0: "Clear sky ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅",
            3: "Overcast ☁️", 45: "Foggy 🌫️", 51: "Light drizzle 🌦️",
            61: "Light rain 🌧️", 63: "Rain 🌧️", 65: "Heavy rain 🌧️",
            71: "Light snow ❄️", 80: "Showers 🌦️", 95: "Thunderstorm ⛈️"
        }
        condition = weather_codes.get(current["weathercode"], "Variable")
        result = f"Weather in {location.title()}:\n"
        result += f"  Now: {condition}, {current['temperature_2m']}°C (feels {current['apparent_temperature']}°C)\n\n"
        result += "  7-Day Forecast:\n"
        for i in range(7):
            d = datetime.fromisoformat(daily["time"][i]).strftime("%a %d %b")
            cond = weather_codes.get(daily["weathercode"][i], "Variable")
            rain_prob = daily["precipitation_probability_max"][i]
            result += f"  {d}: {cond} | {daily['temperature_2m_min'][i]}–{daily['temperature_2m_max'][i]}°C | Rain: {rain_prob}%\n"
        return result
    except Exception as e:
        return f"Weather fetch error: {e}"


# ============================================================
# TOOL 2: GET PUBLIC HOLIDAYS
# ============================================================

def get_public_holidays() -> str:
    try:
        import datetime as dt
        year = date.today().year
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/AU"
        resp = requests.get(url, timeout=10)
        all_holidays = resp.json()
        vic_holidays = [
            h for h in all_holidays
            if h.get("global") or "VIC" in (h.get("counties") or [])
        ]
        today = date.today()
        result = f"Victoria Public Holidays {year}:\n\n"
        long_weekends = []
        for h in vic_holidays:
            holiday_date = date.fromisoformat(h["date"])
            if holiday_date < today:
                continue
            day_of_week = holiday_date.weekday()
            days_away = (holiday_date - today).days
            long_weekend_note = ""
            if day_of_week == 0:
                long_weekend_note = "🎉 LONG WEEKEND (Sat–Mon)"
                long_weekends.append({
                    "name": h["localName"],
                    "start": str(holiday_date - dt.timedelta(days=2)),
                    "end": h["date"],
                    "days_away": days_away
                })
            elif day_of_week == 4:
                long_weekend_note = "🎉 LONG WEEKEND (Fri–Sun)"
                long_weekends.append({
                    "name": h["localName"],
                    "start": h["date"],
                    "end": str(holiday_date + dt.timedelta(days=2)),
                    "days_away": days_away
                })
            result += f"  {h['date']} ({holiday_date.strftime('%A')}): {h['localName']} {long_weekend_note}\n"
            if days_away <= 60:
                result += f"    → {days_away} days away\n"
        if long_weekends:
            result += "\n📅 Upcoming Long Weekends:\n"
            for lw in long_weekends[:3]:
                result += f"  {lw['name']}: {lw['start']} to {lw['end']} ({lw['days_away']} days away)\n"
        return result
    except Exception as e:
        return f"Holiday fetch error: {e}"


# ============================================================
# TOOL 3: TRAVEL SUGGESTIONS
# ============================================================

DESTINATIONS = [
    {"name": "Dandenong Ranges", "type": "Nature & hiking", "distance_hours": 1, "trip_type": ["day trip"], "seasons": ["all"], "budget_per_night": 0, "crowd_level": "medium", "highlights": "Fern gullies, Sherbrooke Forest, Puffing Billy, Mt Dandenong lookout", "tips": "Go early morning on weekdays. Free entry to forests.", "best_for": "Couples, nature lovers"},
    {"name": "Wilson's Promontory", "type": "Nature & hiking", "distance_hours": 2.5, "trip_type": ["overnight"], "seasons": ["spring", "summer", "autumn"], "budget_per_night": 50, "crowd_level": "low", "highlights": "Coastal hikes, secluded beaches, wildlife, Tidal River", "tips": "Book campsites ahead. Huts ~$50/night. Quiet midweek.", "best_for": "Hikers, nature lovers"},
    {"name": "Healesville & Yarra Valley", "type": "Nature & hiking / Food & wine", "distance_hours": 1, "trip_type": ["day trip", "overnight"], "seasons": ["all"], "budget_per_night": 150, "crowd_level": "medium", "highlights": "Healesville Sanctuary, wineries, forest walks", "tips": "Plenty of budget Airbnbs. Avoid school holidays.", "best_for": "Couples, foodies"},
    {"name": "Macedon Ranges", "type": "Nature & hiking / Towns & culture", "distance_hours": 1, "trip_type": ["day trip", "overnight"], "seasons": ["autumn", "spring", "winter"], "budget_per_night": 130, "crowd_level": "low", "highlights": "Mount Macedon, Hanging Rock, heritage towns", "tips": "Less touristy than Yarra Valley. Great autumn foliage.", "best_for": "Couples, history buffs"},
    {"name": "Mornington Peninsula", "type": "Beaches & coastal", "distance_hours": 1.5, "trip_type": ["day trip", "overnight"], "seasons": ["summer", "autumn", "spring"], "budget_per_night": 180, "crowd_level": "high", "highlights": "Ocean and bay beaches, hot springs, wineries", "tips": "Go mid-week to avoid crowds. Hot springs worth it.", "best_for": "Couples, beach lovers"},
    {"name": "Phillip Island", "type": "Beaches & coastal / Nature & hiking", "distance_hours": 1.5, "trip_type": ["overnight"], "seasons": ["all"], "budget_per_night": 150, "crowd_level": "medium", "highlights": "Penguin Parade, Nobbies, surf beaches, koalas", "tips": "Book Penguin Parade online. Quieter in winter.", "best_for": "Couples, wildlife lovers"},
    {"name": "Great Ocean Road (Torquay to Lorne)", "type": "Beaches & coastal / Nature & hiking", "distance_hours": 1.5, "trip_type": ["day trip", "overnight"], "seasons": ["summer", "autumn", "spring"], "budget_per_night": 160, "crowd_level": "medium", "highlights": "Surf beaches, Bells Beach, coastal walks, charming towns", "tips": "Torquay and Anglesea less crowded than Lorne.", "best_for": "Beach lovers, couples"},
    {"name": "Apollo Bay & Otways", "type": "Beaches & coastal / Nature & hiking", "distance_hours": 2.5, "trip_type": ["overnight"], "seasons": ["all"], "budget_per_night": 140, "crowd_level": "low", "highlights": "Rainforest walks, waterfalls, quiet beach town, fresh seafood", "tips": "Much quieter than the main GOR stretch.", "best_for": "Couples wanting quiet escape"},
    {"name": "Daylesford & Hepburn Springs", "type": "Food & wine / Towns & culture", "distance_hours": 1.5, "trip_type": ["overnight"], "seasons": ["all"], "budget_per_night": 170, "crowd_level": "medium", "highlights": "Mineral springs, spa country, artisan food, galleries", "tips": "Very romantic. Hepburn Bathhouse is a must.", "best_for": "Couples, foodies, wellness"},
    {"name": "Yarra Valley Wineries", "type": "Food & wine", "distance_hours": 1, "trip_type": ["day trip"], "seasons": ["all"], "budget_per_night": 0, "crowd_level": "medium", "highlights": "World-class pinot noir, cellar doors, cheese, chocolate", "tips": "De Bortoli, Domaine Chandon great value. Go weekdays.", "best_for": "Wine lovers, foodies"},
    {"name": "Castlemaine & Bendigo", "type": "Towns & culture / Food & wine", "distance_hours": 1.5, "trip_type": ["overnight"], "seasons": ["all"], "budget_per_night": 120, "crowd_level": "low", "highlights": "Gold rush history, architecture, art galleries, great food", "tips": "Bendigo Art Gallery is free. Very budget friendly.", "best_for": "Culture lovers, couples"},
    {"name": "Ballarat", "type": "Towns & culture", "distance_hours": 1.5, "trip_type": ["day trip", "overnight"], "seasons": ["all"], "budget_per_night": 110, "crowd_level": "low", "highlights": "Sovereign Hill, art gallery, Wildlife Park", "tips": "Sovereign Hill excellent value. Very affordable stays.", "best_for": "History lovers, couples"},
]

def get_travel_suggestions(trip_type: str, season: str, max_budget: int = 200, interests: str = "all") -> str:
    season = season.lower().strip()
    trip_type = trip_type.lower().strip()
    results = []
    for dest in DESTINATIONS:
        if dest["distance_hours"] > 2.5:
            continue
        if "all" not in dest["seasons"] and season not in dest["seasons"]:
            continue
        if trip_type not in ["any", "all"]:
            if not any(trip_type in t for t in dest["trip_type"]):
                continue
        if dest["budget_per_night"] > max_budget:
            continue
        if dest["crowd_level"] == "high":
            continue
        results.append(dest)
    if not results:
        return "No destinations found. Try relaxing filters."
    output = f"Matching destinations ({trip_type}, {season}, ≤${max_budget}/night, low-medium crowds):\n\n"
    for d in results:
        cost = "Free/day trip" if d["budget_per_night"] == 0 else f"~${d['budget_per_night']}/night"
        output += f"📍 {d['name']}\n"
        output += f"   Type: {d['type']}\n"
        output += f"   Drive: ~{d['distance_hours']} hrs from Melbourne\n"
        output += f"   Cost: {cost}\n"
        output += f"   Crowd level: {d['crowd_level'].title()}\n"
        output += f"   Highlights: {d['highlights']}\n"
        output += f"   💡 Tip: {d['tips']}\n\n"
    return output


# ============================================================
# TOOLS DEFINITION
# ============================================================

tools = [
    {
        "name": "get_weather",
        "description": "Gets current weather and 7-day forecast for a location in Victoria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City or region name e.g. 'Melbourne', 'Yarra Valley'"}
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_public_holidays",
        "description": "Gets Victoria's public holidays and identifies upcoming long weekends.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_travel_suggestions",
        "description": "Gets curated Victorian travel destinations filtered by trip type, season, budget and crowd level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trip_type": {"type": "string", "description": "'day trip', 'overnight', or 'any'"},
                "season": {"type": "string", "description": "'summer', 'autumn', 'winter', or 'spring'"},
                "max_budget": {"type": "integer", "description": "Max budget per night AUD"},
                "interests": {"type": "string", "description": "Comma separated interests"}
            },
            "required": ["trip_type", "season"]
        }
    }
]

SYSTEM_PROMPT = """You are a friendly Victorian travel planner for a couple based in Melbourne.

You have 3 tools: get_weather, get_public_holidays, get_travel_suggestions.

When asked for travel plans:
- Check public holidays first to find long weekends
- Check weather for Melbourne and destinations
- Get travel suggestions filtered by season and budget
- Synthesize into a structured plan

Always format your final response with these sections:
🗓️ BEST TRAVEL WINDOWS
🌤️ WEATHER SUMMARY
📍 RECOMMENDED DESTINATIONS
🗺️ SAMPLE ITINERARY
💰 BUDGET ESTIMATE (for a couple)
💡 INSIDER TIPS

Keep it practical, budget-conscious (max $200/night), avoid overcrowded places."""


# ============================================================
# AGENT LOGIC
# ============================================================

def run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_weather":
        return get_weather(tool_input["location"])
    elif tool_name == "get_public_holidays":
        return get_public_holidays()
    elif tool_name == "get_travel_suggestions":
        return get_travel_suggestions(
            trip_type=tool_input.get("trip_type", "any"),
            season=tool_input.get("season", "all"),
            max_budget=tool_input.get("max_budget", 200),
            interests=tool_input.get("interests", "all")
        )
    return "Unknown tool"


def run_agent(user_message: str, conversation_history: list) -> str:
    conversation_history.append({"role": "user", "content": user_message})

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=conversation_history
        )

        if response.stop_reason == "tool_use":
            conversation_history.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            conversation_history.append({"role": "user", "content": tool_results})
        else:
            final_text = "".join(block.text for block in response.content if hasattr(block, "text"))
            conversation_history.append({"role": "assistant", "content": final_text})
            return final_text


# ============================================================
# STREAMLIT UI
# ============================================================

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# Suggested prompts shown at the start
if not st.session_state.messages:
    st.markdown("**Try asking:**")
    cols = st.columns(2)
    suggestions = [
        "Plan me a long weekend trip 🗓️",
        "Best coastal overnight trip? 🏖️",
        "Day trip for nature & hiking 🌿",
        "Any long weekends coming up? 📅"
    ]
    for i, suggestion in enumerate(suggestions):
        if cols[i % 2].button(suggestion):
            st.session_state.pending_input = suggestion

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle suggested prompt button clicks
if "pending_input" in st.session_state:
    prompt = st.session_state.pop("pending_input")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("🤔 Planning your trip..."):
            response = run_agent(prompt, st.session_state.conversation_history)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# Chat input
if prompt := st.chat_input("Ask me about your next Victorian getaway..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("🤔 Planning your trip..."):
            response = run_agent(prompt, st.session_state.conversation_history)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
