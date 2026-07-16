<div align="center">

```
╭────────────────────────────────────────────────────╮
│                                                    │
│   guest @ github : ~                    [ o o o ]  │
│                                                    │
│   $ ssh guest@github.com                           │
│   Last login: the moment you clicked in            │
│   $ cat README.md                                  │
│                                                    │
╰────────────────────────────────────────────────────╯
```

**a terminal that happens to be a GitHub profile**

</div>

---

### `~/README.md`

You've found **`harryngai/harryngai`** — the "magic" repo whose `README.md` GitHub
splices onto my profile page. Most people put a résumé here. This one boots a shell.

There is deliberately **nothing about me** below. Instead: a self-contained toy box —
no JavaScript, no trackers, no external images — just `<details>` tags coerced into
behaving like an interactive terminal. Click the prompts. Poke around. There's a
`flag{}` hidden in here somewhere.

<br>

<details>
<summary><code>guest@github:~$ ls -la</code></summary>

<br>

```
drwx------   the-box/
-rw-r--r--   motd          <- start here
-rw-r--r--   .hint         <- you'll want this
-r--------   vault.enc     <- locked
drwxr-xr-x   games/        <- ...why not
```

Open the files below, roughly in order.

</details>

<details>
<summary><code>guest@github:~$ cat motd</code></summary>

<br>

```
╭─────────────────────── motd ───────────────────────╮
│                                                    │
│   Welcome, stranger.                               │
│                                                    │
│   #1  the box tells you nothing it needn't.        │
│   #2  everything here is text. it still moves.     │
│   #3  the flag is real. decode your way in.        │
│                                                    │
╰────────────────────────────────────────────────────╯
```

</details>

<details>
<summary><code>guest@github:~$ cat .hint</code></summary>

<br>

> `vault.enc` is sealed with a passphrase, and the passphrase is hiding in plain
> sight — it's just wearing a **base64** disguise:

```
b3Blbi1zZXNhbWU=
```

> Decode it yourself (`echo b3Blbi1zZXNhbWU= | base64 -d`) — or cheat:

<details>
<summary><code>&nbsp;&nbsp;&nbsp;./decode</code></summary>

<br>

```
open-sesame
```

</details>

</details>

<details>
<summary><code>guest@github:~$ unlock vault.enc --key open-sesame</code></summary>

<br>

```
╭──────────────────── vault.enc ─────────────────────╮
│                                                    │
│   [+] key accepted                                 │
│   [+] decrypting ......................  ok        │
│                                                    │
│        V A U L T   U N L O C K E D                 │
│                                                    │
│        flag{ y0u_read_the_manual }                 │
│                                                    │
╰────────────────────────────────────────────────────╯
```

Nicely done. Now `cd games/` — or go touch some grass.

</details>

<details>
<summary><code>guest@github:~$ cd games/ &amp;&amp; ./rps</code></summary>

<br>

Rock · paper · scissors. I've already thrown. Pick yours:

<details><summary><code>&nbsp;(R) rock</code></summary><br>I threw scissors. **You win.** Suspicious — best of three?</details>
<details><summary><code>&nbsp;(P) paper</code></summary><br>I threw scissors. **I win.** Snip.</details>
<details><summary><code>&nbsp;(S) scissors</code></summary><br>I threw rock. **I win.** Skill issue.</details>

</details>

---

<div align="center">

```
╭─────────────────────── stat ───────────────────────╮
│                                                    │
│   uptime ........ ##################  since forever│
│   coffee->code .. ################..  92%          │
│   repos public .. 3                                │
│   repos secret .. [ REDACTED ]                     │
│   bio ........... ..................  left blank   │
│                                                    │
╰────────────────────────────────────────────────────╯
```

*You reached the end of a README that refused to talk about its author.*
*That was the point.*

</div>
