from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from datetime import date

app = FastAPI()

DB = "routine.db"

# =========================
# DB INIT
# =========================
def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT,
            time TEXT,
            seq INTEGER,
            routine TEXT,
            status TEXT,
            note TEXT
        )
    """)
    conn.close()

init_db()

# =========================
# DAILY PLAN / LOG
# =========================
@app.get("/daily", response_class=HTMLResponse)
def daily():
    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Daily Routine</title>
    </head>
    <body style="font-family:Arial;padding:15px">
        <h3>📝 Daily Routine</h3>

        <form method="post" action="/save">
            วันที่:<br>
            <input type="date" name="day" required><br><br>

            เวลา:<br>
            <input type="time" name="time"><br><br>

            ลำดับ:<br>
            <input type="number" name="seq" value="1"><br><br>

            กิจวัตร:<br>
            <input type="text" name="routine" required><br><br>

            สถานะ:<br>
            <select name="status">
                <option value="Planned">Planned</option>
                <option value="Done">Done</option>
                <option value="Miss">Miss</option>
            </select><br><br>

            หมายเหตุ:<br>
            <textarea name="note"></textarea><br><br>

            <button type="submit">Save</button>
        </form>

        <br>
        <a href="/dashboard">📊 Dashboard</a>
    </body>
    </html>
    """

@app.post("/save")
def save(
    day: date = Form(...),
    time: str = Form(""),
    seq: int = Form(1),
    routine: str = Form(...),
    status: str = Form(...),
    note: str = Form("")
):
    conn = sqlite3.connect(DB)
    conn.execute("""
        INSERT INTO routines (day, time, seq, routine, status, note)
        VALUES (?,?,?,?,?,?)
    """, (str(day), time, seq, routine, status, note))
    conn.commit()
    conn.close()
    return RedirectResponse("/daily", status_code=303)

