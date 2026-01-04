from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from datetime import date

app = FastAPI()
DB = "routine.db"

# =====================
# INIT DATABASE
# =====================
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

# =====================
# ROOT
# =====================
@app.get("/")
def root():
    return RedirectResponse("/dashboard")

# =====================
# DAILY (TEMPLATE + MANUAL ADD)
# =====================
@app.get("/daily", response_class=HTMLResponse)
def daily():
    today = date.today()
    template = [
        (1,"Wake up 6:30"),
        (2,"Weight"),
        (3,"Cardio"),
        (4,"calorie deficit"),
        (5,"หาความรู้เพิ่มเติม"),
        (6,"x"),
        (7,"bed time 22:30"),
    ]

    rows = ""
    for s,r in template:
        rows += f"""
        <tr>
          <td><input name="seq" value="{s}" style="width:50px"></td>
          <td><input name="routine" value="{r}" style="width:100%"></td>
          <td>
            <select name="status">
              <option selected>Planned</option>
              <option>Done</option>
              <option>Miss</option>
            </select>
          </td>
        </tr>
        """

    rows += """
    <tr>
      <td><input name="seq" value="8" style="width:50px"></td>
      <td><input name="routine" placeholder="Add your own routine" style="width:100%"></td>
      <td>
        <select name="status">
          <option selected>Planned</option>
          <option>Done</option>
          <option>Miss</option>
        </select>
      </td>
    </tr>
    """

    return f"""
    <html><body style="font-family:Segoe UI,Arial;padding:14px">
    <h3>📝 Daily Routine</h3>

    <form method="post" action="/save-multi">
      Date:<br><input type="date" name="day" value="{today}"><br><br>

      <table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
        <tr><th>Seq</th><th>Routine</th><th>Status</th></tr>
        {rows}
      </table><br>

      <button>Save Daily Routine</button>
    </form>

    <br><a href="/dashboard">⬅ Dashboard</a>
    </body></html>
    """

# =====================
# SAVE MULTI
# =====================
@app.post("/save-multi")
def save_multi(
    day: str = Form(...),
    seq: list[int] = Form(...),
    routine: list[str] = Form(...),
    status: list[str] = Form(...)
):
    conn = sqlite3.connect(DB)
    for i in range(len(seq)):
        if routine[i].strip():
            conn.execute(
                "INSERT INTO routines (day,seq,routine,status) VALUES (?,?,?,?)",
                (day, seq[i], routine[i], status[i])
            )
    conn.commit()
    conn.close()
    return RedirectResponse("/dashboard", status_code=303)

# =====================
# DASHBOARD (YEAR GRAPH + HISTORY)
# =====================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    conn = sqlite3.connect(DB)

    total = conn.execute("SELECT COUNT(*) FROM routines").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Done'").fetchone()[0]
    miss = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Miss'").fetchone()[0]
    percent = int(done/total*100) if total else 0

    year = conn.execute("""
        SELECT strftime('%m', day),
               SUM(status='Done'),
               SUM(status='Miss')
        FROM routines
        GROUP BY strftime('%m', day)
        ORDER BY strftime('%m', day)
    """).fetchall()

    history = conn.execute("""
        SELECT day,
               SUM(status='Done'),
               SUM(status='Miss')
        FROM routines
        GROUP BY day
        ORDER BY day DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    months = [r[0] for r in year]
    done_y = [r[1] for r in year]
    miss_y = [r[2] for r in year]

    return f"""
    <html>
    <head>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family:Segoe UI,Arial;background:#f4f6fb;padding:14px">

    <h2>📊 Dashboard</h2>

    <div style="background:#fff;padding:12px;border-radius:8px">
      <b>Overall (Year)</b><br>
      <span style="font-size:24px;color:#2563eb">{percent}%</span><br>
      Total {total} | Done {done} | Miss {miss}
    </div><br>

    <div style="background:#fff;padding:12px;border-radius:8px">
      <b>📊 Year Overview</b>
      <canvas id="year" style="max-height:260px"></canvas>
    </div><br>

    <div style="background:#fff;padding:12px;border-radius:8px">
      <form method="get" action="/detail-search">
        <input type="date" name="day">
        <button>🔍 Search Daily Routine</button>
      </form>
    </div><br>

    <div style="background:#fff;padding:12px;border-radius:8px">
      <b>📜 Recent History</b>
      <table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
        <tr><th>Date</th><th>Done</th><th>Miss</th><th>Detail</th></tr>
        {''.join(
            f"<tr><td>{d}</td><td>{dn}</td><td>{ms}</td>"
            f"<td><a href='/detail/{d}'>🔍</a></td></tr>"
            for d,dn,ms in history
        )}
      </table>
    </div>

    <br><a href="/daily">➕ Add Daily Routine</a>

    <script>
    new Chart(document.getElementById("year"), {{
      type:"bar",
      data:{{
        labels:{months},
        datasets:[
          {{label:"Done",data:{done_y},backgroundColor:"#16a34a"}},
          {{label:"Miss",data:{miss_y},backgroundColor:"#dc2626"}}
        ]
      }},
      options:{{
        onClick:(e,els)=>{{
          if(els.length>0){{
            let m={months}[els[0].index];
            location="/monthly/"+m;
          }}
        }}
      }}
    }});
    </script>

    </body></html>
    """

# =====================
# MONTHLY GRAPH
# =====================
@app.get("/monthly/{mon}", response_class=HTMLResponse)
def monthly(mon: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT day,
               SUM(status='Done'),
               SUM(status='Miss')
        FROM routines
        WHERE strftime('%m', day)=?
        GROUP BY day
        ORDER BY day
    """,(mon,)).fetchall()
    conn.close()

    days = [r[0] for r in rows]
    done = [r[1] for r in rows]
    miss = [r[2] for r in rows]

    return f"""
    <html><body style="font-family:Segoe UI,Arial;padding:14px">
    <h3>📊 Month {mon}</h3>
    <canvas id="m"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    new Chart(document.getElementById("m"), {{
      type:"bar",
      data:{{
        labels:{days},
        datasets:[
          {{label:"Done",data:{done},backgroundColor:"green"}},
          {{label:"Miss",data:{miss},backgroundColor:"red"}}
        ]
      }},
      options:{{
        onClick:(e,els)=>{{
          if(els.length>0){{
            location="/detail/"+{days}[els[0].index];
          }}
        }}
      }}
    }});
    </script>
    <br><a href="/dashboard">⬅ Dashboard</a>
    </body></html>
    """

