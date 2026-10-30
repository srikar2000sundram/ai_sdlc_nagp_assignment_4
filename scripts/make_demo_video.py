"""Record the demo video.

    python scripts/make_demo_video.py            # full recording (about 10 minutes of real time)
    DEMO_FAST=1 python scripts/make_demo_video.py  # smoke run: no waiting for the voice, video not in sync

Every command shown in the terminal scenes really runs while it is being recorded (pytest, a deliberate one-character
break that is restored afterwards, mutmut in WSL, Playwright, the log). The UI scene drives the real app on a fresh
server. The voiceover is Windows' built-in speech engine; captions repeat the narration.

Output: docs/video/demo-narrated.mp4 and docs/video/demo-captions-only.mp4
Needs: pip install imageio-ffmpeg playwright markdown pypdf  (and WSL with the mutation venv, see scripts/run_mutation.sh)
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_docs as docs  # noqa: E402  (reuses the Markdown renderer and theme)

WORK = Path(os.environ.get("TEMP", tempfile.gettempdir())) / "demo_video_work"
OUT = ROOT / "docs" / "video"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FAST = os.environ.get("DEMO_FAST") == "1"
VOICE = os.environ.get("DEMO_VOICE", "Microsoft Zira Desktop")
RATE = int(os.environ.get("DEMO_RATE", "0"))
VIDEO_W, VIDEO_H = 1280, 720
TRIM = 0.45  # the first moments of a browser recording are blank; cut them and shift the audio to match
POLICY = ROOT / "backend" / "src" / "invoice_app" / "domain" / "approval_policy.py"
POLICY_BACKUP = POLICY.with_suffix(".py.demo-bak")
OLD_BOUNDARY = "self._limits.manager < attempt.amount <= self._limits.director"
NEW_BOUNDARY = "self._limits.manager <= attempt.amount <= self._limits.director"
UI_PORT = 5057

NARRATION = {
    "intro": "This is my AI in SDLC assignment: approval limits by role for an invoice approval service. "
             "This recording was produced by a script, and every command you see really runs, live, while it is being recorded.",
    "rules": "A Manager may approve invoices up to 50,000. A Director may approve up to 500,000. "
             "Anything above that needs two different approvers, and the second one must be a Director.",
    "negatives": "The same user can never count as both approvers, and a refused attempt must give a clear reason and change nothing.",
    "port": "The original repository is C sharp and this machine has no dot net SDK, so I ported the backend to Python with FastAPI, "
            "kept the same layers, and kept the seven original tests green before touching the feature.",
    "context": "First, context. AGENTS.md is what an agent reads when it arrives cold: the approval rules, the boundaries to test, "
               "the rule that business logic lives only in the domain, the test commands, and my review expectations.",
    "expectations": "A refusal test must check the reason, and that the invoice is unchanged. A test that only checks the exception type does not count.",
    "claude_dir": "In the dot claude folder there are three skills, five agents and the hooks. The agents are a spec writer, an implementer that "
                  "does one step at a time, a test reviewer, a PR reviewer and a mutation analyst. The hooks write every prompt, tool call, "
                  "sub agent result and test run to one log, in one format.",
    "experiment": "I also checked whether the context file really matters. A cold agent with no project files still planned well. "
                  "With AGENTS.md it added cent level boundaries, username normalisation, the Admin rule, exact refusal assertions and the real commands. "
                  "The comparison is in the write up, including a first attempt I had to discard.",
    "spec": "The specification comes from Spec Kit. The clarifications are where I settled the ambiguities: the limits are inclusive, "
            "the first approver above 500,000 may be a Manager or a Director, and the same user means the same username ignoring case and spaces.",
    "tasks": "Tasks are split into two stories, single approver first, then the two approver rule, and I built them in that order.",
    "tests_run": "Now, live. First the whole test suite.",
    "tests_done": "177 tests pass in a few seconds: pure policy rules, the service with a fake repository, a shared contract for the repositories, and the HTTP API.",
    "negative_run": "These are the two negative rules the assignment warns about: the same user can never be both approvers, "
                    "and a Manager can never be the second approver.",
    "helper": "Every refusal test uses this helper. It copies the invoice, expects the refusal, asserts the exact reason text, "
              "asserts the invoice equals the copy, and asserts the repository saw no save.",
    "break": "Now I prove the tests can fail. I change one character, less than becomes less than or equal, at the Manager limit, "
             "so exactly 50,000 would be refused. The boundary test fails straight away.",
    "restored": "The file is restored and everything is green again. That is why every limit is tested one cent either side.",
    "baseline": "Passing tests are not proof that tests are good. Mutation testing changes the code in small ways and checks that a test notices. "
                "Before the feature, with the seven original tests, the score was 63.9 percent.",
    "mutation_run": "Now I run it live on the finished code, under WSL because the tool needs fork. It takes about twenty seconds.",
    "mutation_done": "132 of 132 mutants killed. It did not start there: my first pass was 81 percent with 16 survivors, all missing tests, such as a fake repository "
                     "that never saved, unasserted timestamps and unasserted messages. I added a test for each. The caveat is that this measures the domain unit tests only.",
    "e2e_run": "Next, the end to end test: a rejected over limit approval through the real user interface, using page objects and role based locators.",
    "e2e_done": "It signs in as the Manager, approves the 75,000 invoice, expects the exact refusal on screen, and checks the invoice is still pending. One passed.",
    "ui1": "And here is the feature by hand. As the demo Manager I press Approve on the 75,000 invoice. It is refused, with the reason on screen, and the invoice stays pending.",
    "ui2": "A Director can approve it alone.",
    "ui3": "The 600,000 invoice needs two approvers. After the first approval it is still pending, and shows one of two.",
    "ui4": "The same Director tries again and is refused: the same user cannot be both approvers.",
    "ui5": "A different Director completes it, and the invoice is approved.",
    "review": "I reviewed my own diff with the PR reviewer agent and judged every finding. Eleven findings: six fixed, three dismissed with reasons, two deferred with tracking tasks.",
    "review_race": "Two were real bugs. Two simultaneous approvals by the same Director both passed the already approved check, which breaks the central rule. "
                   "I fixed it with a lock, and wrote race tests that fail when the lock is removed. My first version of those tests passed without the lock, "
                   "so they proved nothing, and I rewrote them.",
    "review_amount": "The other: an enormous amount was accepted and then broke the invoice list for everyone. It is now validated and rejected with a message.",
    "log": "All AI interaction is logged by hooks into one file, one JSON object per line with the same keys every time. "
           "Test runs become check summary lines with pass or fail, including the deliberate failure from earlier.",
    "outro": "To wrap up: unit tests for every rule including both negative rules, a mutation score from 64 to 100 percent, one Playwright test, "
             "and a review with every finding judged, ready for the pull request. One honest limit: the project agents were not selectable by name in the "
             "session that created them, so three roles ran as general purpose sub agents following the agent files. Thank you for watching.",
}

SPOKEN_FIXES = [
    ("AI in SDLC", "A I in S D L C"), ("FastAPI", "Fast A P I"), ("mutmut", "mutt mutt"), ("AGENTS.md", "agents dot M D"),
    ("WSL", "W S L"), ("PRs", "P Rs"), ("PR ", "P R "), ("HTTP", "H T T P"), ("API", "A P I"), ("JSON", "jay son"),
    ("SDK", "S D K"), ("pytest", "pie test"), ("UI", "U I"),
]


def spoken(text: str) -> str:
    """Respell terms (``mutmut``, ``FastAPI``) the speech engine would mispronounce; captions keep the original text.
    """
    for written, said in SPOKEN_FIXES:
        text = text.replace(written, said)
    return text


# ----------------------------------------------------------------------------------------------------------------
# Voice
# ----------------------------------------------------------------------------------------------------------------

def synthesize() -> dict[str, tuple[str, float, Path]]:
    """Create one WAV per narration line with Windows speech and return text, duration and path for each."""
    WORK.mkdir(parents=True, exist_ok=True)
    wav_dir = WORK / "voice"
    shutil.rmtree(wav_dir, ignore_errors=True)
    wav_dir.mkdir()
    items = [{"id": key, "text": spoken(text), "path": str(wav_dir / f"{key}.wav")} for key, text in NARRATION.items()]
    (WORK / "narration.json").write_text(json.dumps(items), encoding="ascii")
    script = WORK / "synth.ps1"
    script.write_text(
        "Add-Type -AssemblyName System.Speech\n"
        "$items = Get-Content -Raw -Path '" + str(WORK / "narration.json") + "' | ConvertFrom-Json\n"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
        f"$s.SelectVoice('{VOICE}'); $s.Rate = {RATE}\n"
        "$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)\n"
        "foreach ($i in $items) { $s.SetOutputToWaveFile($i.path, $fmt); $s.Speak($i.text); $s.SetOutputToNull() }\n",
        encoding="ascii",
    )
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], check=True)
    result = {}
    for item in items:
        with wave.open(item["path"]) as handle:
            result[item["id"]] = (NARRATION[item["id"]], handle.getnframes() / handle.getframerate(), Path(item["path"]))
    total = sum(duration for _, duration, _ in result.values())
    print(f"voice: {len(result)} clips, {total / 60:.1f} minutes of speech")
    return result


# ----------------------------------------------------------------------------------------------------------------
# Live terminal: a tiny local server streams the real output of a fixed set of commands
# ----------------------------------------------------------------------------------------------------------------

def encoded_powershell(script: str) -> list[str]:
    """A PowerShell command line for a script, passed encoded so quoting cannot break it."""
    return ["powershell", "-NoProfile", "-EncodedCommand", base64.b64encode(script.encode("utf-16-le")).decode()]


def scrub(line: str) -> str:
    """The recording must not show the account name or home folder."""
    home = Path.home()
    for form in (str(home), str(home).replace("\\", "/")):
        line = line.replace(form, "~")
    return re.sub(re.escape(home.name), "user", line, flags=re.I)


def stream_process(args: list[str], cwd: Path):
    """Run a command and yield its output line by line as it is produced."""
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "NO_COLOR": "1"}
    env.pop("FORCE_COLOR", None)
    process = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for raw in iter(process.stdout.readline, b""):
        text = raw.decode("utf-8", errors="replace")
        if "systemd user session" in text:  # harmless WSL start-up notice that names the Linux account
            continue
        yield scrub(text)
    process.wait()


def command_pytest_all():
    """Run the full test suite for the terminal scene."""
    yield from stream_process([sys.executable, "-m", "pytest", "backend/tests", "-q", "--disable-warnings"], ROOT)


def command_pytest_negative():
    """Run only the two negative-rule tests."""
    yield from stream_process([sys.executable, "-m", "pytest", "backend/tests/test_approval_policy.py", "-v", "-k",
                               "same_user or second_approver", "--no-header", "--disable-warnings"], ROOT)


def command_break():
    """Change the Manager limit comparison, run the tests so they fail, and always restore the file afterwards."""
    original = POLICY.read_text(encoding="utf-8")
    broken = original.replace(OLD_BOUNDARY, NEW_BOUNDARY)
    if broken == original:
        yield "could not find the Manager limit comparison\n"
        return
    line = next(n for n, text in enumerate(original.splitlines(), start=1) if OLD_BOUNDARY in text)
    shutil.copy2(POLICY, POLICY_BACKUP)
    try:
        POLICY.write_text(broken, encoding="utf-8")
        yield f"edited approval_policy.py line {line}:  manager < amount  ->  manager <= amount  (Manager limit rule)\n\n"
        yield from stream_process([sys.executable, "-m", "pytest", "backend/tests", "-q", "-x", "--tb=short", "--disable-warnings"], ROOT)
    finally:
        shutil.copy2(POLICY_BACKUP, POLICY)
        POLICY_BACKUP.unlink(missing_ok=True)
    yield "\nrestored approval_policy.py (byte for byte)\n"


def command_mutation():
    """Run the mutation script in WSL and delete its demo report."""
    yield from stream_process(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "scripts/run_mutation.sh", "demo"], ROOT)
    (ROOT / "docs" / "mutation" / "demo.txt").unlink(missing_ok=True)


def command_e2e():
    """Run the Playwright test."""
    yield from stream_process(["cmd", "/c", "npx", "playwright", "test", "--reporter=list"], ROOT / "e2e")


LOG_SCRIPT = (
    'Get-Content logs\\ai-interactions.jsonl | Select-String \'"event": "CheckSummary"\' | Select-Object -Last 7 | '
    'ForEach-Object { $r = $_.Line | ConvertFrom-Json; "{0}  {1}" -f $r.timestamp.Substring(0,19), $r.summary }'
)


def command_log():
    """Show the latest check summaries and the log's line count."""
    yield from stream_process(encoded_powershell(LOG_SCRIPT), ROOT)
    yield from stream_process(encoded_powershell("'{0} lines in the log' -f (Get-Content logs\\ai-interactions.jsonl).Count"), ROOT)


