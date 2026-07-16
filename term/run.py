#!/usr/bin/env python3
"""
The engine behind the profile terminal.

It is NOT a shell. It's a fixed dispatch table: a visitor's command string is
matched against known commands and produces text. Nothing the visitor types is
ever executed. Output is sanitized so it can't break out of the README code
fence or inject HTML.

Run modes (driven by env):
  CMD set    -> process one command, append to transcript, re-render README
  CMD empty  -> just re-render README from the current session (used to seed)
"""
import base64, datetime, json, os, pathlib, random, re, urllib.parse

def now_utc(fmt="%Y-%m-%d %H:%M UTC"):
    return datetime.datetime.now(datetime.timezone.utc).strftime(fmt)

ROOT   = pathlib.Path(__file__).resolve().parent.parent
STATE  = ROOT / "term" / "session.json"
OUTF   = ROOT / "term" / "last_output.txt"
README = ROOT / "README.md"

USER      = "harryngai"                 # profile owner (repo = USER/USER)
SHOWLINES = 18                          # transcript lines rendered in the README
KEEPLOG   = 250                         # commands retained in session.json
CREATED   = "2024-02-23"                # account birthday, for uptime

# ── session ────────────────────────────────────────────────────────────────
def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"count": 0, "log": [], "last_actor": None, "last_time": None}

def save(s):
    s["log"] = s["log"][-KEEPLOG:]
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n")

# ── safety ─────────────────────────────────────────────────────────────────
def clean(s, n=600):
    s = s.replace("`", "'").replace("\r", "")
    s = re.sub(r"[<>]", "", s)          # no raw HTML into the README
    return s[:n]

# ── the "filesystem" ───────────────────────────────────────────────────────
KEY_PLAIN = "open-sesame"
KEY_B64   = base64.b64encode(KEY_PLAIN.encode()).decode()

FILES = {
    "motd": (
        "welcome, stranger.\n"
        "  this box is a real terminal wearing a github profile.\n"
        "  every command you run is executed by a robot and written back here.\n"
        "  rule: the box says nothing about its owner. try `help`."
    ),
    ".hint": (
        "vault.enc is sealed with a passphrase.\n"
        "the key is in plain sight, just base64'd:  " + KEY_B64 + "\n"
        "decode it, then run:  unlock <key>"
    ),
    "vault.enc": "\x00\x00 sealed. run:  unlock <key>",
    "readme.md": "you're soaking in it.",
}

LS = [".", "..", "motd", ".hint", "vault.enc", "games/", "readme.md"]

FORTUNES = [
    "the best code is no code.",
    "there are 2 hard problems in CS: cache invalidation, naming, and off-by-one.",
    "a VPN is just someone else's computer you trust more.",
    "prod is the only real test environment.",
    "`rm -rf` builds character.",
    "the network is reliable. — a liar",
    "you are not stuck in traffic. you are traffic.",
    "ship it. we'll fix it in post.",
]

def neofetch(s):
    now = now_utc()
    return "\n".join([
        "        _____         " + USER + "@github",
        "       /     \\        " + "-" * (len(USER) + 7),
        "      | () () |       os      github-actions · ubuntu",
        "       \\  ^  /        shell   interp.py (sandboxed)",
        "        |||||         cmds    %d run" % s["count"],
        "        |||||         last    @%s" % (s["last_actor"] or "nobody"),
        "                      clock   " + now,
        "                      uptime  since " + CREATED,
    ])

def cowsay(text):
    text = text or "moo"
    bar = "-" * (len(text) + 2)
    return "\n".join([
        " " + bar,
        "< " + text + " >",
        " " + "-" * (len(text) + 2),
        "        \\   ^__^",
        "         \\  (oo)\\_______",
        "            (__)\\       )\\/\\",
        "                ||----w |",
        "                ||     ||",
    ])

FLAG = "\n".join([
    "[+] key accepted",
    "[+] decrypting .......... ok",
    "",
    "    V A U L T   U N L O C K E D",
    "    flag{ y0u_r4n_the_term1nal }",
])

