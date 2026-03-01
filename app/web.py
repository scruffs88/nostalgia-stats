from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from app import db
from app.settings import settings

app = FastAPI()


@app.on_event("startup")
async def startup() -> None:
    await db.init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    # simple html page, JS will fetch the api endpoints
    html = """<!DOCTYPE html>
<html>
<head>
<title>Nostalgia Stats</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
<h1>Radio Nostalgia Stats</h1>
<div id="current">
  <p>Loading current data...</p>
</div>
<canvas id="hourlyChart" width="400" height="200"></canvas>
<h2>Top 10 busiest hours</h2>
<table id="busiest">
<thead><tr><th>Hour</th><th>Avg</th><th>Max</th><th>Samples</th></tr></thead>
<tbody></tbody>
</table>
<script>
async function load() {
  const nowResp = await fetch('/api/now');
  const nowData = await nowResp.json();
  document.getElementById('current').innerHTML = `<p>Listeners: ${nowData.listeners} <br>Title: ${nowData.title}<br>Updated: ${nowData.ts_utc}</p>`;

  const statsResp = await fetch('/api/stats/hourly?days=7&tz=Europe/Bucharest');
  const statsData = await statsResp.json();
  const hours = statsData.map(r => r.hour);
  const avgs = statsData.map(r => r.avg_listeners);
  const ctx = document.getElementById('hourlyChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: { labels: hours, datasets: [{ label: 'Avg listeners', data: avgs }] }
  });

  const tbody = document.querySelector('#busiest tbody');
  statsData.sort((a, b) => b.avg_listeners - a.avg_listeners).slice(0, 10).forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${r.hour}</td><td>${r.avg_listeners.toFixed(2)}</td><td>${r.max_listeners}</td><td>${r.samples}</td>`;
    tbody.appendChild(tr);
  });
}
load();
</script>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/api/now")
async def api_now():
    row = await db.get_latest_snapshot()
    if not row:
        raise HTTPException(status_code=404, detail="no data")
    # convert datetime to ISO string for JSON serialization
    if row.get("ts_utc"):
        row["ts_utc"] = row["ts_utc"].isoformat()
    return JSONResponse(row)


@app.get("/api/stats/hourly")
async def api_hourly(days: int = 7, tz: str = "Europe/Bucharest"):
    stats = await db.get_hourly_stats(days, tz)
    # convert Decimal to int/float for JSON serialization
    for row in stats:
        if "avg_listeners" in row and row["avg_listeners"] is not None:
            row["avg_listeners"] = int(row["avg_listeners"])
        if "max_listeners" in row and row["max_listeners"] is not None:
            row["max_listeners"] = int(row["max_listeners"])
        if "samples" in row and row["samples"] is not None:
            row["samples"] = int(row["samples"])
    return JSONResponse(stats)


@app.get("/api/stats/today")
async def api_today(tz: str = "Europe/Bucharest"):
    stats = await db.get_today_stats(tz)
    # convert Decimal to float for JSON serialization
    result = {}
    for key, val in stats.items():
        if val is not None:
            result[key] = float(val)
        else:
            result[key] = None
    return JSONResponse(result)
