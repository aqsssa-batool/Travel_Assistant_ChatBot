import os
from datetime import date, timedelta
from urllib.parse import quote
import requests
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# ==========Page Config===========

st.set_page_config(
    page_title="Trippy AI",
    page_icon="🌍",
    layout="wide"
)

load_dotenv()
api_key = os.getenv("ChatBotKey")
client = Groq(api_key=api_key)
MODEL = "openai/gpt-oss-120b"

st.title("🌍 Trippy AI")
st.subheader("✦ Your Smart Companion for Every Journey.✦")
st.write("🗺️ Discover Destinations • 📍 Explore Places • 🧳 Plan Adventures")

SYSTEM_PROMPT = """
You are Trippy AI, a friendly personal AI travel assistant.

Rules:
1. Ask for the destination first.
2. Next ask for trip duration and number of travelers.
3. Ask for the budget after collecting 2–3 trip details.
4. Reply in Roman Urdu if the user writes in Roman Urdu.
5. Use the conversation history to remember details and do not repeat questions
   the user has already answered.
6. Create personalized day-by-day itineraries when enough details are available.
7. Respect the user's budget, dates, travelers, and preferences.
8. Show budgets in Pakistani rupees (PKR) unless the user asks otherwise.
9. Label costs as estimates unless they have been verified.
10. Never invent live prices, bookings, weather, or availability.
11. Adapt plans when the user changes requirements and preserve unaffected details.
12. Ask only one or two questions at a time.
13. Use simple language and helpful headings.
14. Use actual weather data only when it is supplied by the app.
15. Flight and hotel search links open external websites. Never claim that a booking
    has been completed.
16.Answer questions about every country in the world and its cities, including travel destinations, 
   attractions, culture, weather, transportation, accommodation, and estimated travel budgets. 
   Never restrict answers to specific countries; provide helpful, accurate information about any country or city the user asks about.
"""

# *********** SIDEBAR **********
# ========== Travel Missions ===========
missions = {
    "Find My Destination": (
        "Recommend three destinations based on my interests, trip duration, "
        "and budget in PKR."
    ),
    "Plan My Budget": (
        "Create a realistic trip budget in PKR, including transport, accommodation, "
        "food, activities, and extra expenses. Label costs as estimates."
    ),
    "Build My Itinerary": (
        "Create a practical day-by-day itinerary with attractions, estimated travel "
        "times, activities, meals, and costs."
    ),
    "Find Flights & Hotels": (
        "Help me prepare flight and hotel searches using my origin, destination, "
        "dates, travelers, and budget. Explain that links open external websites."
    ),
    "Weather & Travel Advice": (
        "Give weather-aware travel advice. Use actual weather data only if it is "
        "provided in the conversation; otherwise ask the user to check the Weather tab."
    ),
    "Change My Travel Plan": (
        "Update the existing itinerary when budget, dates, destination, weather, "
        "or activities change. Preserve all unaffected details."
    ),
}

st.sidebar.caption("Your personal AI travel planner")
st.sidebar.divider()
st.sidebar.markdown("### Choose your travel service")

mission = st.sidebar.radio(
    "Travel service",
    options=list(missions.keys()),
    label_visibility="collapsed",
)

planning_stage = st.sidebar.selectbox(
    "⏳ Planning stage",
    [
        " Just exploring ideas",
        " Planning ahead",
        " Ready to travel soon",
    ],
)

if st.sidebar.button("🚀 Activate Travel Service", type="primary", use_container_width=True):
    st.session_state["travel_mission"] = {
        "mission": mission,
        "instruction": missions[mission],
        "planning_stage": planning_stage,
    }
    st.sidebar.success("Travel service activated!")

active_mission = st.session_state.get("travel_mission")
if active_mission:
    st.sidebar.caption(f"Active: {active_mission['mission']}")

if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()

# ============ Travel Command Center ============

st.divider()
st.markdown("🧭 Travel Command Center")
weather_tab, flight_tab, hotel_tab = st.tabs(
    ["🌦️ Weather", "✈️ Flights", "🏨 Hotels"]
)

