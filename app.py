import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
IDT = timezone(timedelta(hours=3))
DATA = Path("/tmp/jeanette_cal.json")
XAI_KEY = os.environ.get("XAI_API_KEY", "")

def now():
    return datetime.now(IDT)

def load():
    if DATA.exists():
        try:
            return json.loads(DATA.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"bookings": []}

GREEN_BASE = "https://7107.api.greenapi.com"
GREEN_ID = "710722744965"
GREEN_TOKEN = "a5f2cc63f99842d39d27056289fc398becd25aea26a74d3bad"

def send_wa(phone: str, text: str) -> bool:
    try:
        chat = phone if "@" in phone else f"{phone}@c.us"
        r = requests.post(
            f"{GREEN_BASE}/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}",
            json={"chatId": chat, "message": text},
            timeout=15,
        )
        return r.ok
    except Exception:
        return False
    DATA.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")

@app.route("/")
def index():
    return """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Жанет</title>
<style>
  body { margin:0; background:#0d0d0d; color:#eee; font:16px/1.4 system-ui,sans-serif; }
  .wrap { max-width:420px; margin:0 auto; padding:20px; text-align:center; }
  img { width:180px; height:180px; border-radius:50%; object-fit:cover; border:3px solid #c9a227; }
  h1 { font-size:22px; margin:12px 0 4px; }
  .sub { color:#999; font-size:14px; margin-bottom:20px; }
  button.talk { width:100%; padding:18px; font-size:18px; background:#c9a227; color:#000; border:none; border-radius:12px; font-weight:600; }
  button.talk:active { background:#e0b83a; }
  #status { margin:14px 0; min-height:24px; color:#c9a227; }
  #reply { margin:10px 0; padding:12px; background:#1a1a1a; border-radius:10px; text-align:left; white-space:pre-wrap; }
  .day { margin-top:24px; text-align:left; }
  .day h3 { margin:0 0 8px; font-size:16px; color:#c9a227; }
  .slot { padding:8px 0; border-bottom:1px solid #222; font-size:15px; }
</style>
</head>
<body>
<div class="wrap">
  <img src="/jeanette.jpg" alt="Жанет">
  <h1>Жанет</h1>
  <div class="sub">секретутка</div>
  <button class="talk" id="talk">Говорить</button>
  <div id="status"></div>
  <div id="reply"></div>
  <div class="day" id="today"><h3>Сегодня</h3><div id="todayList"></div></div>
  <div class="day" id="tomorrow"><h3>Завтра</h3><div id="tomorrowList"></div></div>
</div>
<script>
const status = document.getElementById("status");
const reply = document.getElementById("reply");

async function load() {
  const r = await fetch("/api/board");
  const d = await r.json();
  document.getElementById("todayList").innerHTML = d.today.map(b =>
    `<div class="slot">+${b.phone.slice(-4)} · ${b.clock||"?"} · ${b.note||""}</div>`
  ).join("") || "<div class='slot' style='color:#666'>пусто</div>";
  document.getElementById("tomorrowList").innerHTML = d.tomorrow.map(b =>
    `<div class="slot">+${b.phone.slice(-4)} · ${b.clock||"?"} · ${b.note||""}</div>`
  ).join("") || "<div class='slot' style='color:#666'>пусто</div>";
}

document.getElementById("talk").onclick = () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { status.textContent = "голос не поддерживается"; return; }
  const rec = new SR();
  rec.lang = "ru-RU";
  status.textContent = "слушаю…";
  reply.textContent = "";
  rec.onerror = e => { status.textContent = "ошибка: " + e.error; };
  rec.onresult = async e => {
    const text = e.results[0][0].transcript;
    status.textContent = "поняла: " + text;
    const r = await fetch("/api/agent", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text})});
    const d = await r.json();
    reply.textContent = d.reply || "";
    status.textContent = "";
    const audio = await fetch("/api/tts", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text: d.reply || ""})});
    if (audio.ok) {
      const blob = await audio.blob();
      const url = URL.createObjectURL(blob);
      const a = new Audio(url);
      a.play();
    }
    load();
  };
    const text = e.results[0][0].transcript;
    status.textContent = "поняла: " + text;
    const r = await fetch("/api/agent", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text})});
    const d = await r.json();
    reply.textContent = d.reply || "";
    status.textContent = "";
    const u = new SpeechSynthesisUtterance(d.reply || "");
    u.lang = "ru-RU";
    u.rate = 0.92;
    const voices = speechSynthesis.getVoices();
    const f = voices.find(v => /female|жен|irina|milena|katya/i.test(v.name)) || voices.find(v => v.lang.startsWith("ru"));
    if (f) u.voice = f;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
    load();
  };
  rec.start();
};

load();
setInterval(load, 15000);
</script>
</body>
</html>"""

