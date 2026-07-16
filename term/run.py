#!/usr/bin/env python3
"""
Engine behind the profile terminal.

NOT a shell — a fixed dispatch table. Nothing a visitor types is executed;
output is sanitized so it can't escape the README code fence or inject HTML.

Modes (env):
  CMD set   -> run one command, append to transcript, re-render README
  CMD empty -> just re-render README from current session (used to reskin/seed)
"""
import base64, datetime, json, os, pathlib, random, re, urllib.parse

def now_utc(fmt="%Y-%m-%d %H:%M UTC"):
    return datetime.datetime.now(datetime.timezone.utc).strftime(fmt)

ROOT   = pathlib.Path(__file__).resolve().parent.parent
STATE  = ROOT / "term" / "session.json"
OUTF   = ROOT / "term" / "last_output.txt"
README = ROOT / "README.md"

USER      = "harryngai"      # repo = USER/USER
CW        = 60               # terminal window inner content width
SHOWLINES = 20               # transcript rows shown
KEEPLOG   = 250
CREATED   = "2024-02-23"

GAME_RND = random.Random()
if os.environ.get("SEED"):
    GAME_RND.seed(int(os.environ["SEED"]))

# ── session ────────────────────────────────────────────────────────────────
def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"count": 0, "log": [], "last_actor": None, "last_time": None, "game": None}

def save(s):
    s["log"] = s["log"][-KEEPLOG:]
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n")

def clean(s, n=600):
    return re.sub(r"[<>]", "", s.replace("`", "'").replace("\r", ""))[:n]

# ── "filesystem" ───────────────────────────────────────────────────────────
KEY_PLAIN = "open-sesame"
KEY_B64   = base64.b64encode(KEY_PLAIN.encode()).decode()
FILES = {
    "motd": ("welcome, stranger.\n"
             "  a real terminal wearing a github profile. every command you\n"
             "  run is executed by a robot and written back here.\n"
             "  the box says nothing about its owner. try  help  or  games"),
    ".hint": ("vault.enc is sealed. the key is in plain sight, base64'd:\n"
              "  " + KEY_B64 + "\n  decode it, then:  unlock <key>"),
    "vault.enc": "sealed. run:  unlock <key>   (hint: cat .hint)",
    "readme.md": "you're soaking in it.",
}
LS = [".", "..", "motd", ".hint", "vault.enc", "games/", "readme.md"]
FORTUNES = [
    "the best code is no code.",
    "two hard things in CS: cache invalidation, naming, and off-by-one.",
    "a VPN is just someone else's computer you trust more.",
    "prod is the only real test environment.",
    "the network is reliable. — a liar",
    "you are not stuck in traffic. you are traffic.",
    "weeks of coding can save you hours of planning.",
    "ship it. we'll fix it in post.",
]

def neofetch(s):
    return "\n".join([
        "     _____        " + USER + "@github",
        "    /     \\       " + "-" * (len(USER) + 7),
        "   | () () |      os     github-actions / ubuntu",
        "    \\  ^  /       shell  interp.py (sandboxed)",
        "     |||||        cmds   %d run" % s["count"],
        "     |||||        last   @%s" % (s["last_actor"] or "nobody"),
        "                  up     since " + CREATED,
    ])

FLAG = ("[+] key accepted\n[+] decrypting .......... ok\n\n"
        "    V A U L T   U N L O C K E D\n    flag{ y0u_r4n_the_term1nal }")

# ── game: 2048 ─────────────────────────────────────────────────────────────
def _slide(row):
    t = [x for x in row if x]; out = []; gain = 0; i = 0
    while i < len(t):
        if i + 1 < len(t) and t[i] == t[i+1]:
            out.append(t[i]*2); gain += t[i]*2; i += 2
        else:
            out.append(t[i]); i += 1
    return out + [0]*(4-len(out)), gain

