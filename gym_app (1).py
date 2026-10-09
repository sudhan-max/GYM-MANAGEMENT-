"""
Gym Management System - single file, zero installs.
Backend : Python standard library (http.server)
Database: SQLite (gym.db, created automatically)
Frontend: HTML/CSS/JS embedded below
Run     : python gym_app.py   ->  open http://localhost:8000
"""
import json, sqlite3, os
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gym.db")
PLANS = {"Monthly": 30, "Quarterly": 90, "Half-Yearly": 180, "Yearly": 365}
FEES = {"Monthly": 1500, "Quarterly": 4000, "Half-Yearly": 7500, "Yearly": 14000}
FIELDS = ["name", "age", "gender", "phone", "email", "plan", "trainer", "fee_paid", "join_date", "expiry_date", "status"]


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS members(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER,
            gender TEXT, phone TEXT NOT NULL, email TEXT, plan TEXT, trainer TEXT,
            fee_paid REAL DEFAULT 0, join_date TEXT, expiry_date TEXT, status TEXT DEFAULT 'Active')""")


def clean(d):
    d = {k: d.get(k, "") for k in FIELDS}
    if not str(d["name"]).strip() or not str(d["phone"]).strip():
        raise ValueError("Name and phone are required")
    d["join_date"] = d["join_date"] or date.today().isoformat()
    if not d["expiry_date"]:
        days = PLANS.get(d["plan"], 30)
        d["expiry_date"] = (date.fromisoformat(d["join_date"]) + timedelta(days=days)).isoformat()
    d["age"] = int(d["age"] or 0)
    d["fee_paid"] = float(d["fee_paid"] or 0)
    d["status"] = d["status"] or "Active"
    return d


def stats():
    t = date.today().isoformat()
    soon = (date.today() + timedelta(days=7)).isoformat()
    with db() as c:
        q = lambda s, *a: c.execute(s, a).fetchone()[0]
        plans = [dict(r) for r in c.execute("SELECT plan, COUNT(*) n FROM members GROUP BY plan")]
        return {
            "total": q("SELECT COUNT(*) FROM members"),
            "active": q("SELECT COUNT(*) FROM members WHERE status='Active' AND expiry_date>=?", t),
            "expired": q("SELECT COUNT(*) FROM members WHERE expiry_date<?", t),
            "expiring": q("SELECT COUNT(*) FROM members WHERE expiry_date BETWEEN ? AND ?", t, soon),
            "revenue": q("SELECT COALESCE(SUM(fee_paid),0) FROM members"),
            "plans": plans,
        }


class H(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def payload(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")

    def mid(self):
        p = self.path.split("?")[0].rstrip("/").split("/")
        return int(p[3]) if len(p) > 3 and p[3].isdigit() else None

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            return self.send(200, PAGE, "text/html; charset=utf-8")
        if p == "/api/stats":
            return self.send(200, stats())
        if p.startswith("/api/members"):
            with db() as c:
                if self.mid():
                    r = c.execute("SELECT * FROM members WHERE id=?", (self.mid(),)).fetchone()
                    return self.send(200 if r else 404, dict(r) if r else {"error": "Not found"})
                return self.send(200, [dict(r) for r in c.execute("SELECT * FROM members ORDER BY id DESC")])
        self.send(404, {"error": "Not found"})

    def do_POST(self):
        try:
            d = clean(self.payload())
            with db() as c:
                cur = c.execute(f"INSERT INTO members({','.join(FIELDS)}) VALUES({','.join('?'*len(FIELDS))})", [d[f] for f in FIELDS])
            self.send(201, {"id": cur.lastrowid})
        except Exception as e:
            self.send(400, {"error": str(e)})

    def do_PUT(self):
        try:
            d = clean(self.payload())
            with db() as c:
                c.execute(f"UPDATE members SET {','.join(f+'=?' for f in FIELDS)} WHERE id=?", [d[f] for f in FIELDS] + [self.mid()])
            self.send(200, {"ok": True})
        except Exception as e:
            self.send(400, {"error": str(e)})

    def do_DELETE(self):
        with db() as c:
            c.execute("DELETE FROM members WHERE id=?", (self.mid(),))
        self.send(200, {"ok": True})

    def log_message(self, *a):
        pass


PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IronPulse Gym Manager</title>
<style>
:root{--bg:#eef1f4;--ink:#16202b;--mut:#5d6b7a;--card:#fff;--line:#d9dee4;--navy:#14213d;--lime:#b6e03a;--red:#d64045;--amb:#e8a317;--grn:#2e9e5b}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 "Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{background:var(--navy);color:#fff;padding:18px 28px;display:flex;justify-content:space-between;align-items:center;border-bottom:4px solid var(--lime)}
header h1{margin:0;font-size:22px;letter-spacing:.5px}header span{color:#aab6c8;font-size:13px}
main{max-width:1180px;margin:0 auto;padding:22px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:20px}
.stat{background:var(--card);border-left:5px solid var(--navy);padding:14px 16px;border-radius:6px}
.stat b{display:block;font-size:26px}.stat small{color:var(--mut)}
.stat.g{border-color:var(--grn)}.stat.r{border-color:var(--red)}.stat.a{border-color:var(--amb)}.stat.l{border-color:var(--lime)}
.panel{background:var(--card);border-radius:6px;padding:20px;margin-bottom:20px;border:1px solid var(--line)}
.panel h2{margin:0 0 14px;font-size:17px}
form{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
label{font-size:13px;color:var(--mut);display:flex;flex-direction:column;gap:4px}
input,select{padding:9px 10px;border:1px solid var(--line);border-radius:5px;font:inherit;background:#fff}
input:focus,select:focus,button:focus-visible{outline:2px solid var(--navy);outline-offset:1px}
.bar{display:flex;gap:10px;grid-column:1/-1;align-items:center}
button{border:0;border-radius:5px;padding:9px 16px;font:inherit;font-weight:600;cursor:pointer;background:var(--navy);color:#fff}
button.p{background:var(--lime);color:var(--navy)}button.s{background:#e3e7ec;color:var(--ink)}button.d{background:var(--red)}
button.sm{padding:5px 10px;font-size:13px;margin-right:4px}
#msg{color:var(--red);font-size:13px}
.top{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:12px}.top input,.top select{min-width:180px}
.wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:820px}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:#f5f7f9;font-size:13px;color:var(--mut)}
.tag{padding:2px 9px;border-radius:12px;font-size:12px;font-weight:600;color:#fff}
.Active{background:var(--grn)}.Expired{background:var(--red)}.Expiring{background:var(--amb)}.Frozen{background:#6b7b8c}
.empty{text-align:center;color:var(--mut);padding:26px}
.bars div{display:flex;align-items:center;gap:10px;margin:6px 0;font-size:13px}.bars i{display:block;height:14px;background:var(--navy);border-radius:3px}
dialog{border:0;border-radius:8px;padding:22px;max-width:420px;width:92%}dialog::backdrop{background:#0008}
dialog dl{display:grid;grid-template-columns:110px 1fr;gap:6px;margin:12px 0}dt{color:var(--mut)}dd{margin:0}
</style></head><body>
<header><h1>IronPulse Gym Manager</h1><span id="today"></span></header>
<main>
<section class="stats" id="stats"></section>

<section class="panel"><h2 id="ftitle">Add a new member</h2>
<form id="f">
<label>Full name *<input name="name" required></label>
<label>Age<input name="age" type="number" min="10" max="99"></label>
<label>Gender<select name="gender"><option>Male</option><option>Female</option><option>Other</option></select></label>
<label>Phone *<input name="phone" required pattern="[0-9+ \-]{7,15}" title="7 to 15 digits"></label>
<label>Email<input name="email" type="email"></label>
<label>Plan<select name="plan"><option>Monthly</option><option>Quarterly</option><option>Half-Yearly</option><option>Yearly</option></select></label>
<label>Trainer<select name="trainer"><option>None</option><option>Arjun</option><option>Priya</option><option>Karthik</option><option>Meena</option></select></label>
<label>Fee paid (₹)<input name="fee_paid" type="number" min="0"></label>
<label>Join date<input name="join_date" type="date"></label>
<label>Expiry date<input name="expiry_date" type="date"></label>
<label>Status<select name="status"><option>Active</option><option>Frozen</option></select></label>
<div class="bar"><button class="p" id="save">Save member</button><button type="button" class="s" id="cancel" hidden>Cancel edit</button><span id="msg"></span></div>
</form></section>

<section class="panel"><h2>Members by plan</h2><div class="bars" id="plans"></div></section>

<section class="panel"><h2>Members</h2>
<div class="top"><input id="q" placeholder="Search name, phone or trainer"><select id="flt"><option value="">All statuses</option><option>Active</option><option>Expiring</option><option>Expired</option><option>Frozen</option></select></div>
<div class="wrap"><table><thead><tr><th>ID</th><th>Name</th><th>Phone</th><th>Plan</th><th>Trainer</th><th>Paid</th><th>Expires</th><th>Status</th><th>Actions</th></tr></thead><tbody id="rows"></tbody></table></div>
</section></main>

<dialog id="dlg"><h2 style="margin:0" id="dn"></h2><dl id="dd"></dl><button class="s" onclick="dlg.close()">Close</button></dialog>

<script>
const $=s=>document.querySelector(s), f=$('#f'); let members=[], editId=null;
const inr=n=>'₹'+Number(n).toLocaleString('en-IN');
$('#today').textContent=new Date().toDateString();
f.join_date.value=new Date().toISOString().slice(0,10);

function state(m){ if(m.status==='Frozen')return 'Frozen';
  const t=new Date().toISOString().slice(0,10), s=new Date(Date.now()+7*864e5).toISOString().slice(0,10);
  return m.expiry_date<t?'Expired':m.expiry_date<=s?'Expiring':'Active'; }

async function api(url,method='GET',body){
  const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
  const j=await r.json(); if(!r.ok)throw new Error(j.error||'Request failed'); return j; }

async function load(){
  members=await api('/api/members'); const s=await api('/api/stats');
  $('#stats').innerHTML=[['Total members',s.total,''],['Active',s.active,'g'],['Expiring in 7 days',s.expiring,'a'],['Expired',s.expired,'r'],['Revenue collected',inr(s.revenue),'l']]
    .map(x=>`<div class="stat ${x[2]}"><small>${x[0]}</small><b>${x[1]}</b></div>`).join('');
  const mx=Math.max(1,...s.plans.map(p=>p.n));
  $('#plans').innerHTML=s.plans.length?s.plans.map(p=>`<div><span style="width:100px">${p.plan}</span><i style="width:${p.n/mx*60}%"></i>${p.n}</div>`).join(''):'<span class="empty">No members yet.</span>';
  render(); }

function render(){
  const q=$('#q').value.toLowerCase(), fl=$('#flt').value;
  const list=members.filter(m=>(m.name+m.phone+m.trainer).toLowerCase().includes(q)&&(!fl||state(m)===fl));
  $('#rows').innerHTML=list.length?list.map(m=>{const st=state(m);return `<tr><td>${m.id}</td><td>${esc(m.name)}</td><td>${esc(m.phone)}</td><td>${m.plan}</td><td>${m.trainer}</td><td>${inr(m.fee_paid)}</td><td>${m.expiry_date}</td><td><span class="tag ${st}">${st}</span></td>
  <td><button class="sm" onclick="view(${m.id})">View</button><button class="sm s" onclick="edit(${m.id})">Edit</button><button class="sm d" onclick="del(${m.id})">Delete</button></td></tr>`}).join('')
  :'<tr><td colspan="9" class="empty">No members found. Add one using the form above.</td></tr>'; }
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

f.onsubmit=async e=>{e.preventDefault();$('#msg').textContent='';
  const d=Object.fromEntries(new FormData(f));
  try{ editId?await api('/api/members/'+editId,'PUT',d):await api('/api/members','POST',d); reset(); await load(); }
  catch(err){$('#msg').textContent=err.message}};
function reset(){editId=null;f.reset();f.join_date.value=new Date().toISOString().slice(0,10);$('#ftitle').textContent='Add a new member';$('#save').textContent='Save member';$('#cancel').hidden=true}
$('#cancel').onclick=reset;
function edit(id){const m=members.find(x=>x.id===id);editId=id;
  FIELDSET.forEach(k=>f[k].value=m[k]);$('#ftitle').textContent='Update member #'+id;$('#save').textContent='Update member';$('#cancel').hidden=false;scrollTo({top:0,behavior:'smooth'})}
const FIELDSET=['name','age','gender','phone','email','plan','trainer','fee_paid','join_date','expiry_date','status'];
function view(id){const m=members.find(x=>x.id===id);$('#dn').textContent=m.name;
  $('#dd').innerHTML=[['Member ID',m.id],['Age / Gender',m.age+' / '+m.gender],['Phone',m.phone],['Email',m.email||'-'],['Plan',m.plan],['Trainer',m.trainer],['Fee paid',inr(m.fee_paid)],['Joined',m.join_date],['Expires',m.expiry_date],['Status',state(m)]].map(r=>`<dt>${r[0]}</dt><dd>${esc(r[1])}</dd>`).join('');
  $('#dlg').showModal()}
async function del(id){if(!confirm('Delete this member permanently?'))return;await api('/api/members/'+id,'DELETE');if(editId===id)reset();await load()}
$('#q').oninput=render;$('#flt').onchange=render;
f.plan.onchange=()=>{const fee={Monthly:1500,Quarterly:4000,'Half-Yearly':7500,Yearly:14000}[f.plan.value];if(!editId)f.fee_paid.value=fee};
f.plan.onchange();load();
</script></body></html>"""

if __name__ == "__main__":
    init()
    print("Gym Management running at http://localhost:8000  (Ctrl+C to stop)")
    ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
