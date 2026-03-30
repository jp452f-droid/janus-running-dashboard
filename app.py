import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# =========================
# 🎨 NEON UI STYLE
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a, #020617);
    color: white;
}

h1 {
    color: #00f5ff;
    text-shadow: 0 0 15px #00f5ff;
}

h2, h3 {
    color: #ff00ff;
    text-shadow: 0 0 10px #ff00ff;
}

[data-testid="metric-container"] {
    background: linear-gradient(135deg, #111827, #020617);
    border: 1px solid #00f5ff;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 0 20px rgba(0, 245, 255, 0.2);
}

[data-testid="metric-container"] label {
    color: #00f5ff;
}

.js-plotly-plot {
    border-radius: 12px;
    box-shadow: 0 0 25px rgba(255, 0, 255, 0.2);
}

details {
    border: 1px solid #ff00ff;
    border-radius: 10px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 🔑 SECRETS
# =========================
CLIENT_ID = "218387"
CLIENT_SECRET = "8a9c83285b07d6ea26e6640d0fea8d90c87c7c14"
REFRESH_TOKEN = "75f956afd3c6b740cef3cf3c0b42a731b41d6009"

# =========================
# 🔄 TOKEN
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
# 📥 DATA
# =========================
def get_activities(token):
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    return res.json()

# =========================
# 🧠 LOGIC
# =========================
def classify_run(pace):
    if pace > 8:
        return "Recovery"
    elif pace > 6.5:
        return "Easy"
    else:
        return "Hard"

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
# 🔑 AUTH
# =========================
access_token = refresh_access_token()

if not access_token:
    st.error("❌ Token error")
    st.stop()

# =========================
# 📥 LOAD DATA
# =========================
data = get_activities(access_token)

if not isinstance(data, list) or len(data) == 0:
    st.error("No activity data")
    st.stop()

df = pd.DataFrame(data)

if "type" in df.columns:
    df = df[df["type"] == "Run"]
elif "sport_type" in df.columns:
    df = df[df["sport_type"] == "Run"]

df["distance_km"] = df["distance"] / 1000
df["time_min"] = df["moving_time"] / 60
df = df[df["distance_km"] > 0]

df["pace"] = df["time_min"] / df["distance_km"]
df["start_date_local"] = pd.to_datetime(df["start_date_local"])
# =========================
# 📊 PROGRESS DATA
# =========================

df_progress = df.copy()

# Sort oldest → newest
df_progress = df_progress.sort_values("start_date_local")

# Rolling pace (smooth trend)
df_progress["pace_rolling"] = df_progress["pace"].rolling(5).mean()

# Estimate 5K time
df_progress["est_5k"] = df_progress["pace"] * 5

# Weekly grouping
df_progress["week"] = df_progress["start_date_local"].dt.to_period("W").astype(str)

weekly = df_progress.groupby("week").agg({
    "distance_km": "sum",
    "pace": "mean"
}).reset_index()
df = df.sort_values("start_date_local", ascending=False)

latest = df.iloc[0]

run_type = classify_run(latest["pace"])
next_type, duration, pace_range, shoe = get_recommendation(
    latest["pace"],
    latest["distance_km"]
)

# =========================
# 📊 METRICS
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Distance (km)", f"{latest['distance_km']:.2f}")
col2.metric("Pace", f"{latest['pace']:.2f} /km")
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
    template="plotly_dark"
)

fig.update_traces(line=dict(color="#00f5ff", width=3))

st.plotly_chart(fig)

st.subheader("📈 Pace Progress")

fig_pace = px.line(
    df_progress.tail(30),
    x="start_date_local",
    y="pace_rolling",
    template="plotly_dark"
)

fig_pace.update_traces(line=dict(color="#ff00ff", width=3))

st.plotly_chart(fig_pace)

st.subheader("📊 Weekly Distance")

fig_week = px.bar(
    weekly.tail(8),
    x="week",
    y="distance_km",
    template="plotly_dark"
)

fig_week.update_traces(marker_color="#00f5ff")

st.plotly_chart(fig_week)

st.subheader("🔥 5K Progress Trend")

fig_5k = px.line(
    df_progress.tail(30),
    x="start_date_local",
    y="est_5k",
    template="plotly_dark"
)

fig_5k.update_traces(line=dict(color="#39ff14", width=3))

st.plotly_chart(fig_5k)

# =========================
# 🧠 PROGRESS STATUS
# =========================

recent = df_progress.tail(5)["pace"].mean()
previous = df_progress.tail(10).head(5)["pace"].mean()

if recent < previous:
    status = "🔥 Improving"
elif recent > previous:
    status = "⚠️ Slowing"
else:
    status = "➖ Stable"

st.subheader("🧠 Progress Status")
st.write(status)
# =========================
# 🧠 EXTRA STATS
# =========================
last5 = df.head(5)
avg_pace_5 = last5["pace"].mean()

df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors="coerce")

today = pd.Timestamp.now()

last_7_days = df[
    df["start_date_local"].notna() &
    (df["start_date_local"] > (today - pd.Timedelta(days=7)))
]

weekly_km = last_7_days["distance_km"].sum()

avg_hr = latest.get("average_heartrate")
if avg_hr and avg_hr > 200:
    avg_hr = None

VO2_MAX = 41
GOAL_5K = "Sub 30 min"

# =========================
# 📊 PERFORMANCE
# =========================
st.subheader("⚡ Performance Overview")

col4, col5, col6, col7 = st.columns(4)

col4.metric("Avg Pace (Last 5)", f"{avg_pace_5:.2f} /km")
col5.metric("Weekly Distance", f"{weekly_km:.2f} km")
col6.metric("Avg HR", f"{avg_hr:.0f} bpm" if avg_hr else "N/A")
col7.metric("VO2 Max", VO2_MAX)
# =========================
# 📅 NEXT RUN DATE LOGIC
# =========================

from datetime import timedelta

last_run_date = latest["start_date_local"]

if run_type == "Hard":
    next_run_date = last_run_date + timedelta(days=2)
elif run_type == "Easy":
    next_run_date = last_run_date + timedelta(days=1)
else:
    next_run_date = last_run_date + timedelta(days=1)

next_run_str = next_run_date.strftime("%A, %b %d")
# =========================
# 🎯 RECOMMENDATION
# =========================
st.subheader("⚡ Next Run Recommendation")

colA, colB = st.columns(2)

colA.write(f"⚡ Type: {next_type}")
colA.write(f"🔥 Duration: {duration}")

colB.write(f"💜 Pace Target: {pace_range}")
colB.write(f"👟 Shoe: {shoe}")
st.subheader("📅 Next Run Schedule")

st.write(f"🗓 Next Run: **{next_run_str}**")
# =========================
# 🎯 GOAL
# =========================
st.subheader("🎯 Goal")

st.write(f"🏁 5K Goal: {GOAL_5K}")

estimated_5k = latest["pace"] * 5
st.write(f"📈 Estimated 5K: {estimated_5k:.1f} min")

# =========================
# 🔍 DEBUG
# =========================
with st.expander("Debug Data"):
    st.write(df.head())