def _T(b):            return [list(r) for r in zip(*b)]
def _spawn(b):
    empty = [(r, c) for r in range(4) for c in range(4) if b[r][c] == 0]
    if empty:
        r, c = GAME_RND.choice(empty)
        b[r][c] = 4 if GAME_RND.random() < 0.1 else 2

def _move(b, d):
    orig = [r[:] for r in b]; gain = 0
    if d in ("left", "right"):
        for r in range(4):
            row = b[r][::-1] if d == "right" else b[r]
            row, g = _slide(row); gain += g
            b[r] = row[::-1] if d == "right" else row
    else:
        b[:] = _T(b)
        for r in range(4):
            row = b[r][::-1] if d == "down" else b[r]
            row, g = _slide(row); gain += g
            b[r] = row[::-1] if d == "down" else row
        b[:] = _T(b)
    return b != orig, gain

def _stuck(b):
    if any(0 in r for r in b): return False
    for r in range(4):
        for c in range(4):
            if c < 3 and b[r][c] == b[r][c+1]: return False
            if r < 3 and b[r][c] == b[r+1][c]: return False
    return True

def _draw2048(g):
    rows = ["   ".join(f"{v if v else '.':>4}" for v in row) for row in g["board"]]
    if g.get("won"):   tail = f"score {g['score']}   2048! you win. `play 2048` again?"
    elif g.get("over"):tail = f"score {g['score']}   game over. `play 2048` to retry."
    else:              tail = f"score {g['score']}   move: up/down/left/right  ·  quit"
    return "2048\n" + "\n".join(rows) + "\n" + tail

def start_2048(s):
    b = [[0]*4 for _ in range(4)]; _spawn(b); _spawn(b)
    s["game"] = {"name": "2048", "board": b, "score": 0, "over": False, "won": False}
    return _draw2048(s["game"])

def play_2048(s, d):
    g = s["game"]
    if g.get("over") or g.get("won"):
        return _draw2048(g)
    changed, gain = _move(g["board"], d)
    g["score"] += gain
    if changed:
        _spawn(g["board"])
        if any(2048 in r for r in g["board"]): g["won"] = True
        elif _stuck(g["board"]): g["over"] = True
    return _draw2048(g)

# ── interpreter ────────────────────────────────────────────────────────────
DIRS = {"up": "up", "down": "down", "left": "left", "right": "right",
        "w": "up", "s": "down", "a": "left", "d": "right"}

