from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import AppConfig
from .events import EventStore

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DevLoop Agents</title><style>
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif;background:#071019;color:#e7edf5}*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at 20% 0,#132a3d 0,transparent 35%),#071019;min-height:100vh}.wrap{max-width:1180px;margin:auto;padding:32px 24px}
header{display:flex;justify-content:space-between;align-items:end;margin-bottom:24px}h1{font-size:28px;margin:0}.sub{color:#8fa3b8;margin-top:7px}.live{color:#70e0a5;font-size:13px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#35d07f;box-shadow:0 0 12px #35d07f;margin-right:7px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px}.card,.panel{background:rgba(13,27,40,.88);border:1px solid #20394f;border-radius:14px}.card{padding:18px}.role{font-size:13px;color:#8fa3b8;text-transform:uppercase;letter-spacing:.1em}.metric{font-size:26px;font-weight:700;margin:8px 0 2px}.small{color:#8fa3b8;font-size:13px}.panel{padding:18px}h2{font-size:15px;margin:0 0 14px}.event{display:grid;grid-template-columns:94px 80px 1fr;gap:12px;border-top:1px solid #192f43;padding:11px 0;font-size:13px}.event:first-of-type{border-top:0}.time,.kind{color:#7f96aa}.coder{color:#70a9ff}.qa{color:#d9a5ff}.monitor{color:#70e0a5}.error{color:#ff8b8b}.empty{color:#7f96aa;padding:25px 0}.budget{height:8px;background:#172b3d;border-radius:5px;overflow:hidden;margin-top:10px}.budget i{display:block;height:100%;background:linear-gradient(90deg,#35d07f,#ffc857);width:0}code{color:#a8c7e8}@media(max-width:760px){.grid{grid-template-columns:1fr}.event{grid-template-columns:70px 62px 1fr}.wrap{padding:22px 16px}}
</style></head><body><div class="wrap"><header><div><h1>DevLoop Agents</h1><div class="sub" id="project">Autonomous delivery operations</div></div><div class="live"><span class="dot"></span>local dashboard</div></header>
<section class="grid" id="roles"></section><section class="panel"><h2>Monthly agent budget</h2><div><strong id="cost">$0.00</strong> <span class="small" id="limit"></span></div><div class="budget"><i id="bar"></i></div></section><section class="panel" style="margin-top:18px"><h2>Recent activity</h2><div id="events" class="empty">Waiting for events…</div></section></div>
<script>
const esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
function render(data){document.getElementById('project').textContent=data.project;const roles=['coder','qa','monitor'];document.getElementById('roles').innerHTML=roles.map(r=>{const xs=data.events.filter(e=>e.role===r), last=xs.at(-1);return `<article class="card"><div class="role ${r}">${r}</div><div class="metric">${xs.filter(e=>e.event==='item.finished'||e.event==='probe.healthy').length}</div><div class="small">successful signals</div><div class="small" style="margin-top:10px">${last?esc(last.message):'No activity yet'}</div></article>`}).join('');document.getElementById('cost').textContent=`$${data.month_cost.toFixed(2)}`;document.getElementById('limit').textContent=`of $${data.budget.toFixed(2)}`;document.getElementById('bar').style.width=Math.min(100,data.budget?data.month_cost/data.budget*100:0)+'%';const events=[...data.events].reverse();document.getElementById('events').className=events.length?'':'empty';document.getElementById('events').innerHTML=events.length?events.map(e=>`<div class="event"><span class="time">${esc((e.timestamp||'').slice(11,19))}</span><span class="kind ${esc(e.role)}">${esc(e.role)}</span><span class="${e.level==='error'?'error':''}">${esc(e.message)}</span></div>`).join(''):'Waiting for events…'}
async function tick(){try{render(await(await fetch('/api/status')).json())}catch{}}tick();setInterval(tick,3000);
</script></body></html>"""


def serve_dashboard(config: AppConfig, host: str, port: int) -> None:
    store = EventStore(config.storage.events_path)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if self.path == "/":
                body = PAGE.encode()
                content_type = "text/html; charset=utf-8"
            elif self.path == "/api/status":
                all_events = store.read(limit=10000)
                events = all_events[-250:]
                month = __import__("datetime").datetime.now(__import__("datetime").UTC).strftime("%Y-%m")
                month_cost = sum(
                    float(event.get("data", {}).get("cost_usd") or 0)
                    for event in all_events
                    if str(event.get("timestamp", "")).startswith(month)
                )
                body = json.dumps(
                    {
                        "project": config.project.name,
                        "events": events,
                        "month_cost": month_cost,
                        "budget": config.budget.monthly_usd,
                    }
                ).encode()
                content_type = "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    print(f"DevLoop dashboard: http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