# =========================
# DASHBOARD + FILTER
# =========================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    year: str = Query(""),
    month: str = Query("")
):
    conn = sqlite3.connect(DB)

    where = ""
    params = []

    if year and month:
        where = "WHERE strftime('%Y', day)=? AND strftime('%m', day)=?"
        params = [year, month]
    elif year:
        where = "WHERE strftime('%Y', day)=?"
        params = [year]

    total = conn.execute(
        f"SELECT COUNT(*) FROM routines {where}", params
    ).fetchone()[0]

    done = conn.execute(
        f"SELECT COUNT(*) FROM routines {where} {'AND' if where else 'WHERE'} status='Done'",
        params
    ).fetchone()[0]

    percent = int(done / total * 100) if total else 0

    best = conn.execute(
        f"""
        SELECT day FROM routines
        {where} {'AND' if where else 'WHERE'} status='Done'
        GROUP BY day
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """,
        params
    ).fetchone()

    conn.close()
    best_day = best[0] if best else ""

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="theme-color" content="#1f4ed8">
        <title>Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                font-family: Arial;
                background:#f4f6fa;
                padding:12px;
                margin:0;
            }}
            .grid {{
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:8px;
            }}
            .card {{
                background:white;
                padding:10px;
                border-radius:10px;
                box-shadow:0 1px 4px rgba(0,0,0,.1);
            }}
            .kpi {{
                font-size:22px;
                color:#1f4ed8;
                font-weight:bold;
            }}
            .small {{ font-size:12px;color:#555 }}
            a {{ text-decoration:none;color:#1f4ed8;font-weight:bold }}
            #gauge {{ max-width:160px;margin:auto }}
        </style>
    </head>
    <body>

    <h3>📊 Executive Dashboard</h3>

    <div class="card">
        <form method="get">
            <select name="year">
                <option value="">ปีทั้งหมด</option>
                <option value="2025" {"selected" if year=="2025" else ""}>2025</option>
                <option value="2026" {"selected" if year=="2026" else ""}>2026</option>
            </select>
            <select name="month">
                <option value="">เดือนทั้งหมด</option>
                <option value="01" {"selected" if month=="01" else ""}>ม.ค.</option>
                <option value="02" {"selected" if month=="02" else ""}>ก.พ.</option>
                <option value="03" {"selected" if month=="03" else ""}>มี.ค.</option>
                <option value="04" {"selected" if month=="04" else ""}>เม.ย.</option>
                <option value="05" {"selected" if month=="05" else ""}>พ.ค.</option>
                <option value="06" {"selected" if month=="06" else ""}>มิ.ย.</option>
                <option value="07" {"selected" if month=="07" else ""}>ก.ค.</option>
                <option value="08" {"selected" if month=="08" else ""}>ส.ค.</option>
                <option value="09" {"selected" if month=="09" else ""}>ก.ย.</option>
                <option value="10" {"selected" if month=="10" else ""}>ต.ค.</option>
                <option value="11" {"selected" if month=="11" else ""}>พ.ย.</option>
                <option value="12" {"selected" if month=="12" else ""}>ธ.ค.</option>
            </select>
            <button type="submit">กรอง</button>
        </form>
    </div>

    <div class="grid">
        <div class="card"><div class="small">Overall</div><div class="kpi">{percent}%</div></div>
        <div class="card"><div class="small">Total</div><div class="kpi">{total}</div></div>
        <div class="card"><div class="small">Done</div><div class="kpi">{done}</div></div>
        <div class="card">
            <div class="small">Best Day</div>
            <div class="kpi" style="font-size:14px">{best_day}</div>
            <a href="/detail/{best_day}">Detail</a>
        </div>
    </div>

    <div class="card" style="margin-top:8px">
        <div class="small">KPI Gauge</div>
        <canvas id="gauge" height="120"></canvas>
    </div>

    <div class="card">
        📅 <input type="date" id="pickday">
        <button onclick="go()">Go</button>
    </div>

    <div class="card">
        <a href="/charts">📈 Charts</a> |
        <a href="/daily">➕ Add</a>
    </div>

    <script>
    function go(){{
        const d=document.getElementById("pickday").value;
        if(d) location.href="/detail/"+d;
    }}

    const v={percent};
    let c="#dc2626";
    if(v>=80) c="#16a34a";
    else if(v>=50) c="#facc15";

    new Chart(document.getElementById("gauge"), {{
        type:"doughnut",
        data:{{datasets:[{{data:[v,100-v],backgroundColor:[c,"#e5e7eb"],borderWidth:0}}]}},
        options:{{rotation:-90,circumference:180,cutout:"70%",plugins:{{legend:{{display:false}},tooltip:{{enabled:false}}}}}}
    }});
    </script>

    </body>
    </html>
    """

# =========================
# CHARTS (DRILL-DOWN)
# =========================
@app.get("/charts", response_class=HTMLResponse)
def charts():
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT day, COUNT(*) t, SUM(status='Done') d
        FROM routines
        GROUP BY day
        ORDER BY day DESC
        LIMIT 14
    """).fetchall()
    conn.close()

    days = [d for d,_,_ in reversed(rows)]
    perc = [int(dn/t*100) if t else 0 for d,t,dn in reversed(rows)]

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body style="padding:12px;font-family:Arial">
        <h3>📈 Daily Trend</h3>
        <canvas id="c"></canvas>
        <br><a href="/dashboard">⬅ Back</a>

        <script>
        const labels={days};
        new Chart(document.getElementById("c"), {{
            type:"line",
            data:{{labels:labels,datasets:[{{data:{perc},borderColor:"#1f4ed8",pointRadius:6}}]}},
            options:{{scales:{{y:{{beginAtZero:true,max:100}}}},
                onClick:(e,el)=>{{if(el.length)location.href="/detail/"+labels[el[0].index];}}
            }}
        }});
        </script>
    </body>
    </html>
    """

# =========================
# DETAIL
# =========================
@app.get("/detail/{day}", response_class=HTMLResponse)
def detail(day: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT seq,time,routine,status,note
        FROM routines
        WHERE DATE(day)=DATE(?)
        ORDER BY seq,time
    """,(day,)).fetchall()
    conn.close()

    html=f"<h3>📅 {day}</h3><table border=1 cellpadding=6>"
    html+="<tr><th>ลำดับ</th><th>เวลา</th><th>Routine</th><th>Status</th><th>Note</th></tr>"
    for seq,t,r,s,n in rows:
        col="green" if s=="Done" else "red" if s=="Miss" else "gray"
        html+=f"<tr><td>{seq}</td><td>{t}</td><td>{r}</td><td style='color:{col}'>{s}</td><td>{n}</td></tr>"
    html+="</table><br><a href='/dashboard'>⬅ Back</a>"
    return html