def interpret(line, s):
    line = line.strip()
    if not line: return ""
    parts = line.split(); cmd, args = parts[0].lower(), parts[1:]
    rest = " ".join(args)
    rnd = random.Random(f"{s['count']}:{line}")
    game = s.get("game")

    # active-game routing
    if game and game.get("name") == "2048" and cmd in DIRS:
        return play_2048(s, DIRS[cmd])
    if game and game.get("name") == "mines" and cmd in ("reveal","r","dig","open","flag","f"):
        return mines_cmd(s, cmd, args)
    if cmd in ("quit", "q") and game:
        s["game"] = None; return "quit game. back to the shell."
    if cmd in DIRS and not game:
        return "no game running. start one:  play mines   (or:  games)"
    if cmd in ("reveal","dig","open","flag") and not (game and game.get("name") == "mines"):
        return "no minesweeper running. start it:  play mines"

    if cmd == "help":
        return ("commands:  help  ls  cat <f>  whoami  id  date  uptime  echo <t>\n"
                "           neofetch  fortune  cowsay <t>  history  unlock <key>\n"
                "games:     games · play mines · play 2048 · rps <r|p|s> · guess <n>\n"
                "there's a flag{} hidden in the filesystem. poke around.")
    if cmd == "games":
        return ("available games:\n"
                "  play mines  reveal/flag cells, don't hit a mine (9×9, 10 mines)\n"
                "  play 2048   slide tiles, w/a/s/d or up/down/left/right\n"
                "  rps <r|p|s> rock paper scissors\n  guess <n>   1-100, guess my number")
    if cmd == "play":
        g = (args[0].lower() if args else "")
        if g == "mines":
            s["game"] = mines_new()
            return "minesweeper: 9×9, 10 mines. reveal a cell:  reveal e5  (first move is always safe)"
        if g == "2048": return start_2048(s)
        if g == "guess":
            s["game"] = {"name": "guess", "n": GAME_RND.randint(1, 100), "tries": 0}
            return "guessing game: i picked 1-100. type  guess <n>"
        return "usage: play <mines|2048|guess>   (see: games)"
    if cmd == "ls":  return "  ".join(LS)
    if cmd == "cat":
        if not args: return "cat: missing operand"
        return FILES.get(args[0].lower(), f"cat: {args[0]}: No such file or directory")
    if cmd == "whoami": return f"guest — visitor #{s['count']+1}, clearance: curious"
    if cmd == "id":     return "uid=1000(guest) gid=1000(guest) groups=1000(guest),27(curious)"
    if cmd == "date":   return now_utc("%a %d %b %Y %H:%M:%S UTC")
    if cmd == "uptime":
        d = (datetime.date.today() - datetime.date.fromisoformat(CREATED)).days
        return f"up {d} days,  load average: 0.42, 0.17, 0.09,  vibes: immaculate"
    if cmd == "echo":     return clean(rest)
    if cmd == "neofetch": return neofetch(s)
    if cmd == "fortune":  return rnd.choice(FORTUNES)
    if cmd == "cowsay":
        t = clean(rest, 48) or "moo"; bar = "-"*(len(t)+2)
        return (f" {bar}\n< {t} >\n {bar}\n"
                "     \\   ^__^\n      \\  (oo)\\_____\n         (__)\\     )\\/\\\n"
                "             ||--w |\n             ||    ||")
    if cmd == "history":
        return "\n".join(f"  {i+1}  {e['cmd']}" for i, e in enumerate(s["log"][-10:])) or "  (empty)"
    if cmd == "rps":
        me = rnd.choice(["rock", "paper", "scissors"])
        you = {"r":"rock","p":"paper","s":"scissors","rock":"rock","paper":"paper","scissors":"scissors"}.get(args[0].lower() if args else "")
        if not you: return "usage: rps <rock|paper|scissors>"
        res = "draw" if you==me else ("you win" if {"rock":"scissors","paper":"rock","scissors":"paper"}[you]==me else "i win")
        return f"you: {you}  ·  me: {me}  →  {res}"
    if cmd == "guess":
        if not (game and game.get("name") == "guess"): return "no game. start:  play guess"
        try: n = int(args[0])
        except (IndexError, ValueError): return "usage: guess <number 1-100>"
        game["tries"] += 1
        if n == game["n"]:
            t = game["tries"]; s["game"] = None
            return f"correct! {n} in {t} t{'ry' if t==1 else 'ries'}. `play guess` again?"
        return ("too low."  if n < game["n"] else "too high.") + f"  (try {game['tries']})"
    if cmd == "unlock":
        return FLAG if (args and args[0] == KEY_PLAIN) else "access denied. read `.hint`."
    if cmd == "sudo":   return "guest is not in the sudoers file. this incident will be reported. (jk)"
    if cmd in ("rm","rmdir"): return "nice try. this filesystem is load-bearing."
    if cmd in ("curl","wget"):return f"{cmd}: no egress from this box. (it's a security thing.)"
    if cmd == "clear":  s["log"] = []; s["game"] = None; return "__CLEAR__"
    if cmd in ("about","whois"): return "operator: [REDACTED]. the box is more interesting than its owner."
    if cmd == "exit":   return "there is no exit. there is only more terminal."
    if cmd in ("hello","hi"): return "hi. type  help"
    if cmd == "ping":   return "pong"
    return f"{cmd}: command not found. try  help"