# =====================
# SEARCH
# =====================
@app.get("/detail-search")
def detail_search(day: str):
    return RedirectResponse("/detail/"+day)

# =====================
# DETAIL / EDIT / DELETE
# =====================
@app.get("/detail/{day}", response_class=HTMLResponse)
def detail(day: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id,seq,routine,status FROM routines WHERE day=? ORDER BY seq",
        (day,)
    ).fetchall()
    conn.close()

    html = f"<h3>{day}</h3><table border=1 cellpadding=6>"
    html += "<tr><th>Seq</th><th>Routine</th><th>Status</th><th>Action</th></tr>"
    for rid,seq,r,s in rows:
        html += f"""
        <tr>
          <td>{seq}</td><td>{r}</td><td>{s}</td>
          <td>
            <a href="/edit/{rid}">✏️</a>
            <form method="post" action="/delete/{rid}" style="display:inline">
              <button>🗑</button>
            </form>
          </td>
        </tr>
        """
    html += "</table><br><a href='/dashboard'>⬅ Dashboard</a>"
    return html

@app.get("/edit/{rid}", response_class=HTMLResponse)
def edit(rid: int):
    conn = sqlite3.connect(DB)
    d,seq,r,s,n = conn.execute(
        "SELECT day,seq,routine,status,note FROM routines WHERE id=?",
        (rid,)
    ).fetchone()
    conn.close()

    return f"""
    <form method="post">
      <input type="date" name="day" value="{d}"><br>
      <input type="number" name="seq" value="{seq}"><br>
      <input type="text" name="routine" value="{r}"><br>
      <select name="status">
        <option {"selected" if s=="Planned" else ""}>Planned</option>
        <option {"selected" if s=="Done" else ""}>Done</option>
        <option {"selected" if s=="Miss" else ""}>Miss</option>
      </select><br>
      <textarea name="note">{n or ""}</textarea><br>
      <button>Save</button>
    </form>
    """

@app.post("/edit/{rid}")
def edit_save(
    rid:int,
    day:str=Form(...),
    seq:int=Form(...),
    routine:str=Form(...),
    status:str=Form(...),
    note:str=Form("")
):
    conn=sqlite3.connect(DB)
    conn.execute(
        "UPDATE routines SET day=?,seq=?,routine=?,status=?,note=? WHERE id=?",
        (day,seq,routine,status,note,rid)
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/detail/"+day,status_code=303)

@app.post("/delete/{rid}")
def delete(rid:int):
    conn=sqlite3.connect(DB)
    conn.execute("DELETE FROM routines WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return RedirectResponse("/dashboard",status_code=303)
