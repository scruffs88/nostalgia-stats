from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app import db
from app.settings import settings

from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

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
        <select id="range">
          <option value="last24">Last 24 hours</option>
          <option value="today">Today</option>
          <option value="yesterday">Yesterday</option>
          <option value="last7" selected>Last 7 days</option>
          <option value="thisweek">This week</option>
          <option value="lastweek">Last week</option>
          <option value="thismonth">This month</option>
          <option value="lastmonth">Last month</option>
          <option value="last30">Last 30 days</option>
          <option value="last365">Last 365 days</option>
          <option value="custom">Custom range...</option>
        </select>
        <div id="customRange" style="display:none; gap:4px; align-items:center;">
          <input type="date" id="startDate" />
          <input type="date" id="endDate" />
          <button id="applyRange">Apply</button>
          <span id="rangeError" style="color:#fbbf24;font-size:12px;margin-left:6px;"></span>
        </div>
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

function localNow(){
  return new Date(new Date().toLocaleString('en-US',{timeZone:TZ}));
}

function localDateString(dt){
  return dt.toLocaleDateString('sv-SE',{timeZone:TZ});
}

function computePreset(preset){
  const now = localNow();
  let start, end, days;
  switch(preset){
    case 'last24': days=1; break;
    case 'today':
      start = localDateString(now);
      end = start;
      break;
    case 'yesterday':{
      const d=new Date(now);
      d.setDate(d.getDate()-1);
      start = localDateString(d);
      end = start;
      break;
    }
    case 'last7': days=7; break;
    case 'thisweek':{
      const d=new Date(now);
      const dow=(d.getDay()+6)%7;
      const m=new Date(now);
      m.setDate(d.getDate()-dow);
      start = localDateString(m);
      end = localDateString(now);
      break;
    }
    case 'lastweek':{
      const d=new Date(now);
      const dow=(d.getDay()+6)%7;
      const mon=new Date(now);
      mon.setDate(d.getDate()-dow-7);
      start=localDateString(mon);
      const sun=new Date(mon);
      sun.setDate(mon.getDate()+6);
      end=localDateString(sun);
      break;
    }
    case 'thismonth':{
      const m=new Date(now);
      m.setDate(1);
      start=localDateString(m);
      end=localDateString(now);
      break;
    }
    case 'lastmonth':{
      const m=new Date(now);
      m.setDate(1);
      m.setMonth(m.getMonth()-1);
      start=localDateString(m);
      const m2=new Date(m);
      m2.setMonth(m.getMonth()+1);
      m2.setDate(0);
      end=localDateString(m2);
      break;
    }
    case 'last30': days=30; break;
    case 'last365': days=365; break;
  }
  return {start,end,days};
}

function saveSelection(sel){
  localStorage.setItem('rangeSelection', JSON.stringify(sel));
}

function loadSelection(){
  const r=localStorage.getItem('rangeSelection');
  return r? JSON.parse(r): null;
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
        backgroundColor: "rgba(56,189,248,0.55)",
        borderColor: "rgba(56,189,248,0.95)",
        borderWidth: 1,
        borderRadius: 8,
        hoverBackgroundColor: "rgba(56,189,248,0.85)",
        hoverBorderColor: "rgba(56,189,248,1)",
        barPercentage: 0.9,
        categoryPercentage: 0.8
      }]
    },
    options: {
      responsive: true,
      animation: false,
      plugins: {
        legend: { display: true, labels: { boxWidth: 18 } },
        tooltip: {
          intersect: false,
          mode: "index",
          backgroundColor: "rgba(10,16,28,0.95)",
          titleColor: "#e6edf6",
          bodyColor: "#e6edf6",
          callbacks: {
            label: ctx => {
              const v = ctx.parsed.y;
              return `Avg: ${Number(v).toFixed(0)}`;
            }
          }
        },
        annotation: {
          annotations: annotations || {}
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#9fb0c3", maxRotation: 0 } },
        y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.08)" }, ticks: { color: "#9fb0c3" } }
      }
    }
  });
}