# ── window render ──────────────────────────────────────────────────────────
def _transcript(s, n):
    lines = []
    for e in s["log"]:
        lines.append(f"guest@github:~$ {e['cmd']}")
        for ln in e["out"].split("\n"):
            lines.append(("  " + ln) if ln else "")
    lines.append("guest@github:~$ █")
    view = lines[-n:]
    trimmed = False
    while len(view) > 1 and not view[0].startswith("guest@github"):
        view.pop(0); trimmed = True
    if trimmed: view = ["  ⋮"] + view
    return view

# ── SVG rendering (colour, like the stat plugins) ───────────────────────────
SVG = ROOT / "term" / "screen.svg"
W        = 760
BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
GREEN, BLUE, WHITE, GRAY, DIM = "#3fb950", "#58a6ff", "#e6edf3", "#adbac7", "#6e7681"
YELLOW, CYAN, RED = "#e3b341", "#39c5cf", "#f85149"
FONT = ("ui-monospace,'SFMono-Regular',Menlo,Consolas,"
        "'Liberation Mono','DejaVu Sans Mono',monospace")

def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

def _chrome(h, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
        f'viewBox="0 0 {W} {h}" font-family="{FONT}">'
        f'<clipPath id="r"><rect width="{W}" height="{h}" rx="12"/></clipPath>'
        f'<g clip-path="url(#r)">'
        f'<rect width="{W}" height="{h}" fill="{BG}"/>'
        f'<rect width="{W}" height="40" fill="{PANEL}"/>'
        f'<circle cx="24" cy="20" r="6" fill="#ff5f56"/>'
        f'<circle cx="44" cy="20" r="6" fill="#ffbd2e"/>'
        f'<circle cx="64" cy="20" r="6" fill="#27c93f"/>'
        f'<text x="{W/2}" y="25" text-anchor="middle" fill="#8b949e" '
        f'font-size="13">{esc(title)}</text>'
        f'<line x1="0" y1="40" x2="{W}" y2="40" stroke="{BORDER}"/>')

def _end(h, status):
    return (f'<rect x="0" y="{h-28}" width="{W}" height="28" fill="{PANEL}"/>'
            f'<text x="16" y="{h-9}" fill="{DIM}" font-size="12">{esc(status)}</text>'
            f'</g><rect x="0.5" y="0.5" width="{W-1}" height="{h-1}" rx="12" '
            f'fill="none" stroke="{BORDER}"/></svg>')

def _accent(ln):
    low = ln.lower()
    if "flag{" in low or "vault" in low: return YELLOW
    if "you win" in low or "correct" in low or "accepted" in low: return GREEN
    if "denied" in low or "not found" in low or "game over" in low: return RED
    return GRAY

def svg_terminal(s):
    lines = _transcript(s, 15)
    fw, lh, x0, top = 8.6, 21, 22, 66
    h = top + len(lines) * lh + 18 + 28
    body = [_chrome(h, f"{USER}@github — zsh")]
    y = top
    for ln in lines:
        cur = ln.endswith("█"); txt = ln[:-1] if cur else ln
        if txt.startswith("guest@github:~$"):
            rest = esc(txt[len("guest@github:~$"):])
            body.append(
                f'<text x="{x0}" y="{y}" font-size="15" xml:space="preserve">'
                f'<tspan fill="{GREEN}">guest@github</tspan>'
                f'<tspan fill="{BLUE}">:~$</tspan>'
                f'<tspan fill="{WHITE}">{rest}</tspan></text>')
            if cur:
                cx = x0 + len(txt) * fw + 3
                body.append(
                    f'<rect x="{cx:.0f}" y="{y-13}" width="9" height="17" '
                    f'fill="{GREEN}"><animate attributeName="opacity" '
                    f'values="1;1;0;0" dur="1.05s" repeatCount="indefinite"/></rect>')
        elif txt.strip().startswith("⋮"):
            body.append(f'<text x="{x0}" y="{y}" font-size="15" fill="{DIM}" '
                        f'xml:space="preserve">{esc(txt)}</text>')
        else:
            body.append(f'<text x="{x0}" y="{y}" font-size="15" fill="{_accent(txt)}" '
                        f'xml:space="preserve">{esc(txt)}</text>')
        y += lh
    body.append(_end(h, f"cmds {s['count']}  ·  last @{s['last_actor'] or 'nobody'}"
                        f"  ·  {s['last_time'] or now_utc()}"))
    return "".join(body)