# ── the interpreter ────────────────────────────────────────────────────────
def interpret(line, s):
    line = line.strip()
    if not line:
        return ""
    parts = line.split()
    cmd, args = parts[0].lower(), parts[1:]
    rest = " ".join(args)
    rnd = random.Random(f"{s['count']}:{line}")   # deterministic-ish per run

    if cmd == "help":
        return ("commands:\n"
                "  help  ls  cat <f>  whoami  id  date  uptime  echo <t>\n"
                "  neofetch  fortune  cowsay <t>  history  rps <r|p|s>\n"
                "  unlock <key>  sudo <..>  clear  about\n"
                "hidden ones exist. poke around.")
    if cmd == "ls":
        return "  ".join(LS)
    if cmd == "cat":
        if not args:
            return "cat: missing operand"
        f = args[0].lower()
        return FILES.get(f, f"cat: {args[0]}: No such file or directory")
    if cmd == "whoami":
        return f"guest — visitor #{s['count']+1}, clearance: curious, taste: impeccable"
    if cmd == "id":
        return "uid=1000(guest) gid=1000(guest) groups=1000(guest),27(the-curious)"
    if cmd == "date":
        return now_utc("%a %d %b %Y %H:%M:%S UTC")
    if cmd == "uptime":
        d = (datetime.date.today() - datetime.date.fromisoformat(CREATED)).days
        return f"up {d} days,  load average: 0.42, 0.17, 0.09,  vibes: immaculate"
    if cmd == "echo":
        return clean(rest)
    if cmd == "neofetch":
        return neofetch(s)
    if cmd == "fortune":
        return rnd.choice(FORTUNES)
    if cmd == "cowsay":
        return cowsay(clean(rest, 60))
    if cmd == "history":
        h = [f"  {i+1}  {e['cmd']}" for i, e in enumerate(s["log"][-10:])]
        return "\n".join(h) or "  (empty)"
    if cmd == "rps":
        me = rnd.choice(["rock", "paper", "scissors"])
        you = (args[0].lower() if args else "")
        norm = {"r": "rock", "p": "paper", "s": "scissors",
                "rock": "rock", "paper": "paper", "scissors": "scissors"}
        you = norm.get(you)
        if not you:
            return "usage: rps <rock|paper|scissors>"
        beats = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        if you == me:
            res = "draw"
        elif beats[you] == me:
            res = "you win"
        else:
            res = "i win"
        return f"you: {you}  ·  me: {me}  →  {res}"
    if cmd == "unlock":
        return FLAG if (args and args[0] == KEY_PLAIN) else "access denied. read `.hint`."
    if cmd == "sudo":
        return "guest is not in the sudoers file. this incident will be reported. (jk)"
    if cmd in ("rm", "rmdir"):
        return "nice try. this filesystem is load-bearing."
    if cmd in ("curl", "wget"):
        return f"{cmd}: this terminal has no egress. (it's a security thing.)"
    if cmd == "clear":
        s["log"] = []
        return "__CLEAR__"
    if cmd in ("about", "whoami-owner", "whois"):
        return "operator: [REDACTED]. the box is more interesting than its owner — by design."
    if cmd == "exit":
        return "there is no exit. there is only more terminal."
    if cmd in ("ping",):
        return "pong"
    if cmd in ("hello", "hi"):
        return "hi. type `help`."
    return f"{cmd}: command not found. try `help`."

# ── README rendering ───────────────────────────────────────────────────────
def issue_link(cmd, label=None):
    q = urllib.parse.urlencode({
        "title": "$ " + cmd,
        "body": (f"Click **Submit new issue** to run `$ {cmd}` on the profile "
                 f"terminal.\n\nThe bot runs it, writes the result to the profile, "
                 f"replies here, and closes this issue (~30s). "
                 f"Then refresh https://github.com/{USER}"),
    })
    return f"https://github.com/{USER}/{USER}/issues/new?{q}"

QUICK = ["help", "ls", "whoami", "cat motd", "neofetch", "rps rock",
         "fortune", "date", "cowsay hi"]

def transcript_lines(s):
    out = []
    for e in s["log"]:
        out.append(f"guest@github:~$ {e['cmd']}")
        for ln in e["out"].split("\n"):
            out.append("  " + ln if ln else "")
    out.append("guest@github:~$ █")
    view = out[-SHOWLINES:]
    trimmed = False
    while len(view) > 1 and not view[0].startswith("guest@github"):
        view.pop(0); trimmed = True
    if trimmed:
        view = ["  ⋮"] + view
    return view

def render(s):
    now = (s["last_time"] or now_utc())
    body = transcript_lines(s)
    top = "== " + USER + "@github : /dev/profile " + "=" * 26
    bar = "=" * len(top)
    screen = "\n".join([top, ""] + body + ["", bar])
    status = (f"[ commands run: {s['count']} · "
              f"last: @{s['last_actor'] or 'nobody'} · {now} ]")

    quick = " · ".join(f"[`{c}`]({issue_link(c)})" for c in QUICK)
    freeform = issue_link("your command here")

    parts = [
        '<div align="center">', "", "```", screen, "```", "",
        status, "", "</div>", "", "---", "",
        "### ▸ this is a real terminal",
        "",
        "You've found **`%s/%s`** — the repo whose README is my GitHub profile. "
        "It's a live, shared terminal. Every command below is **actually executed** "
        "by a GitHub Action and written back to this page." % (USER, USER),
        "",
        "**Run a command** — click one (then hit *Submit new issue*):",
        "",
        quick,
        "",
        "…or [**type your own →**](%s). It's a sandboxed interpreter, not a real "
        "shell, so nothing you type can hurt anything. Try `help`. There's a "
        "`flag{}` hidden in the filesystem." % freeform,
        "",
        "<sub>how it works: your command opens a pre-filled Issue → an Action runs "
        "`term/run.py` → it appends the output here, replies, and closes the issue "
        "(~30s) → refresh the profile.</sub>",
        "",
    ]
    README.write_text("\n".join(parts) + "\n")

# ── main ───────────────────────────────────────────────────────────────────
def main():
    s = load()
    raw = os.environ.get("CMD", "")
    actor = os.environ.get("ACTOR", "").strip() or None
    cmd = raw.lstrip()
    if cmd.startswith("$"):
        cmd = cmd[1:].strip()

    output = ""
    if cmd:
        output = interpret(cmd, s)
        if output == "__CLEAR__":
            output = "cleared."
        else:
            s["log"].append({"cmd": clean(cmd, 120), "out": output})
        s["count"] += 1
        s["last_actor"] = actor or s["last_actor"]
        s["last_time"] = now_utc()
        save(s)

    render(s)
    OUTF.write_text((output or "(rendered)") + "\n")

if __name__ == "__main__":
    main()
