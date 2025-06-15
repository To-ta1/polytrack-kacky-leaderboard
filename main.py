import os, json, requests, threading, time
from datetime import datetime
from flask import Flask, render_template, redirect, url_for
import matplotlib.pyplot as plt
from matplotlib import ticker

app = Flask(__name__)

# -- Config --
track_names = ["Test Leaderboard Track #1", "Test Leaderboard Track #2"]
track_ids = [
  "9612eb2b9b37a7b053a86f55323e43a58ade7577122daa6d97ff9fec1e6c7038",
  "f231be762a3ff2930817c9458f17618f014305da03cb018335c9cc5953738c84"
]
track_codes = ["PolyTrack14pdFK3tCDCCGAA9ZSoB1lezpiWNyZ14zLXYNxeHEjq90P6c9BLz4VxmivcRqmwr1kgNvXfVTe8k3Bxywp8s6kdrxX8Bcef1fiLCSMJjuKGbNb4M8EpsdQ1JCaJaEDokPDesoFl4oboDB10bJnqq93HjPmANTZ7pWSHdSbsDbEZQrpGbLcEdXx20S4wvzVjHMDQLXD4CffgZVkzP", "PolyTrack14pdBBntlDBDAAA9XiiJxjas0oLxWK6bckEtpoB1kxXf5eWfaXx1oZEy3PM0dIdhmeX0ZFNTOlHqEXI2iXELN7EuBI9Df09kmTZz54Br1LD9tf6I3BvrsY33WVmmGfZzyBe2hmNguAwG3ZJwyqkSeWcA1zuAygZ57i5a7lOEHepUV0Io0ftIkozr9kZjcOd1oyTfR8txsxeuSNnQOwLzgaMOpHok7cPNwGG9uud6j8e4AffGk2FXYmOTjGEOJeUTVv8PefAr3WJ2A"]
HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# Fetch leaderboard JSON
def fetch_leaderboard(track_id):
    url = (
        f"https://vps.kodub.com:43273/leaderboard?"
        f"version=0.5.0&trackId={track_id}&skip=0&amount=500&onlyVerified=false"
        f"&userTokenHash=89b15d5cb1d07073894030b58ece6140fc3f357ad7dacf7ecbbe5a78440bf6f9"
    )
    return requests.get(url).json()

def update_all_data():
    for idx, track_id in enumerate(track_ids):
        data = fetch_leaderboard(track_id)
        entries = data.get("entries", [])
        timestamp = datetime.utcnow().isoformat()
        path = os.path.join(HISTORY_DIR, f"{idx}.json")
        history = json.load(open(path)) if os.path.exists(path) else {}
        for e in entries:
            uid, name, frames = e["userId"], e["name"], e["frames"]
            hist = history.setdefault(uid, {"name": name, "data": []})
            hist["data"].append([timestamp, frames / 1000])
        json.dump(history, open(path, "w"), indent=2)
        generate_graph(history, idx)

def generate_graph(history, idx):
    plt.figure(figsize=(12,6))
    ax = plt.gca()
    for info in history.values():
        times = [datetime.fromisoformat(t[0]) for t in info["data"]]
        vals = [t[1] for t in info["data"]]
        ax.plot(times, vals)
        ax.text(times[-1], vals[-1], info["name"], fontsize=8)
    ax.set_title(track_names[idx])
    ax.set_xlabel("Time")
    ax.set_ylabel("Run Time (s)")
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.3f"))
    plt.tight_layout()
    plt.savefig(f"static/leaderboard_{idx}.png")
    plt.close()

def generate_overall():
    overall = {}
    for idx in range(len(track_ids)):
        path = os.path.join(HISTORY_DIR, f"{idx}.json")
        if not os.path.exists(path): continue
        history = json.load(open(path))
        ranked = sorted(
            [(uid, info["name"], info["data"][-1][1]) for uid, info in history.items() if info["data"]],
            key=lambda x: x[2]
        )
        for place, (uid, name, _) in enumerate(ranked, start=1):
            data = overall.setdefault(uid, {"name": name, "maps_completed":0, "places":[]})
            data["maps_completed"] += 1
            data["places"].append(place)
    lb = [
        {"name": d["name"], "maps_completed": d["maps_completed"],
         "avg_place": sum(d["places"])/len(d["places"])}
        for d in overall.values()
    ]
    return sorted(lb, key=lambda x: (-x["maps_completed"], x["avg_place"]))

@app.route("/")
def home():
    return render_template("home.html", track_names=track_names)

@app.route("/track/<int:track_index>")
def track_page(track_index):
    if track_index >= len(track_ids): return "Invalid track", 404
    path = os.path.join(HISTORY_DIR, f"{track_index}.json")
    if not os.path.exists(path): update_all_data()
    history = json.load(open(path))
    lb = sorted(
        [{"name": d["name"], "time": d["data"][-1][1]} for d in history.values() if d["data"]],
        key=lambda x: x["time"]
    )
    return render_template(
        "leaderboard.html",
        track_index=track_index,
        track_names=track_names,
        track_codes=track_codes,
        leaderboard=lb,
        image_file=f"/static/leaderboard_{track_index}.png"
    )

@app.route("/overall")
def overall_page():
    overall = generate_overall()
    return render_template("overall.html", leaderboard=overall)

@app.route("/ping")
def ping():
    update_all_data()
    return redirect(url_for("home"))
    return "OK", 200
    

def schedule_updates():
    while True:
        update_all_data()
        time.sleep(300)

if __name__ == "__main__":
    threading.Thread(target=schedule_updates, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
