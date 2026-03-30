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
h1 { color: #00f5ff; text-shadow: 0 0 15px #00f5ff; }
h2, h3 { color: #ff00ff; text-shadow: 0 0 10px #ff00ff; }
[data-testid="metric-container"] {
    background: #020617;
    border: 1px solid #00f5ff;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 0 20px rgba(0,245,255,0.2);
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
    st.error("Token error")
    st.stop()

# =========================
# 📥 LOAD DATA
# =========================
data = get_activities(access_token)

if not isinstance(data, list) or len(data) == 0:
    st.error("No activity data")
    st.stop()

df = pd.DataFrame(data)

# =========================
# 🛠️ FILTER RUNS
# =========================
if "type" in df.columns:
    df = df[df["type"] == "Run"]
elif "sport_type" in df.columns:
    df = df[df["sport_type"] == "Run"]

df["distance_km"] = df["distance"] / 1000
df["time_min"] = df["moving_time"] / 60

df = df[df["distance_km"] > 0]
df["pace"] = df["time_min"] / df["distance_km"]

# FIX DATETIME
df["start_date_local"] = pd.to_datetime(df["start_date_local"], errors="coerce")

# 🔥 HANDLE BOTH CASES (WITH OR WITHOUT TIMEZONE)
if df["start_date_local"].dt.tz is not None:
    df["start_date_local"] = df["start_date_local"].dt.tz_convert(None)

df = df[df["start_date_local"].notna()]

# SORT
df = df.sort_values("start_date_local", ascending=False)

latest = df.iloc[0]

run_type = classify_run(latest["pace"])
next_type, duration, pace_range, shoe = get_recommendation(
    latest["pace"], latest["distance_km"]
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

# =========================
# 📊 PROGRESS DATA
# =========================
df_progress = df.sort_values("start_date_local")

df_progress["pace_rolling"] = df_progress["pace"].rolling(5).mean()
df_progress["est_5k"] = df_progress["pace"] * 5

st.subheader("📈 Pace Progress")

fig2 = px.line(
    df_progress.tail(30),
    x="start_date_local",
    y="pace_rolling",
    template="plotly_dark"
)
fig2.update_traces(line=dict(color="#ff00ff", width=3))
st.plotly_chart(fig2)

# =========================
# 📅 WEEKLY DISTANCE
# =========================
df_progress["week"] = df_progress["start_date_local"].dt.to_period("W").astype(str)

weekly = df_progress.groupby("week")["distance_km"].sum().reset_index()

st.subheader("📊 Weekly Distance")

fig3 = px.bar(
    weekly.tail(8),
    x="week",
    y="distance_km",
    template="plotly_dark"
)
fig3.update_traces(marker_color="#00f5ff")
st.plotly_chart(fig3)

# =========================
# 🧠 TRAINING LOGIC
# =========================
today = pd.Timestamp.now(tz=None).normalize()

last_7_days = df[
    df["start_date_local"] >= (today - pd.Timedelta(days=7))
]
weekly_km = last_7_days["distance_km"].sum() if not last_7_days.empty else 0

recent_runs = df.head(7)

training_load = (recent_runs["distance_km"] * recent_runs["pace"]).sum()

if training_load < 150:
    load_status = "🟢 Low"
elif training_load < 300:
    load_status = "🟡 Moderate"
else:
    load_status = "🔴 High"

recent_pace = recent_runs["pace"].mean()
baseline_pace = df.head(20)["pace"].mean()

fatigue_score = recent_pace / baseline_pace if baseline_pace else 1

if fatigue_score > 1.1:
    fatigue_status = "🔴 Fatigued"
elif fatigue_score > 1.05:
    fatigue_status = "🟡 Slight Fatigue"
else:
    fatigue_status = "🟢 Fresh"

last_run_date = latest["start_date_local"].date()
days_since_last = (today.date() - last_run_date).days

if fatigue_status == "🔴 Fatigued":
    decision = "❌ Rest Day"
elif days_since_last == 0:
    decision = "❌ Already Ran"
elif training_load > 300:
    decision = "⚠️ Easy or Rest"
else:
    decision = "✅ Good to Run"

# =========================
# 🧠 DISPLAY INTEL
# =========================
st.subheader("🧠 Training Intelligence")

c1, c2, c3 = st.columns(3)

c1.metric("Training Load", f"{training_load:.0f}", load_status)
c2.metric("Fatigue", fatigue_status)
c3.metric("Today", decision)

# =========================
# 📅 NEXT RUN DATE
# =========================
if fatigue_status == "🔴 Fatigued" or training_load > 300:
    next_run_date = latest["start_date_local"] + pd.Timedelta(days=2)
else:
    next_run_date = latest["start_date_local"] + pd.Timedelta(days=1)

next_run_str = next_run_date.strftime("%A, %b %d")

st.subheader("📅 Next Run")
st.write(f"🗓 {next_run_str}")

# =========================
# 🎯 RECOMMENDATION
# =========================
st.subheader("⚡ Next Run Plan")

cA, cB = st.columns(2)

cA.write(f"🏃 {next_type}")
cA.write(f"⏱ {duration}")

cB.write(f"⚡ {pace_range}")
cB.write(f"👟 {shoe}")

# =========================
# 🎯 GOAL
# =========================
st.subheader("🎯 Goal")

GOAL_5K = "Sub 30 min"
estimated_5k = latest["pace"] * 5

st.write(f"🏁 Goal: {GOAL_5K}")
st.write(f"📈 Estimated 5K: {estimated_5k:.1f} min")

# =========================
# DEBUG
# =========================
with st.expander("Debug Data"):
    st.write(df.head())