# ============== WEATHER FUNCTION ==============

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}

def get_weather(city):
    """Return current weather and a 7-day forecast for a city."""
    try:
        geo_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=15,
        )
        geo_response.raise_for_status()
        places = geo_response.json().get("results", [])

        if not places:
            return None, f"Could not find the location: {city}. Check the spelling."

        place = places[0]
        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "precipitation,weather_code,wind_speed_10m"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "forecast_days": 7,
                "timezone": "auto",
            },
            timeout=15,
        )
        weather_response.raise_for_status()
        data = weather_response.json()

        current = data["current"]
        daily = data["daily"]

        result = {
            "location": f"{place['name']}, {place.get('country', '')}",
            "temperature": current["temperature_2m"],
            "feels_like": current["apparent_temperature"],
            "humidity": current["relative_humidity_2m"],
            "wind": current["wind_speed_10m"],
            "precipitation": current["precipitation"],
            "condition": WEATHER_CODES.get(current["weather_code"], "Unknown"),
            "forecast": [],
        }

        for index, forecast_date in enumerate(daily["time"]):
            result["forecast"].append(
                {
                    "date": forecast_date,
                    "condition": WEATHER_CODES.get(
                        daily["weather_code"][index], "Unknown"
                    ),
                    "max": daily["temperature_2m_max"][index],
                    "min": daily["temperature_2m_min"][index],
                    "rain_chance": daily["precipitation_probability_max"][index],
                }
            )

        return result, None

    except requests.RequestException:
        return None, "The weather service could not be reached. Please try again."
    except (KeyError, ValueError, IndexError, TypeError):
        return None, "Weather data could not be processed. Please try again."


# ============= Weather Tab ================

with weather_tab:
    st.markdown("Destination Weather")
    st.write("Check current conditions and the next 7 days.")

    with st.form("weather_form"):
        weather_city = st.text_input(
            "Destination city",
            placeholder="e.g. Murree, Islamabad, Istanbul",
        )
        weather_submit = st.form_submit_button("Check Weather", type="primary")

    if weather_submit:
        if not weather_city.strip():
            st.warning("Please enter a destination city.")
        else:
            with st.spinner("Fetching weather data..."):
                weather, error = get_weather(weather_city.strip())

            if error:
                st.warning(error)
            elif weather:
                st.subheader(f"📍 {weather['location']}")
                col1, col2, col3 = st.columns(3)
                col1.metric("🌡️ Temperature", f"{weather['temperature']} °C")
                col2.metric("🤗 Feels like", f"{weather['feels_like']} °C")
                col3.metric("💨 Wind", f"{weather['wind']} km/h")

                st.write(f"**Conditions:** {weather['condition']}")
                st.write(f"**Humidity:** {weather['humidity']}%")
                st.write(
                    f"**Current precipitation:** {weather['precipitation']} mm"
                )
                st.subheader("📅 7-Day Forecast")

                for day in weather["forecast"]:
                    with st.container(border=True):
                        st.write(f"**{day['date']} — {day['condition']}**")
                        st.write(f"🌡️ {day['min']}°C to {day['max']}°C")
                        st.write(
                            f"🌧️ Precipitation probability: {day['rain_chance']}%"
                        )

                st.caption("Weather data provided by Open-Meteo. Forecasts may change.")

# =========== Flights Tab ============