TILE = {0:"#21262d",2:"#eee4da",4:"#ede0c8",8:"#f2b179",16:"#f59563",32:"#f67c5f",
        64:"#f65e3b",128:"#edcf72",256:"#edcc61",512:"#edc850",1024:"#edc53f",
        2048:"#edc22e"}
def svg_2048(s, g):
    h = 536
    b = g["board"]; sc = g["score"]
    won, over = g.get("won"), g.get("over")
    title = f"2048 — score {sc}" + ("  · you win!" if won else "  · game over" if over else "")
    body = [_chrome(h, title)]
    tile, gap = 88, 12
    bw = 4*tile + 5*gap
    ox = (W - bw) / 2; oy = 56
    body.append(f'<rect x="{ox}" y="{oy}" width="{bw}" height="{bw}" rx="10" fill="#1c2128"/>')
    for r in range(4):
        for c in range(4):
            v = b[r][c]
            x = ox + gap + c*(tile+gap); y = oy + gap + r*(tile+gap)
            body.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{tile}" height="{tile}" '
                        f'rx="6" fill="{TILE.get(v,"#3c3a32")}"/>')
            if v:
                fs = 40 if v < 100 else 32 if v < 1000 else 24
                col = "#776e65" if v <= 4 else "#f9f6f2"
                body.append(f'<text x="{x+tile/2:.0f}" y="{y+tile/2+fs*0.35:.0f}" '
                            f'text-anchor="middle" font-size="{fs}" font-weight="bold" '
                            f'fill="{col}">{v}</text>')
    cy = oy + bw + 32
    hint = ("`play 2048` to retry" if over else "`play 2048` again" if won
            else "run  up · down · left · right   ·   quit")
    body.append(f'<text x="{W/2}" y="{cy}" text-anchor="middle" font-size="15" '
                f'fill="{GRAY}" xml:space="preserve">{esc(hint)}</text>')
    body.append(_end(h, f"cmds {s['count']}  ·  last @{s['last_actor'] or 'nobody'}"
                        f"  ·  {s['last_time'] or now_utc()}"))
    return "".join(body)

# ── game: minesweeper ───────────────────────────────────────────────────────
MN = 9      # board size
MM = 10     # mine count

def mines_new():
    return {"name": "mines", "n": MN, "m": MM,
            "mine": [[0]*MN for _ in range(MN)], "adj": [[0]*MN for _ in range(MN)],
            "shown": [[0]*MN for _ in range(MN)], "flag": [[0]*MN for _ in range(MN)],
            "placed": False, "over": False, "won": False}

def _mplace(g, sr, sc):
    N = g["n"]; safe = {(sr+dr, sc+dc) for dr in (-1,0,1) for dc in (-1,0,1)}
    cells = [(r, c) for r in range(N) for c in range(N) if (r, c) not in safe]
    for r, c in GAME_RND.sample(cells, min(g["m"], len(cells))):
        g["mine"][r][c] = 1
    for r in range(N):
        for c in range(N):
            g["adj"][r][c] = sum(g["mine"][r+dr][c+dc] for dr in (-1,0,1) for dc in (-1,0,1)
                                 if 0 <= r+dr < N and 0 <= c+dc < N)
    g["placed"] = True