COMMANDS = {
    "pytest_all": command_pytest_all, "pytest_negative": command_pytest_negative, "break": command_break,
    "mutation": command_mutation, "e2e": command_e2e, "log": command_log,
}

TERMINAL_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>terminal</title><style>
*{box-sizing:border-box}body{margin:0;background:linear-gradient(160deg,#07142b,#0b1e3f);font-family:Consolas,'Courier New',monospace;height:100vh;overflow:hidden}
.win{position:absolute;left:36px;right:36px;top:30px;bottom:112px;background:#0b1220;border:1px solid #1f3a5f;border-radius:12px;box-shadow:0 14px 40px rgba(0,0,0,.45);display:flex;flex-direction:column;overflow:hidden}
.bar{height:38px;background:#12203a;display:flex;align-items:center;padding:0 14px;gap:8px;color:#8fa6c2;font:13px 'Segoe UI',Arial,sans-serif;border-bottom:1px solid #1f3a5f}
.dot{width:12px;height:12px;border-radius:50%}.d1{background:#ff5f57}.d2{background:#febc2e}.d3{background:#28c840}
.live{margin-left:auto;display:none;align-items:center;gap:7px;color:#ff8a8a;font-weight:600;letter-spacing:.12em}
.live i{width:10px;height:10px;border-radius:50%;background:#ff4d4d;animation:p 1s infinite}@keyframes p{50%{opacity:.2}}
#out{padding:16px 20px;overflow:auto;flex:1;font-size:15px;line-height:1.5;color:#d6e2f0;white-space:pre-wrap;word-break:break-word}
.ps{color:#2dd4bf}.cmd{color:#fff}.cur{display:inline-block;width:9px;height:17px;background:#2dd4bf;vertical-align:text-bottom;animation:b 1s steps(1) infinite}@keyframes b{50%{opacity:0}}
.ok{color:#5eead4}.bad{color:#ff7b7b}.dim{color:#7b8fa8}
</style></head><body><div class="win"><div class="bar"><span class="dot d1"></span><span class="dot d2"></span><span class="dot d3"></span>
<span style="margin-left:10px">PowerShell  -  invoice-approval</span><span class="live" id="live"><i></i>LIVE</span></div><div id="out"></div></div>
<script>
const out=document.getElementById('out'),sleep=ms=>new Promise(r=>setTimeout(r,ms));let line;
function prompt(){line=document.createElement('div');line.innerHTML='<span class="ps">PS invoice-approval&gt;</span> <span class="cmd"></span><span class="cur"></span>';out.appendChild(line);out.scrollTop=out.scrollHeight}
function add(t){const d=document.createElement('div');t=t.replace(/\\x1b\\[[0-9;]*m/g,'').replace(/\\r/g,'');
 d.className=/failed|FAILED|Error|error/.test(t)?'bad':/passed|PASSED|killed|100\\.0%|Mutation score|✓/.test(t)?'ok':(/^\\s*$/.test(t)?'':'');d.textContent=t||' ';out.appendChild(d);out.scrollTop=out.scrollHeight}
window.term={async run(id,show,speed){const c=line.querySelector('.cmd');for(const ch of show){c.textContent+=ch;await sleep(speed||24)}
 await sleep(400);line.querySelector('.cur').remove();document.getElementById('live').style.display='flex';
 const res=await fetch('/run?id='+id);const rd=res.body.getReader(),dec=new TextDecoder();let buf='';
 for(;;){const{done,value}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});const parts=buf.split('\\n');buf=parts.pop();parts.forEach(add)}
 if(buf)add(buf);document.getElementById('live').style.display='none';prompt()},clear(){out.innerHTML='';prompt()}};
prompt();
</script></body></html>"""


class TerminalHandler(BaseHTTPRequestHandler):
    """Serves the terminal page and streams the real output of a fixed list of commands (nothing else can be run)."""

    protocol_version = "HTTP/1.0"

    def log_message(self, *_):
        """Silence the server's request log."""
        pass

    def do_GET(self):  # noqa: N802
        """Serve the page, or stream a known command's output; anything else is a 404."""
        url = urlparse(self.path)
        if url.path == "/":
            body = TERMINAL_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif url.path == "/run" and parse_qs(url.query).get("id", [""])[0] in COMMANDS:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            for chunk in COMMANDS[parse_qs(url.query)["id"][0]]():
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
        else:
            self.send_error(404)


def start_terminal_server() -> tuple[ThreadingHTTPServer, str]:
    """Start the local terminal server on a free port and return it with its URL."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), TerminalHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


# ----------------------------------------------------------------------------------------------------------------
# Browser overlay (captions, visible cursor) and scenes
# ----------------------------------------------------------------------------------------------------------------

OVERLAY_JS = """(()=>{
 function init(){ if(document.getElementById('__cap'))return;
  const k=innerWidth>1400?1.3:1;
  const s=document.createElement('style');s.textContent=`#__cap{position:fixed;left:50%;bottom:${24*k}px;transform:translateX(-50%);width:max-content;max-width:${1080*k}px;padding:${12*k}px ${22*k}px;
  background:rgba(7,20,43,.88);color:#fff;font:500 ${22*k}px/1.4 "Segoe UI",Arial,sans-serif;border-radius:12px;border:1px solid rgba(20,184,166,.55);text-align:center;opacity:0;
  transition:opacity .25s;z-index:2147483647;pointer-events:none}#__cap.on{opacity:1}
  #__cur{position:fixed;width:24px;height:24px;border-radius:50%;border:3px solid #14b8a6;background:rgba(20,184,166,.28);z-index:2147483646;pointer-events:none;
  transform:translate(-50%,-50%);display:none;transition:transform .08s}#__cur.down{transform:translate(-50%,-50%) scale(.65);background:rgba(20,184,166,.7)}`;
  document.head.appendChild(s);
  const c=document.createElement('div');c.id='__cap';document.body.appendChild(c);
  const u=document.createElement('div');u.id='__cur';document.body.appendChild(u);}
 if(document.readyState!=='loading')init();else addEventListener('DOMContentLoaded',init);
 window.__cap=t=>{init();const c=document.getElementById('__cap');if(t){c.textContent=t;c.classList.add('on')}else{c.classList.remove('on');setTimeout(()=>{if(!c.classList.contains('on'))c.textContent=''},350)}};
 addEventListener('mousemove',e=>{init();const u=document.getElementById('__cur');u.style.display='block';u.style.left=e.clientX+'px';u.style.top=e.clientY+'px'},true);
 addEventListener('mousedown',()=>{const u=document.getElementById('__cur');u&&u.classList.add('down')},true);
 addEventListener('mouseup',()=>{const u=document.getElementById('__cur');u&&u.classList.remove('down')},true);
})();"""

VIEW_CSS = """
body{margin:0;background:#fff}.bar{position:sticky;top:0;z-index:5;background:#12203a;color:#cfe0f3;font:14px Consolas,monospace;padding:10px 24px;display:flex;gap:10px;align-items:center;border-bottom:3px solid #14b8a6}
.bar b{color:#4be3d2;font-weight:600}.doc{padding:18px 56px 160px;font-size:12.5pt;max-width:1180px;margin:0 auto}.doc pre{font-size:11pt}
"""

CARD_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;height:100vh;overflow:hidden;color:#fff;font-family:'Segoe UI',Arial,sans-serif;background:linear-gradient(150deg,#07142b,#0b1e3f 55%,#0d3157)}
.o{position:absolute;border-radius:50%}.o1{width:620px;height:620px;right:-170px;top:-230px;background:radial-gradient(circle at 32% 32%,#2ed9c5,#14b8a6 38%,#0c7c86 66%,rgba(12,124,177,0) 72%)}
.o2{width:430px;height:430px;right:-60px;top:-110px;border:1.2px solid rgba(255,255,255,.22)}.o3{width:300px;height:300px;left:-130px;bottom:-140px;border:1.2px solid rgba(20,184,166,.5)}
.c{position:absolute;left:90px;top:250px}.k{color:#4be3d2;letter-spacing:.32em;font-size:15px;text-transform:uppercase;font-weight:600}
h1{font:400 64px/1.1 Georgia,serif;margin:20px 0 22px;white-space:pre-line}.r{width:90px;height:4px;background:#14b8a6;border-radius:2px}
p{font-size:23px;color:#c6d6e8;font-weight:300;margin:24px 0 0;max-width:820px;line-height:1.5}
.ch{margin-top:34px;display:flex;gap:10px;flex-wrap:wrap}.ch span{font-size:15px;padding:5px 14px;border:1px solid rgba(75,227,210,.5);border-radius:20px;color:#bff3ec}
</style></head><body><div class="o o1"></div><div class="o o2"></div><div class="o o3"></div><div class="c"><div class="k">KICKER</div><h1>TITLE</h1><div class="r"></div><p>SUB</p><div class="ch">CHIPS</div></div></body></html>"""


def card(kicker: str, title: str, sub: str, chips: tuple[str, ...]) -> Path:
    """Write a full-screen title card page and return its path."""
    page = (CARD_HTML.replace("KICKER", kicker).replace("TITLE", title).replace("SUB", sub)
            .replace("CHIPS", "".join(f"<span>{c}</span>" for c in chips)))
    path = WORK / f"card-{abs(hash(title))}.html"
    path.write_text(page, encoding="utf-8")
    return path


def view_page(name: str, file_label: str, inner_html: str) -> Path:
    """Write a document-viewer page (title bar plus rendered content) and return its path."""
    page = (f"<!doctype html><html><head><meta charset='utf-8'><style>{docs.BODY_CSS}{VIEW_CSS}</style></head><body>"
            f"<div class='bar'><b>&#9679;</b> {file_label}</div><div class='doc'>{inner_html}</div></body></html>")
    path = WORK / f"view-{name}.html"
    path.write_text(page, encoding="utf-8")
    return path


def markdown_view(name: str, source: Path, label: str) -> Path:
    """A viewer page for a Markdown file."""
    text = docs.strip_front_matter(source.read_text(encoding="utf-8"))
    return view_page(name, label, docs.render_markdown(text))


def text_view(name: str, label: str, text: str, highlight: tuple[str, ...] = ()) -> Path:
    """A viewer page for plain text with line numbers and optional highlighted lines."""
    import html as html_lib
    lines = []
    for number, line in enumerate(text.splitlines(), start=1):
        mark = ' style="background:#e6f6f4;display:block"' if any(h in line for h in highlight) else ' style="display:block"'
        lines.append(f"<span{mark}><span style='color:#9aa8b8'>{number:>4}  </span>{html_lib.escape(line)}</span>")
    return view_page(name, label, "<pre><code>" + "\n".join(lines) + "</code></pre>")


class Scene:
    """One browser page recorded to its own video; narration clips are placed where each step starts."""

    def __init__(self, browser, name: str, voice: dict, viewport=(VIDEO_W, VIDEO_H)):
        """Open a browser context that records video, with the caption overlay installed."""
        self.name, self.voice, self.events = name, voice, []
        self.dir = WORK / "scenes" / name
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(parents=True)
        self.context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                                           record_video_dir=str(self.dir), record_video_size={"width": VIDEO_W, "height": VIDEO_H})
        self.context.add_init_script(OVERLAY_JS)
        self.page = self.context.new_page()
        self.t0 = time.monotonic()

    def goto(self, target):
        """Open a URL or local file."""
        self.page.goto(target if isinstance(target, str) else target.as_uri())

    def pause(self, seconds: float):
        """Wait a moment (almost none in fast mode)."""
        time.sleep(0.2 if FAST else seconds)

    def say(self, key: str, action=None):
        """Show a caption, run the action, and hold until the narration clip has finished."""
        text, duration, _ = self.voice[key]
        started = time.monotonic()
        self.events.append((started - self.t0, key))
        self.page.evaluate("t => window.__cap(t)", text)
        if action:
            action()
        left = duration + 0.5 - (time.monotonic() - started)
        if left > 0 and not FAST:
            time.sleep(left)
        self.page.evaluate("() => window.__cap('')")
        self.pause(0.35)

    def finish(self) -> dict:
        """Close the page and return its video file and narration timings."""
        self.pause(0.6)
        video = self.page.video
        self.context.close()
        return {"name": self.name, "video": Path(video.path()), "events": self.events}


def scroll_to(page, heading: str, block: str = "start"):
    """Smoothly scroll a heading into view."""
    page.evaluate(
        "([text, block]) => { const h=[...document.querySelectorAll('h1,h2,h3,h4')].find(e=>e.textContent.includes(text));"
        " if(h) h.scrollIntoView({behavior:'smooth', block}); }", [heading, block])


def scroll_by(page, pixels: int):
    """Smoothly scroll by a number of pixels."""
    page.evaluate("y => window.scrollBy({top:y, behavior:'smooth'})", pixels)


def run_in_terminal(scene: Scene, command_id: str, shown: str, speed: int = 24):
    """Type a command into the terminal page and wait until it finishes."""
    scene.page.evaluate("([id, shown, speed]) => window.term.run(id, shown, speed)", [command_id, shown, speed])


def human_click(page, locator):
    """Move the visible cursor to an element, then click it."""
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=22)
    time.sleep(0.25)
    page.mouse.down()
    time.sleep(0.08)
    page.mouse.up()
    time.sleep(0.35)


def human_type(page, locator, text: str):
    """Click a field, select its content and type text at a human pace."""
    human_click(page, locator)
    page.keyboard.press("Control+A")
    page.keyboard.type(text, delay=55)


def sign_in(page, username: str):
    """Sign in through the real form."""
    human_type(page, page.get_by_label("Username"), username)
    human_type(page, page.get_by_label("Password"), "ChangeMe123!")
    human_click(page, page.get_by_role("button", name="Sign in"))
    page.get_by_text(f"{username} (").wait_for()


# ----------------------------------------------------------------------------------------------------------------
# The script of the video
# ----------------------------------------------------------------------------------------------------------------

def record_all(browser, voice: dict, terminal_url: str) -> list[dict]:
    """Record every scene in order and return their videos and timings."""
    results = []

    scene = Scene(browser, "01-intro", voice)
    scene.goto(card("AI in SDLC  ·  Live demo", "Approval limits\nby role", "Manager and Director limits, two distinct approvers above 500,000, and refusals that change nothing.",
                    ("Python", "FastAPI", "pytest", "mutmut", "Playwright", "Spec Kit")))
    scene.pause(0.8)
    scene.say("intro")
    results.append(scene.finish())

    scene = Scene(browser, "02-readme", voice)
    scene.goto(markdown_view("readme", ROOT / "README.md", "README.md"))
    scene.pause(0.8)
    scene.say("rules", lambda: scroll_to(scene.page, "Approval limits by role"))
    scene.say("negatives")
    scene.say("port", lambda: scroll_to(scene.page, "What it does"))
    results.append(scene.finish())

    scene = Scene(browser, "03-context", voice)
    scene.goto(markdown_view("agents", ROOT / "AGENTS.md", "AGENTS.md"))
    scene.pause(0.8)
    scene.say("context", lambda: scroll_to(scene.page, "Approval rules"))
    scene.say("expectations", lambda: scroll_to(scene.page, "Review expectations"))
    claude_tree = "\n".join(sorted(
        str(p.relative_to(ROOT)).replace("\\", "/") + ("/" if p.is_dir() else "")
        for p in [ROOT / ".claude" / "settings.json", ROOT / ".claude" / "agents", ROOT / ".claude" / "hooks", ROOT / ".claude" / "skills"]
        + list((ROOT / ".claude" / "agents").glob("*.md")) + list((ROOT / ".claude" / "hooks").glob("*.py"))
        + [d for d in (ROOT / ".claude" / "skills").iterdir() if not d.name.startswith("speckit")]
    ))
    scene.goto(text_view("claude", ".claude/  (skills, agents, hooks)", claude_tree))
    scene.pause(0.5)
    scene.say("claude_dir")
    scene.goto(markdown_view("assignment", ROOT / "ASSIGNMENT.md", "ASSIGNMENT.md  -  section 7: does the context file matter?"))
    scene.pause(0.6)
    scene.say("experiment", lambda: scroll_to(scene.page, "Does the context file matter"))
    results.append(scene.finish())

    scene = Scene(browser, "04-spec", voice)
    spec = ROOT / "specs" / "001-invoice-approval-limits"
    scene.goto(markdown_view("spec", spec / "spec.md", "specs/001-invoice-approval-limits/spec.md"))
    scene.pause(0.8)
    scene.say("spec", lambda: scroll_to(scene.page, "Clarifications"))
    scene.goto(markdown_view("tasks", spec / "tasks.md", "specs/001-invoice-approval-limits/tasks.md"))
    scene.pause(0.5)
    scene.say("tasks", lambda: scroll_to(scene.page, "Phase 2"))
    results.append(scene.finish())

    scene = Scene(browser, "05-tests", voice)
    scene.goto(terminal_url)
    scene.pause(0.8)
    scene.say("tests_run", lambda: run_in_terminal(scene, "pytest_all", "python -m pytest backend/tests -q --disable-warnings"))
    scene.say("tests_done")
    scene.say("negative_run", lambda: run_in_terminal(
        scene, "pytest_negative", 'python -m pytest backend/tests/test_approval_policy.py -v -k "same_user or second_approver" --disable-warnings', 16))
    results.append(scene.finish())

    scene = Scene(browser, "06-helper", voice)
    service_tests = (ROOT / "backend" / "tests" / "test_approval_service.py").read_text(encoding="utf-8")
    start = service_tests.index("def assert_refused_and_unchanged")
    end = service_tests.index("\n\n\n", start)
    scene.goto(text_view("helper", "backend/tests/test_approval_service.py", service_tests[start:end],
                         highlight=("deepcopy", "pytest.raises", "assert ")))
    scene.pause(0.8)
    scene.say("helper")
    results.append(scene.finish())

    scene = Scene(browser, "07-break", voice)
    scene.goto(terminal_url)
    scene.pause(0.8)
    scene.say("break", lambda: run_in_terminal(scene, "break", "# change < to <= in the Manager limit rule, run the tests, then restore the file", 14))
    scene.say("restored", lambda: run_in_terminal(scene, "pytest_all", "python -m pytest backend/tests -q --disable-warnings"))
    results.append(scene.finish())

    scene = Scene(browser, "08-mutation", voice)
    scene.goto(text_view("baseline", "docs/mutation/baseline.txt", (ROOT / "docs" / "mutation" / "baseline.txt").read_text(encoding="utf-8"),
                         highlight=("Mutation score",)))
    scene.pause(0.8)
    scene.say("baseline")
    scene.goto(terminal_url)
    scene.pause(0.5)
    scene.say("mutation_run", lambda: run_in_terminal(scene, "mutation", "wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh demo", 22))
    scene.say("mutation_done")
    results.append(scene.finish())

    scene = Scene(browser, "09-e2e", voice)
    scene.goto(terminal_url)
    scene.pause(0.8)
    scene.say("e2e_run", lambda: run_in_terminal(scene, "e2e", "cd e2e; npx playwright test --reporter=list", 24))
    scene.say("e2e_done")
    results.append(scene.finish())

    results.append(record_ui(browser, voice))

    scene = Scene(browser, "11-review", voice)
    scene.goto(markdown_view("review", ROOT / "docs" / "pr-review.md", "docs/pr-review.md  -  every finding has one verdict"))
    scene.pause(0.8)
    scene.say("review", lambda: scroll_to(scene.page, "AI review of this diff"))
    scene.say("review_race", lambda: scroll_by(scene.page, 380))
    scene.say("review_amount", lambda: scroll_by(scene.page, 330))
    results.append(scene.finish())

    scene = Scene(browser, "12-log", voice)
    scene.goto(terminal_url)
    scene.pause(0.8)
    shown = "Get-Content logs\\ai-interactions.jsonl | Select-String '\"event\": \"CheckSummary\"' | Select-Object -Last 7 | ForEach-Object { ... }"
    scene.say("log", lambda: run_in_terminal(scene, "log", shown, 12))
    results.append(scene.finish())

    scene = Scene(browser, "13-outro", voice)
    scene.goto(card("Summary", "Rules enforced.\nTests that can fail.", "177 tests  ·  mutation score 63.9% to 100%  ·  one Playwright test  ·  11 review findings, each with a verdict",
                    ("Unit tests for every rule", "Both negative rules", "Spec Kit", "Hooks and log", "Reviewed")))
    scene.pause(0.8)
    scene.say("outro")
    results.append(scene.finish())
    return results


def record_ui(browser, voice: dict) -> dict:
    """Record the UI walkthrough against a fresh server."""
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "invoice_app.api.main:app", "--app-dir", str(ROOT / "backend" / "src"),
         "--host", "127.0.0.1", "--port", str(UI_PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urlopen(f"http://127.0.0.1:{UI_PORT}/", timeout=1)
                break
            except OSError:
                time.sleep(0.3)
        scene = Scene(browser, "10-ui", voice, viewport=(1600, 900))
        page = scene.page
        scene.goto(f"http://127.0.0.1:{UI_PORT}/")
        page.get_by_role("heading", name="Sign in").wait_for()
        scene.pause(0.8)

        def manager_refused():
            """Sign in as the Manager and press Approve on the 75,000.00 invoice; wait for the refusal message."""
            sign_in(page, "demo.manager")
            human_click(page, page.get_by_role("tab", name="Approvals"))
            human_click(page, page.get_by_role("button", name="Approve invoice INV-2001"))
            page.get_by_role("alert").filter(has_text="Manager may approve").wait_for()
            time.sleep(1.2)

        def director_approves_small():
            """Sign in as a Director and approve the 75,000.00 invoice; wait until it leaves the list."""
            human_click(page, page.get_by_role("button", name="Sign out"))
            sign_in(page, "demo.director")
            human_click(page, page.get_by_role("tab", name="Approvals"))
            human_click(page, page.get_by_role("button", name="Approve invoice INV-2001"))
            page.get_by_role("button", name="Approve invoice INV-2001").wait_for(state="detached")

        def first_of_two():
            """Approve the 600,000.00 invoice once and wait for the 1 of 2 approvals text."""
            human_click(page, page.get_by_role("button", name="Approve invoice INV-2002"))
            page.get_by_text("1 of 2").first.wait_for()
            time.sleep(0.8)

        def same_user_refused():
            """Approve the same invoice again as the same user and wait for the refusal message."""
            human_click(page, page.get_by_role("button", name="Approve invoice INV-2002"))
            page.get_by_role("alert").filter(has_text="already approved").wait_for()
            time.sleep(1.0)

        def second_director():
            """Sign in as the second Director, approve, and wait until the invoices table shows Approved."""
            human_click(page, page.get_by_role("button", name="Sign out"))
            sign_in(page, "demo.director2")
            human_click(page, page.get_by_role("tab", name="Approvals"))
            human_click(page, page.get_by_role("button", name="Approve invoice INV-2002"))
            human_click(page, page.get_by_role("tab", name="Invoices"))
            page.get_by_role("row").filter(has_text="INV-2002").get_by_text("Approved").wait_for()
            time.sleep(1.0)

        scene.say("ui1", manager_refused)
        scene.say("ui2", director_approves_small)
        scene.say("ui3", first_of_two)
        scene.say("ui4", same_user_refused)
        scene.say("ui5", second_director)
        return scene.finish()
    finally:
        server.terminate()


# ----------------------------------------------------------------------------------------------------------------
# Assembly
# ----------------------------------------------------------------------------------------------------------------

def ffmpeg(*args: str) -> str:
    """Run ffmpeg and raise with its error output if it fails."""
    result = subprocess.run([FFMPEG, "-y", "-hide_banner", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1500:])
    return result.stderr


def duration_of(path: Path) -> float:
    """Length of a media file in seconds."""
    probe = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def build_audio(scene: dict, voice: dict, length: float) -> Path:
    """Place each narration clip at its recorded time on a silent track the length of the scene."""
    rate = 44100
    track = bytearray(int(length * rate) * 2)
    for started, key in scene["events"]:
        with wave.open(str(voice[key][2])) as clip:
            data = clip.readframes(clip.getnframes())
        offset = int(max(0.0, started - TRIM) * rate) * 2
        data = data[: max(0, len(track) - offset)]
        track[offset:offset + len(data)] = data
    path = WORK / "scenes" / f"{scene['name']}.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(bytes(track))
    return path


def assemble(scenes: list[dict], voice: dict) -> None:
    """Encode the scenes, add the voice, and join them into the narrated and captions-only videos."""
    OUT.mkdir(parents=True, exist_ok=True)
    segments = {"narrated": [], "captions-only": []}
    for scene in scenes:
        length = duration_of(scene["video"]) - TRIM
        audio = build_audio(scene, voice, length)
        for variant in segments:
            target = WORK / "scenes" / f"{scene['name']}-{variant}.mp4"
            video_args = ["-ss", str(TRIM), "-i", str(scene["video"])]
            encode = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "25"]
            if variant == "narrated":
                ffmpeg(*video_args, "-i", str(audio), "-map", "0:v", "-map", "1:a", *encode, "-c:a", "aac", "-b:a", "160k", "-shortest", str(target))
            else:
                ffmpeg(*video_args, *encode, "-an", str(target))
            segments[variant].append(target)
    for variant, files in segments.items():
        listing = WORK / f"concat-{variant}.txt"
        listing.write_text("".join(f"file '{f.as_posix()}'\n" for f in files), encoding="utf-8")
        final = OUT / f"demo-{variant}.mp4"
        ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(final))
        print(f"{final.name}: {duration_of(final) / 60:.2f} minutes, {final.stat().st_size / 1e6:.1f} MB")


def restore_leftover_backup() -> None:
    """Put approval_policy.py back if an earlier run was interrupted during the break demo."""
    if POLICY_BACKUP.exists():
        shutil.copy2(POLICY_BACKUP, POLICY)
        POLICY_BACKUP.unlink()
        print("restored approval_policy.py from a leftover backup")


def main() -> None:
    """Synthesize the voice, record every scene, and assemble the videos."""
    restore_leftover_backup()
    voice = synthesize()
    server, terminal_url = start_terminal_server()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            scenes = record_all(browser, voice, terminal_url)
            browser.close()
    finally:
        server.shutdown()
        restore_leftover_backup()
    assemble(scenes, voice)


if __name__ == "__main__":
    main()
