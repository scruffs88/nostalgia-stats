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
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Radio Nostalgia Stats</title>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3"></script>

  <style>
    :root{
      --bg: #0b1220;
      --panel: #0f1b2d;
      --panel2: #0c1728;
      --text: #e6edf6;
      --muted: #9fb0c3;
      --border: rgba(255,255,255,.08);
      --shadow: 0 10px 25px rgba(0,0,0,.35);
      --radius: 14px;
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
      background: radial-gradient(1200px 600px at 20% -10%, rgba(99,102,241,.25), transparent 60%),
                  radial-gradient(900px 500px at 80% 0%, rgba(16,185,129,.18), transparent 55%),
                  var(--bg);
      color: var(--text);
    }
    .wrap{max-width:1200px;margin:28px auto;padding:0 16px}
    header{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:18px}
    h1{margin:0;font-size:28px;letter-spacing:.2px}
    .subtitle{color:var(--muted);font-size:13px;margin-top:6px}
    .grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}
    .card{
      background: linear-gradient(180deg, rgba(255,255,255,.03), transparent 30%), var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 14px 14px;
      overflow:hidden;
    }
    .card h2{margin:0 0 10px;font-size:14px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.08em}
    .statRow{display:flex;gap:12px;flex-wrap:wrap}
    .stat{
      background: var(--panel2);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 12px;
      min-width: 220px;
      flex: 1;
    }
    .stat .k{color:var(--muted);font-size:12px;margin-bottom:6px}
    .stat .v{font-size:22px;font-weight:700}
    .stat .s{color:var(--muted);font-size:12px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    canvas{width:100%;height:320px}
    .col-12{grid-column:span 12}
    .col-8{grid-column:span 8}
    .col-4{grid-column:span 4}
    @media (max-width: 900px){
      .col-8,.col-4{grid-column:span 12}
      .stat{min-width:unset}
    }
    table{width:100%;border-collapse:collapse}
    th,td{padding:10px 8px;border-bottom:1px solid var(--border);text-align:left;font-size:13px}
    th{color:var(--muted);font-weight:600}
    .pill{
      display:inline-block;padding:4px 10px;border:1px solid var(--border);
      border-radius:999px;color:var(--muted);font-size:12px
    }
    .toolbar{display:flex;gap:8px;align-items:center;justify-content:flex-end}
    select{
      background:var(--panel2);color:var(--text);border:1px solid var(--border);
      border-radius:10px;padding:8px 10px;font-size:13px;
    }
    a{color:#8ab4ff}

    /* KPI colours */
    .kpi-listeners { color: #4ade80; }   /* green */
    .kpi-peaks     { color: #fbbf24; }   /* amber */
    .kpi-now       { color: #38bdf8; }   /* cyan */

    /* subtle glow for active KPIs (now section) */
    .kpi-card {
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.04),
        0 0 24px rgba(56,189,248,0.08);
    }
  </style>
</head>

<body>
  <div class="wrap">
    <header>
      <div>
        <h1>Radio Nostalgia Stats</h1>
        <div class="subtitle">Live + historical listener tracking</div>
      </div>
      <div class="toolbar">
        <span class="pill" id="tzPill">TZ: Europe/Bucharest</span>
        <select id="days">
          <option value="1">Last 1 day</option>
          <option value="7" selected>Last 7 days</option>
          <option value="30">Last 30 days</option>
        </select>
      </div>
    </header>

    <div class="grid">
      <div class="card col-12 kpi-card">
        <h2>Now</h2>
        <div class="statRow">
          <div class="stat">
            <div class="k">Listeners</div>
            <div class="v kpi-listeners" id="nowListeners">—</div>
            <div class="s" id="nowUpdated">Updated: —</div>
          </div>
          <div class="stat">
            <div class="k">Now playing</div>
            <div class="v kpi-now" id="nowTitle" style="font-size:16px;font-weight:700">—</div>
            <div class="s" id="nowMeta">—</div>
          </div>
          <div class="stat">
            <div class="k">Peaks</div>
            <div class="v kpi-peaks" id="peakToday">—</div>
            <div class="s" id="peakWeek">—</div>
          </div>
        </div>
      </div>

      <div class="card col-8">
        <h2>Average listeners by hour</h2>
        <canvas id="hourlyChart"></canvas>
      </div>

      <div class="card col-4">
        <h2>Top busiest hours</h2>
        <table>
          <thead><tr><th>Hour</th><th>Avg</th><th>Max</th><th>Samples</th></tr></thead>
          <tbody id="topHours"></tbody>
        </table>
      </div>
    </div>
  </div>

<script>
const TZ = "Europe/Bucharest";

function fmtLocal(iso){
  if(!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("ro-RO", { timeZone: TZ });
}

function chartDefaults(){
  Chart.defaults.color = "#9fb0c3";
  Chart.defaults.borderColor = "rgba(255,255,255,.08)";
  Chart.defaults.font.family = "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
}

let hourlyChart;

function makeHourlyChart(labels, values, annotations){
  const ctx = document.getElementById("hourlyChart").getContext("2d");
  if(hourlyChart) hourlyChart.destroy();

  hourlyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Avg listeners",
        data: values,
        borderWidth: 0,
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      animation: false,
      plugins: {
        legend: { display: true, labels: { boxWidth: 18 } },
        tooltip: { intersect: false, mode: "index" },
        annotation: {
          annotations: annotations || {}
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0 } },
        y: { beginAtZero: true, grid: { color: "rgba(255,255,255,.08)" } }
      }
    }
  });
}

async function load(){
  document.getElementById("tzPill").textContent = "TZ: " + TZ;
  const days = document.getElementById("days").value;

  const now = await (await fetch("/api/now")).json();
  document.getElementById("nowListeners").textContent = now.listeners ?? "—";
  document.getElementById("nowTitle").textContent = now.title ?? "—";
  document.getElementById("nowUpdated").textContent = "Updated: " + fmtLocal(now.ts_utc || now.timestamp || now.ts);
  document.getElementById("nowMeta").textContent = now.listenurl ? now.listenurl : "—";

  // peaks (you’ll add endpoint below; if not present, keep placeholder)
  try {
    const peaks = await (await fetch(`/api/stats/peaks?days=${days}&tz=${TZ}`)).json();
    document.getElementById("peakToday").textContent = peaks.peak_today ?? "—";
    document.getElementById("peakWeek").textContent = `Peak ${days}d: ${peaks.peak_window ?? "—"}`;
  } catch(e){}

  const hourly = await (await fetch(`/api/stats/hourly?days=${days}&tz=${TZ}`)).json();
  const labels = hourly.map(d => String(d.hour).padStart(2,"0"));
  const values = hourly.map(d => d.avg_listeners);

  // annotations (optional endpoint; safe if missing)
  let ann = {};
  try{
    const events = await (await fetch(`/api/events?days=${days}&tz=${TZ}`)).json();
    // mark "title change" events as vertical lines (only last ~15 to avoid clutter)
    const last = events.slice(-15);
    last.forEach((ev, i) => {
      // ev.hour is local hour bucket of event
      ann["e"+i] = {
        type: "line",
        xMin: String(ev.hour).padStart(2,"0"),
        xMax: String(ev.hour).padStart(2,"0"),
        borderColor: "rgba(255,255,255,.18)",
        borderWidth: 1,
        label: { display: false }
      };
    });
  } catch(e){}

  chartDefaults();
  makeHourlyChart(labels, values, ann);

  // top hours table
  const top = [...hourly]
    .filter(r => r.samples > 0)
    .sort((a,b) => b.avg_listeners - a.avg_listeners)
    .slice(0,10);

  const tbody = document.getElementById("topHours");
  tbody.innerHTML = top.map(r => `
    <tr>
      <td>${String(r.hour).padStart(2,"0")}</td>
      <td>${Number(r.avg_listeners).toFixed(1)}</td>
      <td>${r.max_listeners ?? 0}</td>
      <td>${r.samples ?? 0}</td>
    </tr>
  `).join("");
}

document.getElementById("days").addEventListener("change", load);
load();
setInterval(load, 60_000);
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

from fastapi import Query

@app.get("/api/events")
async def api_events(days: int = Query(7, ge=1, le=365), tz: str = "Europe/Bucharest"):
    # Title-change events (last N days)
    q = f"""
      WITH x AS (
        SELECT
          ts_utc,
          title,
          LAG(title) OVER (ORDER BY ts_utc) AS prev_title
        FROM snapshots
        WHERE ts_utc >= NOW() - INTERVAL '{days} days'
      )
      SELECT
        ts_utc,
        title,
        EXTRACT(HOUR FROM (ts_utc AT TIME ZONE 'UTC' AT TIME ZONE '{tz}'))::int AS hour
      FROM x
      WHERE title IS NOT NULL AND prev_title IS NOT NULL AND title <> prev_title
      ORDER BY ts_utc;
    """
    async with db.pool.acquire() as conn:  # type: ignore
        rows = await conn.fetch(q)
    return [dict(r) for r in rows]

@app.get("/api/stats/peaks")
async def api_peaks(days: int = Query(7, ge=1, le=365), tz: str = "Europe/Bucharest"):
    q_today = f"""
      SELECT COALESCE(MAX(listeners), 0)::int AS peak_today
      FROM snapshots
      WHERE (ts_utc AT TIME ZONE 'UTC' AT TIME ZONE '{tz}')::date
            = (NOW() AT TIME ZONE '{tz}')::date
        AND listeners IS NOT NULL;
    """
    q_window = f"""
      SELECT COALESCE(MAX(listeners), 0)::int AS peak_window
      FROM snapshots
      WHERE ts_utc >= NOW() - INTERVAL '{days} days'
        AND listeners IS NOT NULL;
    """
    async with db.pool.acquire() as conn:  # type: ignore
        peak_today = await conn.fetchval(q_today)
        peak_window = await conn.fetchval(q_window)
    return {"peak_today": int(peak_today or 0), "peak_window": int(peak_window or 0)}