def _mflood(g, r, c):
    N = g["n"]; st = [(r, c)]
    while st:
        r, c = st.pop()
        if g["shown"][r][c] or g["flag"][r][c]: continue
        g["shown"][r][c] = 1
        if g["adj"][r][c] == 0 and not g["mine"][r][c]:
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < N and 0 <= nc < N and not g["shown"][nr][nc]:
                        st.append((nr, nc))

def mines_reveal(g, r, c):
    if not g["placed"]: _mplace(g, r, c)
    if g["flag"][r][c] or g["shown"][r][c]: return
    if g["mine"][r][c]:
        g["over"] = True
        for rr in range(g["n"]):
            for cc in range(g["n"]):
                if g["mine"][rr][cc]: g["shown"][rr][cc] = 1
        return
    _mflood(g, r, c)
    N = g["n"]
    if all(g["shown"][rr][cc] or g["mine"][rr][cc] for rr in range(N) for cc in range(N)):
        g["won"] = True

def _cell(tok):
    m = re.search(r"[a-iA-I]", tok); n = re.search(r"[1-9]", tok)
    if not m or not n: return None
    r = ord(m.group().lower()) - 97; c = int(n.group()) - 1
    return (r, c) if 0 <= r < MN and 0 <= c < MN else None

def mines_cmd(s, cmd, args):
    g = s["game"]
    if g["over"] or g["won"]: return "game finished. `play mines` for a fresh board."
    if not args: return f"usage: {cmd} <cell>   e.g.  {cmd} e5"
    rc = _cell(args[0])
    if not rc: return f"'{args[0]}'? use a cell like  b3  (row a-i, col 1-9)"
    r, c = rc; tok = args[0].lower()
    if cmd in ("flag", "f"):
        if not g["shown"][r][c]: g["flag"][r][c] ^= 1
        F = sum(map(sum, g["flag"]))
        return f"flag {tok} {'planted' if g['flag'][r][c] else 'removed'} · flags {F}/{g['m']}"
    mines_reveal(g, r, c)
    if g["over"]: return f"boom — {tok} was a mine. game over. `play mines`"
    if g["won"]:  return "swept! every safe cell cleared. you win."
    shown = sum(map(sum, g["shown"]))
    return f"revealed {tok}: {g['adj'][r][c]} adjacent mine(s) · cleared {shown}/{MN*MN-MM}"

NUMCOL = {1:"#58a6ff",2:"#3fb950",3:"#f85149",4:"#bc8cff",5:"#f0883e",6:"#39c5cf",7:WHITE,8:"#8b949e"}
def svg_mines(s, g):
    N = g["n"]; cell, gap = 40, 3
    bw = N*cell + (N-1)*gap
    ox = (W - bw) / 2; oy = 92
    h = oy + bw + 58
    F = sum(map(sum, g["flag"])); shown = sum(map(sum, g["shown"]))
    body = [_chrome(h, f"minesweeper — {N}×{N} · {g['m']} mines")]
    for c in range(N):
        body.append(f'<text x="{ox+c*(cell+gap)+cell/2:.0f}" y="{oy-10}" text-anchor="middle" '
                    f'font-size="12" fill="{DIM}">{c+1}</text>')
    for r in range(N):
        body.append(f'<text x="{ox-14:.0f}" y="{oy+r*(cell+gap)+cell/2+4:.0f}" text-anchor="middle" '
                    f'font-size="12" fill="{DIM}">{chr(65+r)}</text>')
    for r in range(N):
        for c in range(N):
            x = ox + c*(cell+gap); y = oy + r*(cell+gap); cx = x+cell/2; cy = y+cell/2
            sh, mn, fl, ad = g["shown"][r][c], g["mine"][r][c], g["flag"][r][c], g["adj"][r][c]
            if sh and mn:
                body.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cell}" height="{cell}" rx="4" fill="#8b1a1a"/>')
                body.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="8" fill="#0d0d0d" stroke="#f0f0f0" stroke-width="1.5"/>')
            elif sh:
                body.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cell}" height="{cell}" rx="4" fill="#161b22" stroke="#21262d"/>')
                if ad > 0:
                    body.append(f'<text x="{cx:.0f}" y="{cy+8:.0f}" text-anchor="middle" font-size="22" '
                                f'font-weight="bold" fill="{NUMCOL.get(ad, WHITE)}">{ad}</text>')
            else:
                body.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cell}" height="{cell}" rx="4" fill="#3b434d"/>')
                body.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cell}" height="3" rx="1.5" fill="#4b555f"/>')
                if fl:
                    body.append(f'<line x1="{cx-5:.0f}" y1="{cy-10:.0f}" x2="{cx-5:.0f}" y2="{cy+11:.0f}" stroke="#c9d1d9" stroke-width="2"/>')
                    body.append(f'<polygon points="{cx-5:.0f},{cy-10:.0f} {cx+8:.0f},{cy-5:.0f} {cx-5:.0f},{cy:.0f}" fill="#f85149"/>')
    hint = ("boom! `play mines` to retry" if g["over"] else
            "swept! `play mines` again" if g["won"] else
            "reveal <cell> · flag <cell>   e.g.  reveal e5")
    body.append(f'<text x="{W/2}" y="{oy+bw+26:.0f}" text-anchor="middle" font-size="15" '
                f'fill="{GRAY}" xml:space="preserve">{esc(hint)}</text>')
    body.append(_end(h, f"mines {g['m']} · flags {F} · cleared {shown}/{N*N-g['m']}"))
    return "".join(body)