async function load(){
  document.getElementById("tzPill").textContent = "TZ: " + TZ;
  // determine selection
  let sel = loadSelection();
  if(!sel){
    sel = {type:'preset', value:'last7'};
  }
  // apply to UI
  document.getElementById('range').value = sel.value;
  if(sel.type==='custom' && sel.start && sel.end){
    document.getElementById('customRange').style.display='flex';
    document.getElementById('startDate').value=sel.start;
    document.getElementById('endDate').value=sel.end;
  }

  // compute query params
  let params = new URLSearchParams({tz:TZ});
  if(sel.type==='preset'){
    const {start,end,days} = computePreset(sel.value);
    if(days){ params.set('days', days); }
    if(start && end){ params.set('start', start); params.set('end', end); }
  } else if(sel.type==='custom'){
    params.set('start', sel.start);
    params.set('end', sel.end);
  }
  const q = params.toString();

  // now/kpis
  const now = await (await fetch("/api/now")).json();
  document.getElementById("nowListeners").textContent = now.listeners ?? "—";
  document.getElementById("nowTitle").textContent = now.title ?? "—";
  document.getElementById("nowUpdated").textContent = "Updated: " + fmtLocal(now.ts_utc || now.timestamp || now.ts);
  document.getElementById("nowMeta").textContent = now.listenurl ? now.listenurl : "—";

  try {
    const peaks = await (await fetch(`/api/stats/peaks?${q}`)).json();
    document.getElementById("peakToday").textContent = peaks.peak_today ?? "—";
    document.getElementById("peakWeek").textContent = peaks.peak_window ? `Peak: ${peaks.peak_window}` : "";
  } catch(e){ }

  const hourly = await (await fetch(`/api/stats/hourly?${q}`)).json();
  const labels = hourly.map(d => String(d.hour).padStart(2,"0"));
  const values = hourly.map(d => d.avg_listeners);

  // annotations
  let ann = {};
  try{
    const events = await (await fetch(`/api/events?${q}`)).json();
    const last = events.slice(-15);
    last.forEach((ev, i) => {
      ann["e"+i] = {
        type: "line",
        xMin: String(ev.hour).padStart(2,"0"),
        xMax: String(ev.hour).padStart(2,"0"),
        borderColor: "rgba(255,255,255,0.10)",
        borderWidth: 1,
        label: { display: false }
      };
    });
  } catch(e){}

  chartDefaults();
  makeHourlyChart(labels, values, ann);

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

const rangeSelect = document.getElementById("range");
const customDiv = document.getElementById("customRange");
const startInput = document.getElementById("startDate");
const endInput = document.getElementById("endDate");
const applyBtn = document.getElementById("applyRange");
const errspan = document.getElementById("rangeError");

rangeSelect.addEventListener("change", () => {
  const val = rangeSelect.value;
  errspan.textContent = "";
  if(val === "custom"){
    customDiv.style.display = "flex";
  } else {
    customDiv.style.display = "none";
    saveSelection({type:'preset', value: val});
    load();
  }
});

applyBtn.addEventListener("click", () => {
  const s = startInput.value;
  const e = endInput.value;
  if(!s || !e){ errspan.textContent = "start/end required"; return; }
  if(e < s){ errspan.textContent = "end must be after start"; return; }
  const diff = (new Date(e) - new Date(s))/(1000*60*60*24);
  if(diff > 730){ errspan.textContent = "range > 2 years"; return; }
  errspan.textContent = "";
  saveSelection({type:'custom', start: s, end: e});
  load();
});

load();
setInterval(load, 60_000);
</script>
</body>
</html>"""
    return HTMLResponse(html)



# helpers

def _parse_range(start: Optional[str], end: Optional[str], tz: str):
    if start or end:
        if not start or not end:
            raise HTTPException(status_code=400, detail="both start and end required")
        try:
            sd = date.fromisoformat(start)
            ed = date.fromisoformat(end)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid date format")
        if ed < sd:
            raise HTTPException(status_code=400, detail="end must be >= start")
        if (ed - sd).days > 365 * 2:
            raise HTTPException(status_code=400, detail="range too large")
        z = ZoneInfo(tz)
        start_dt = datetime.combine(sd, time.min).replace(tzinfo=z).astimezone(ZoneInfo("UTC"))
        # end exclusive: next day start
        end_dt = datetime.combine(ed + timedelta(days=1), time.min).replace(tzinfo=z).astimezone(ZoneInfo("UTC"))
        return start_dt, end_dt
    return None, None


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
async def api_hourly(
    days: Optional[int] = Query(None, ge=1, le=3650),
    start: Optional[str] = None,
    end: Optional[str] = None,
    tz: str = "Europe/Bucharest",
):
    start_dt, end_dt = _parse_range(start, end, tz)
    if start_dt and end_dt:
        stats = await db.get_hourly_stats_range(start_dt, end_dt, tz)
    else:
        stats = await db.get_hourly_stats(days or 7, tz)
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
async def api_events(
    days: Optional[int] = Query(None, ge=1, le=3650),
    start: Optional[str] = None,
    end: Optional[str] = None,
    tz: str = "Europe/Bucharest",
):
    start_dt, end_dt = _parse_range(start, end, tz)
    if start_dt and end_dt:
        q = f"""
          WITH x AS (
            SELECT
              ts_utc,
              title,
              LAG(title) OVER (ORDER BY ts_utc) AS prev_title
            FROM snapshots
            WHERE ts_utc >= $1 AND ts_utc < $2
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
            rows = await conn.fetch(q, start_dt, end_dt)
        return [dict(r) for r in rows]
    else:
        d = days or 7
        q = f"""
          WITH x AS (
            SELECT
              ts_utc,
              title,
              LAG(title) OVER (ORDER BY ts_utc) AS prev_title
            FROM snapshots
            WHERE ts_utc >= NOW() - INTERVAL '{d} days'
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
async def api_peaks(
    days: Optional[int] = Query(None, ge=1, le=3650),
    start: Optional[str] = None,
    end: Optional[str] = None,
    tz: str = "Europe/Bucharest",
):
    start_dt, end_dt = _parse_range(start, end, tz)
    async with db.pool.acquire() as conn:  # type: ignore
        if start_dt and end_dt:
            rec = await conn.fetchrow(
                """
                SELECT COALESCE(MAX(listeners),0)::int as peak
                FROM snapshots
                WHERE ts_utc >= $1 AND ts_utc < $2 AND listeners IS NOT NULL
                """,
                start_dt,
                end_dt,
            )
            peak = rec["peak"] if rec else 0
            return {"peak_window": int(peak)}
        else:
            # preserve legacy peak_today/peak_window semantics
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
              WHERE ts_utc >= NOW() - INTERVAL '{days or 7} days'
                AND listeners IS NOT NULL;
            """
            peak_today = await conn.fetchval(q_today)
            peak_window = await conn.fetchval(q_window)
            return {"peak_today": int(peak_today or 0), "peak_window": int(peak_window or 0)}