with flight_tab:
    st.markdown("Explore Flights")
    st.write("Create a search and view results on an external flight-search website.")

    with st.form("flight_form"):
        col1, col2 = st.columns(2)

        with col1:
            origin = st.text_input(
                "Departure city or airport",
                placeholder="e.g. Karachi",
            )
            departure_date = st.date_input(
                "Departure date",
                value=date.today() + timedelta(days=7),
                min_value=date.today(),
                key="flight_departure",
            )

        with col2:
            destination = st.text_input(
                "Destination city or airport",
                placeholder="e.g. Skardu",
            )
            return_date = st.date_input(
                "Return date",
                value=date.today() + timedelta(days=10),
                min_value=date.today(),
                key="flight_return",
            )

        passengers = st.number_input(
            "Passengers", min_value=1, max_value=20, value=1, step=1
        )
        flight_submit = st.form_submit_button("🔎 Search Flights", type="primary")

    if flight_submit:
        if not origin.strip() or not destination.strip():
            st.warning("Enter both departure and destination cities.")
        elif return_date < departure_date:
            st.warning("Return date must be on or after the departure date.")
        else:
            query = (
                f"Flights from {origin.strip()} to {destination.strip()} "
                f"departing {departure_date.isoformat()}, returning "
                f"{return_date.isoformat()}, {int(passengers)} passengers"
            )
            flight_url = "https://www.google.com/travel/flights?q=" + quote(query)
            st.success("Your flight search is ready.")
            st.link_button(
                "✈️ View Flight Options",
                flight_url,
                use_container_width=True,
            )
            st.caption(
                "Check prices, baggage rules, and availability on the provider's site. "
                "RoamWise has not purchased a ticket."
            )


# ============ Chat History ==============

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_text = st.chat_input("Where would you love to travel?")

if user_text:
    st.session_state.messages.append({"role":"user","content":user_text})

    with st.chat_message("user"):
        st.markdown(user_text)

    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    active_mission = st.session_state.get("travel_mission")
    if active_mission:
        api_messages.append(
            {
                "role":"system",
                "content": (
                    f"Active travel service: {active_mission['mission']}\n"
                    f"Instructions: {active_mission['instruction']}\n"
                    f"Travel style: {active_mission}\n"
                    f"Planning stage: {active_mission['planning_stage']}\n"
                    "Apply these preferences without repeating questions already answered."
                ),
            }
        )

    api_messages.extend(st.session_state.messages)
    with st.chat_message("assistant"):
        with st.spinner("Planning your adventure..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=api_messages,
                    max_tokens=2000,
                )
                reply = response.choices[0].message.content or (
                    "Sorry, I could not create a response. Please try again."
                )
                st.markdown(reply)
                st.session_state.messages.append(
                    {"role":"assistant","content":reply}
                )
            except Exception as error:
                st.error(
                    "The chatbot could not get a response from Groq. "
                    "Check your internet connection, API key, and model name. "
                    f"Details: {error}"
                )

# ========== Hotel Tab ===========

with hotel_tab:
    st.markdown("Find Accommodation")
    st.write("Search for stays using your destination and dates.")

    with st.form("hotel_form"):
        hotel_city = st.text_input(
            "Hotel destination",
            placeholder="e.g. Hunza, Lahore, Dubai",
        )
        col1, col2 = st.columns(2)

        with col1:
            checkin = st.date_input(
                "Check-in",
                value=date.today() + timedelta(days=7),
                min_value=date.today(),
                key="hotel_checkin",
            )

        with col2:
            checkout = st.date_input(
                "Check-out",
                value=date.today() + timedelta(days=9),
                min_value=date.today(),
                key="hotel_checkout",
            )

        guests = st.number_input("Guests", min_value=1, max_value=30, value=2, step=1)
        rooms = st.number_input("Rooms", min_value=1, max_value=10, value=1, step=1)
        hotel_submit = st.form_submit_button("🔎 Search Hotels", type="primary")

    if hotel_submit:
        if not hotel_city.strip():
            st.warning("Please enter a hotel destination.")
        elif checkout <= checkin:
            st.warning("Check-out must be after check-in.")
        else:
            hotel_url = (
                "https://www.booking.com/searchresults.html?"
                f"ss={quote(hotel_city.strip())}"
                f"&checkin={checkin.isoformat()}"
                f"&checkout={checkout.isoformat()}"
                f"&group_adults={int(guests)}"
                f"&no_rooms={int(rooms)}"
            )
            st.success("Your hotel search is ready.")
            st.link_button(
                "🏨 View Hotel Options",
                hotel_url,
                use_container_width=True,
            )
            st.caption(
                "Confirm the final price, taxes, cancellation policy, and availability "
                "on the booking website."
            )


# ============ Footer ===========

st.divider()
st.caption(
    "Ask anything about Travel! "
)