def render_svg(s):
    g = s.get("game"); name = g.get("name") if g else None
    if name == "2048":    SVG.write_text(svg_2048(s, g))
    elif name == "mines": SVG.write_text(svg_mines(s, g))
    else:                 SVG.write_text(svg_terminal(s))

# ── README (image is the star) ──────────────────────────────────────────────
def issue_link(cmd):
    q = urllib.parse.urlencode({"title": "$ " + cmd,
        "body": f"Click **Submit new issue** to run `$ {cmd}`.\n\nThe bot runs it, "
                f"updates the profile, replies, and closes this (~30s). "
                f"Then refresh https://github.com/{USER}"})
    return f"https://github.com/{USER}/{USER}/issues/new?{q}"

BAR = ["help", "play mines", "play 2048", "neofetch", "fortune", "rps rock", "cat .hint"]

def render(s):
    img = (f"https://raw.githubusercontent.com/{USER}/{USER}/main/term/screen.svg"
           f"?v={s['count']}")
    links = " · ".join(f"[`{c}`]({issue_link(c)})" for c in BAR)
    parts = [
        f'<a href="{issue_link("help")}">'
        f'<img alt="a live terminal — click a command below to drive it" '
        f'src="{img}" width="760"></a>', "",
        f"**run:**  {links}  ·  [`type your own →`]({issue_link('your command here')})",
        "",
        "<sub>a live, shared terminal, rendered as an image. your command opens an "
        "issue → a GitHub Action runs it (sandboxed, not a real shell) → this picture "
        "updates in ~30s. try `play mines`.</sub>", "",
    ]
    README.write_text("\n".join(parts) + "\n")

# ── main ───────────────────────────────────────────────────────────────────
def main():
    s = load()
    raw = os.environ.get("CMD", "")
    actor = (os.environ.get("ACTOR", "").strip() or None)
    cmd = raw.lstrip()
    if cmd.startswith("$"): cmd = cmd[1:].strip()

    output = ""
    if cmd:
        output = interpret(cmd, s)
        if output == "__CLEAR__": output = "cleared."
        else: s["log"].append({"cmd": clean(cmd, 120), "out": output})
        s["count"] += 1
        s["last_actor"] = actor or s["last_actor"]
        s["last_time"] = now_utc()
        save(s)
    render_svg(s)
    render(s)
    OUTF.write_text((output or "(rendered)") + "\n")

if __name__ == "__main__":
    main()