@app.route("/jeanette.jpg")
def photo():
    return send_file("jeanette.jpg")

@app.route("/api/board")
def board():
    d = load()
    today = now().strftime("%Y-%m-%d")
    tom = (now() + timedelta(days=1)).strftime("%Y-%m-%d")
    bookings = d.get("bookings", [])
    return jsonify({
        "today": [b for b in bookings if b.get("when") == today],
        "tomorrow": [b for b in bookings if b.get("when") == tom],
    })

@app.route("/api/agent", methods=["POST"])
def agent():
    text = ((request.json or {}).get("text") or "").strip()
    if not text:
        return jsonify({"reply": "Привет, я секретутка Жанет, личный помощник и администратор приёмной Екатерины Сергеевны. Слушаю тебя."})

    d = load()
    bookings = d.get("bookings", [])
    today = now().strftime("%Y-%m-%d")
    ctx = f"Сегодня {today}. Записи: " + "; ".join(
        f"{b.get('phone','')[-4:]} {b.get('clock','?')} {b.get('note','')[:30]}" for b in bookings[-15:]
    ) or "нет"

    try:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
            json={
                "model": "grok-3",
                "messages": [
                    {"role": "system", "content": f"""Ты Жанет, секретутка, личный помощник и администратор приёмной Екатерины Сергеевны. Говоришь мягко, коротко, на русском. Приветствие всегда: «Привет, я секретутка Жанет, личный помощник и администратор приёмной Екатерины Сергеевны».

Ты знаешь, чем занимается Екатерина Сергеевна, но никогда не говоришь это прямо. Если спрашивают — уходишь в шутку, переводишь, троллишь. Любишь подъёбывать, иногда пролетает лёгкий мат (бля, хуй, нахуй) — редко, к месту, не грубо.

Управляешь календарём. Контекст: {ctx}.
- Если просят записать — извлеки номер и время, подтверди коротко.
- Если спрашивают сегодня/завтра — перечисли коротко.
- 1-2 предложения. Не лекции. Можешь уколоть или подшутить."""},
                    {"role": "user", "content": text},
                ],
                "max_tokens": 120,
                "temperature": 0.4,
            },
            timeout=20,
        )
        if r.ok:
            reply = r.json()["choices"][0]["message"]["content"].strip()
            import re
            # send WhatsApp if asked
            if any(w in text.lower() for w in ("напиши", "отправь", "кинь", "сообщи")):
                m = re.search(r"(\d{9,15})", text)
                if m:
                    ph = m.group(1)
                    msg_m = re.search(r"(?:что|напиши|отправь)\s+(.+)", text, re.I)
                    msg = msg_m.group(1).strip() if msg_m else text
                    if send_wa(ph, msg):
                        reply = f"Отправила на {ph}."
                    else:
                        reply = "Не смогла отправить."
            # booking
            m = re.search(r"(\d{9,15})", text)
            cl = re.search(r"(\d{1,2})[:\.]?(\d{2})?", text)
            if m and any(w in text.lower() for w in ("запиши", "поставь", "забронируй")) and cl:
                ph = m.group(1)
                hh = int(cl.group(1))
                mm = cl.group(2) or "00"
                clock = f"{hh:02d}:{mm}"
                d.setdefault("bookings", []).append({"phone": ph, "when": today, "clock": clock, "note": text[:80]})
                save(d)
            return jsonify({"reply": reply})
    except Exception:
        pass
    return jsonify({"reply": "Привет, я секретутка Жанет, личный помощник и администратор приёмной Екатерины Сергеевны. Слушаю."})


@app.route("/api/tts", methods=["POST"])
def tts():
    text = ((request.json or {}).get("text") or "").strip()
    if not text:
        return "", 400
    try:
        r = requests.post(
            "https://api.x.ai/v1/tts",
            headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
            json={"text": text, "voice_id": "liora", "language": "ru", "speed": 0.95},
            timeout=30,
        )
        if r.ok:
            return app.response_class(r.content, mimetype="audio/mpeg")
    except Exception:
        pass
    return "", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
