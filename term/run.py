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
    if cmd in ("quit", "q") and game:
        s["game"] = None; return "quit game. back to the shell."
    if cmd in DIRS and not game:
        return "no game running. start one:  play 2048   (or:  games)"

    if cmd == "help":
        return ("commands:  help  ls  cat <f>  whoami  id  date  uptime  echo <t>\n"
                "           neofetch  fortune  cowsay <t>  history  unlock <key>\n"
                "games:     games  ·  play 2048  ·  rps <r|p|s>  ·  guess <n>\n"
                "there's a flag{} hidden in the filesystem. poke around.")
    if cmd == "games":
        return ("available games:\n  play 2048   slide tiles, w/a/s/d or up/down/left/right\n"
                "  rps <r|p|s> rock paper scissors\n  guess <n>   1-100, i'm thinking of a number")
    if cmd == "play":
        g = (args[0].lower() if args else "")
        if g == "2048": return start_2048(s)
        if g == "guess":
            s["game"] = {"name": "guess", "n": GAME_RND.randint(1, 100), "tries": 0}
            return "guessing game: i picked 1-100. type  guess <n>"
        return "usage: play <2048|guess>   (see: games)"
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
def _topbar(total, left, right):
    dashes = total - 4 - len(left) - len(right)
    return "┌─" + left + "─"*max(1, dashes) + right + "─┐"

def _cl(content):
    if len(content) > CW: content = content[:CW-1] + "…"
    return "│ " + content.ljust(CW) + " │"

def _transcript(s):
    lines = []
    for e in s["log"]:
        lines.append(f"guest@github:~$ {e['cmd']}")
        for ln in e["out"].split("\n"):
            lines.append(("  " + ln) if ln else "")
    lines.append("guest@github:~$ █")
    view = lines[-SHOWLINES:]
    trimmed = False
    while len(view) > 1 and not view[0].startswith("guest@github"):
        view.pop(0); trimmed = True
    if trimmed: view = ["  ⋮"] + view
    return view

def window(s):
    total = CW + 4
    out = [_topbar(total, f" {USER}@github — zsh ", " [_][o][x] ")]
    for ln in _transcript(s):
        out.append(_cl(ln))
    out.append("├" + "─"*(total-2) + "┤")
    out.append(_cl(f"cmds {s['count']}  ·  last @{s['last_actor'] or 'nobody'}  ·  {s['last_time'] or now_utc()}"))
    out.append("└" + "─"*(total-2) + "┘")
    return "\n".join(out)

def issue_link(cmd):
    q = urllib.parse.urlencode({"title": "$ " + cmd,
        "body": f"Click **Submit new issue** to run `$ {cmd}`.\n\nThe bot runs it, "
                f"updates the profile, replies, and closes this (~30s). "
                f"Then refresh https://github.com/{USER}"})
    return f"https://github.com/{USER}/{USER}/issues/new?{q}"

BAR = ["help", "play 2048", "neofetch", "fortune", "ls", "rps rock", "cat .hint"]

def render(s):
    links = "  ·  ".join(f"[`{c}`]({issue_link(c)})" for c in BAR)
    parts = [
        "```", window(s), "```", "",
        f"**run a command** (opens a 1-click issue):  {links}  ·  "
        f"[`type your own →`]({issue_link('your command here')})", "",
        "<sub>a real, shared terminal: your command opens an issue → a GitHub Action "
        "runs it (sandboxed, not a shell) → the result is written back here in ~30s. "
        "you're in `harryngai/harryngai`, the repo behind this profile.</sub>", "",
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
    render(s)
    OUTF.write_text((output or "(rendered)") + "\n")

if __name__ == "__main__":
    main()
