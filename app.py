import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# =========================
# 🔑 YOUR CREDENTIALS
# =========================
CLIENT_ID = "218387"
CLIENT_SECRET = "8a9c83285b07d6ea26e6640d0fea8d90c87c7c14"
REFRESH_TOKEN = "75f956afd3c6b740cef3cf3c0b42a731b41d6009"

# =========================
# 🔄 REFRESH TOKEN
# =========================
def refresh_access_token():
    url = "https://www.strava.com/oauth/token"

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }

    res = requests.post(url, data=payload)
    return res.json().get("access_token")

# =========================
# 📥 GET ACTIVITIES
# =========================
def get_activities(token):
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers)
    return res.json()

# =========================
# 🧠 CLASSIFY RUN
# =========================
def classify_run(pace):
    if pace > 8:
        return "Recovery"
    elif pace > 6.5:
        return "Easy"
    else:
        return "Hard"

# =========================
# 🧠 RECOMMENDATION ENGINE
# =========================
def get_recommendation(pace, distance):
    if pace > 8:
        return "Recovery Run", "20–25 mins", "8:30 – 9:30 /km", "Cloudmonster"

    elif pace > 6.5:
        if distance < 3:
            return "Easy Build Run", "25–30 mins", "7:30 – 8:15 /km", "Vomero"
        else:
            return "Easy Endurance Run", "30–40 mins", "7:30 – 8:00 /km", "Vomero"

    else:
        return "Hard Run", "20–25 mins", "6:00 – 7:00 /km", "Alphafly"

# =========================
# 🚀 UI
# =========================
st.set_page_config(page_title="Janus Dashboard", layout="wide")
st.title("🏃 Janus Running Dashboard")

# =========================
# 🔑 TOKEN
# =========================
access_token = refresh_access_token()

if not access_token:
    st.error("❌ Failed to refresh access token")
    st.stop()

# =========================
# 📥 DATA
# =========================
data = get_activities(access_token)

if not isinstance(data, list) or len(data) == 0:
    st.error("No activity data returned")
    st.write(data)
    st.stop()

df = pd.DataFrame(data)

# =========================
# 🛠️ FILTER RUNS
# =========================
if "type" in df.columns:
    df = df[df["type"] == "Run"]
elif "sport_type" in df.columns:
    df = df[df["sport_type"] == "Run"]
else:
    st.error("No activity type column found")
    st.write(df.columns)
    st.stop()

if df.empty:
    st.warning("No running activities found")
    st.stop()

# =========================
# 📊 METRICS CALC
# =========================
df["distance_km"] = df["distance"] / 1000
df["time_min"] = df["moving_time"] / 60

df = df[df["distance_km"] > 0]
df["pace"] = df["time_min"] / df["distance_km"]

df["start_date_local"] = pd.to_datetime(df["start_date_local"])

# Sort newest first
df = df.sort_values("start_date_local", ascending=False)

# Latest run
latest = df.iloc[0]

# =========================
# 🧠 EXTRA STATS
# =========================

# Avg pace last 5 runs
last5 = df.head(5)
avg_pace_5 = last5["pace"].mean()

# Weekly distance (last 7 runs approx)
weekly_km = df.head(7)["distance_km"].sum()

# Heart rate (if exists)
avg_hr = latest.get("average_heartrate", None)

# Manual VO2 max (edit anytime)
VO2_MAX = 41  # your current

# Goal (edit anytime)
GOAL_5K = "Sub 30 min"

# Classification
run_type = classify_run(latest["pace"])

# Recommendation
next_type, duration, pace_range, shoe = get_recommendation(
    latest["pace"],
    latest["distance_km"]
)

# =========================
# 📊 METRICS
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Distance (km)", f"{latest['distance_km']:.2f}")
col2.metric("Pace (min/km)", f"{latest['pace']:.2f}")
col3.metric("Run Type", run_type)

st.caption(f"Latest run: {latest['start_date_local'].strftime('%Y-%m-%d')}")

# =========================
# 📈 CHART
# =========================
df_chart = df.sort_values("start_date_local")

fig = px.line(
    df_chart.tail(20),
    x="start_date_local",
    y="distance_km",
    title="Distance Trend (Last 20 Runs)"
)

st.plotly_chart(fig)

# =========================
# 📊 PERFORMANCE STATS
# =========================
st.subheader("Performance Overview")

col4, col5, col6, col7 = st.columns(4)

col4.metric("Avg Pace (Last 5)", f"{avg_pace_5:.2f} /km")
col5.metric("Weekly Distance", f"{weekly_km:.2f} km")

if avg_hr:
    col6.metric("Avg HR", f"{avg_hr:.0f} bpm")
else:
    col6.metric("Avg HR", "N/A")

col7.metric("VO2 Max", VO2_MAX)

# =========================
# 🎯 RECOMMENDATION
# =========================
st.subheader("Next Run Recommendation")

colA, colB = st.columns(2)

colA.write(f"🏃 Type: {next_type}")
colA.write(f"⏱ Duration: {duration}")

colB.write(f"⚡ Pace Target: {pace_range}")
colB.write(f"👟 Shoe: {shoe}")

# =========================
# 🎯 GOAL
# =========================
st.subheader("Goal")

st.write(f"🎯 5K Goal: {GOAL_5K}")

# Estimate current 5K based on pace
estimated_5k = latest["pace"] * 5

st.write(f"📈 Estimated 5K Time: {estimated_5k:.1f} min")

# =========================
# 🔍 DEBUG
# =========================
with st.expander("Debug Data"):
    st.write(df.head())