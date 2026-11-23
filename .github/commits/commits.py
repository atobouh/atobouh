"""Draws the commits glyph grid and the live status bar (light + dark SVGs).
Runs daily in GitHub Actions. Needs GITHUB_TOKEN in the environment. No third-party packages."""
import json, os, re, urllib.request, datetime

USER = os.environ.get('GH_USER', 'atobouh')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('OUT_DIR', os.path.join(HERE, '..', '..', 'assets'))
G = json.load(open(os.path.join(HERE, 'glyphs.json'), encoding='utf-8'))

Q = '''query($u:String!){user(login:$u){repositories(privacy:PUBLIC,ownerAffiliations:OWNER){totalCount}
latest:repositories(first:8,privacy:PUBLIC,ownerAffiliations:OWNER,orderBy:{field:PUSHED_AT,direction:DESC}){nodes{name isFork
defaultBranchRef{target{... on Commit{messageHeadline committedDate}}}}}
contributionsCollection{totalCommitContributions totalPullRequestContributions
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}'''

def fetch():
    src = os.environ.get('CONTRIB_JSON')
    if src:
        return json.load(open(src))['data']['user']
    req = urllib.request.Request('https://api.github.com/graphql', data=json.dumps({'query': Q, 'variables': {'u': USER}}).encode(),
                                 headers={'Authorization': 'bearer ' + os.environ['GITHUB_TOKEN'], 'User-Agent': 'profile-readme'})
    return json.load(urllib.request.urlopen(req))['data']['user']

def r(v): return f'{v:.1f}'
def text(s, size, x, y, track=0.0, anchor='start'):
    w = sum(G.get(c, G[' '])[0] * size + track * size for c in s) - track * size
    if anchor == 'middle': x -= w / 2
    if anchor == 'end': x -= w
    d = []
    for c in s:
        adv, p = G.get(c, G[' '])
        if p:
            d.append(f'<path transform="translate({r(x)} {r(y)}) scale({size})" d="{p}"/>')
        x += adv * size + track * size
    return ''.join(d), w

TH = {
  'dark':  dict(bg='#0f0f12', ink='#ececef', mid='#8b8d98', dim='#34343c', gl='#6f86ff', hi='#c8f560', line='#2a2a31'),
  'light': dict(bg='#f3f3f1', ink='#121214', mid='#6b6d78', dim='#c9c9c3', gl='#2f4bd8', hi='#5f8a00', line='#d9d9d4'),
}
LV = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
CH = ['·', ':', '+', '#', '@']

ICON = {  # 24px line icons
  'commit': 'M12 8.6a3.4 3.4 0 1 0 0 6.8a3.4 3.4 0 1 0 0-6.8z M2 12h6.6 M15.4 12H22',
  'pr': 'M6 3.5a2.2 2.2 0 1 0 0 4.4a2.2 2.2 0 1 0 0-4.4z M6 16.1a2.2 2.2 0 1 0 0 4.4a2.2 2.2 0 1 0 0-4.4z M18 16.1a2.2 2.2 0 1 0 0 4.4a2.2 2.2 0 1 0 0-4.4z M6 7.9v8.2 M18 16.1V9a3 3 0 0 0-3-3h-4 M13 3.6 10.6 6 13 8.4',
  'repo': 'M5 3.5h12.5a1.5 1.5 0 0 1 1.5 1.5v14.5H6.5A1.5 1.5 0 0 1 5 18z M5 16.5a1.5 1.5 0 0 1 1.5-1.5H19 M9 3.5v6l2-1.4 2 1.4v-6',
  'pulse': 'M2 12.5h4.2l2.4-6 4.6 11.5 2.6-6.2 1.2.7H22',
}

def build(u, name):
    c = TH[name]
    cc = u['contributionsCollection']; cal = cc['contributionCalendar']; weeks = cal['weeks']
    W, H = 1280, 336; cell = 20.2; gx = 128; gy = 92; size = 15
    out = ['<style>.wk{animation:in .4s ease-out both}@keyframes in{from{opacity:0}to{opacity:1}}@media (prefers-reduced-motion:reduce){.wk{animation:none}}</style>', f'<rect width="{W}" height="{H}" rx="18" fill="{c["bg"]}"/>']
    # month labels
    seen = None; ml = []
    for i, wk in enumerate(weeks):
        d0 = datetime.date.fromisoformat(wk['contributionDays'][0]['date'])
        if d0.month != seen and d0.day <= 7 and i < len(weeks) - 1:
            seen = d0.month
            p, _ = text(d0.strftime('%b').upper(), 11, gx + i * cell, gy - 22, 0.12); ml.append(p)
    out.append(f'<g fill="{c["mid"]}">{"".join(ml)}</g>')
    for j, dn in ((1, 'MON'), (3, 'WED'), (5, 'FRI')):
        p, _ = text(dn, 11, gx - 22, gy + j * cell + 10, 0.12, 'end'); out.append(f'<g fill="{c["mid"]}">{p}</g>')
    # glyph cells, each week decodes in from left to right
    cols = {0: c['dim'], 1: c['mid'], 2: c['gl'], 3: c['gl'], 4: c['hi']}
    last = None
    for i, wk in enumerate(weeks):
        cells = []
        for day in wk['contributionDays']:
            wd = datetime.date.fromisoformat(day['date']).isoweekday() % 7
            lv = LV.get(day['contributionLevel'], 0)
            x = gx + i * cell + cell / 2; y = gy + wd * cell + 11
            p, _ = text(CH[lv], size, x, y, 0, 'middle')
            op = ' fill-opacity=".7"' if lv == 2 else ''
            cells.append(f'<g fill="{cols[lv]}"{op}>{p}</g>')
            last = (x, y)
        b = f'{0.018 * i:.3f}s'
        out.append(f'<g class="wk" style="animation-delay:{b}">{"".join(cells)}</g>')
    # today: lime caret blinking
    if last:
        out.append(f'<rect x="{r(last[0]-6)}" y="{r(last[1]+4)}" width="12" height="2" fill="{c["hi"]}"><animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/></rect>')
    # stats row: icon + number + small label
    stats = [('pulse', cal['totalContributions'], 'CONTRIBUTIONS'), ('commit', cc['totalCommitContributions'], 'COMMITS'),
             ('pr', cc['totalPullRequestContributions'], 'PULL REQUESTS'), ('repo', u['repositories']['totalCount'], 'REPOS')]
    sy = 290; x = gx
    out.append(f'<line x1="{gx}" x2="{r(gx + 53 * cell)}" y1="252" y2="252" stroke="{c["line"]}"/>')
    for ic, n, lab in stats:
        out.append(f'<path transform="translate({r(x)} {sy - 17}) scale(1.05)" d="{ICON[ic]}" fill="none" stroke="{c["ink"]}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>')
        p, w = text(f'{n:,}', 22, x + 36, sy + 2, -0.02); out.append(f'<g fill="{c["ink"]}">{p}</g>')
        p, w2 = text(lab, 10.5, x + 36 + w + 10, sy + 1, 0.14); out.append(f'<g fill="{c["mid"]}">{p}</g>')
        x += 36 + w + 10 + w2 + 46
    # legend
    lx = gx + 53 * cell; p, w = text('MORE', 10.5, lx, sy + 1, 0.14, 'end'); out.append(f'<g fill="{c["mid"]}">{p}</g>')
    lx -= w + 12
    for lv in (4, 3, 2, 1, 0):
        p, _ = text(CH[lv], size, lx - 7, sy + 3, 0, 'middle'); out.append(f'<g fill="{cols[lv]}">{p}</g>'); lx -= 17
    p, _ = text('LESS', 10.5, lx - 4, sy + 1, 0.14, 'end'); out.append(f'<g fill="{c["mid"]}">{p}</g>')
    label = f'{cal["totalContributions"]} contributions in the last 12 months'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{label}"><title>{label}</title>{"".join(out)}</svg>'

def ago(iso, now):
    s = (now - datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))).total_seconds()
    if s < 3600: return f'{max(1, int(s // 60))}m ago'
    if s < 86400: return f'{int(s // 3600)}h ago'
    d = int(s // 86400); return 'yesterday' if d == 1 else f'{d} days ago'

def status(u, name, now=None):
    c = TH[name]; now = now or datetime.datetime.now(datetime.timezone.utc)
    W, H = 1280, 96; y = 55
    lt = None
    for n in u.get('latest', {}).get('nodes', []):
        t = (n.get('defaultBranchRef') or {}).get('target') or {}
        if n['name'].lower() != USER.lower() and not n.get('isFork') and t.get('committedDate'):
            if not lt or t['committedDate'] > lt[2]: lt = (n['name'], t['messageHeadline'], t['committedDate'])
    out = [f'<rect width="{W}" height="{H}" rx="18" fill="{c["bg"]}"/>',
           '<style>.pulse{animation:p 2.2s ease-out infinite;transform-origin:center;transform-box:fill-box}@keyframes p{0%{opacity:.55;transform:scale(1)}80%,100%{opacity:0;transform:scale(3.2)}}@media (prefers-reduced-motion:reduce){.pulse{animation:none;opacity:0}}</style>',
           f'<circle class="pulse" cx="48" cy="{y-5}" r="5" fill="{c["hi"]}"/><circle cx="48" cy="{y-5}" r="5" fill="{c["hi"]}"/>']
    x = 66
    def put(s, size, col, track=0.1, gap=0):
        nonlocal x
        p, w = text(s, size, x, y, track); out.append(f'<g fill="{col}">{p}</g>'); x += w + gap
    put('ONLINE', 12.5, c['ink'], 0.16, 30)
    out.append(f'<line x1="{r(x-15)}" x2="{r(x-15)}" y1="{y-18}" y2="{y+6}" stroke="{c["line"]}"/>')
    put('$ git log -1', 13.5, c['mid'], 0, 22)
    if lt:
        repo, msg, when = lt
        put(repo, 13.5, c['ink'], 0, 16)
        _, rw = text('CAMEROON  ·  WAT, UTC+1', 12.5, 0, 0, 0.14); _, aw = text(ago(when, now), 13.5, 0, 0)
        room = int((W - 44 - rw - 40 - x - aw - 16) / (G['a'][0] * 13.5)) - 2
        msg = msg if len(msg) <= room else msg[:max(8, room - 3)].rstrip() + '...'
        put('"' + msg + '"', 13.5, c['gl'], 0, 16)
        put(ago(when, now), 13.5, c['mid'], 0, 0)
    p, w = text('CAMEROON  ·  WAT, UTC+1', 12.5, W - 44, y, 0.14, 'end'); out.append(f'<g fill="{c["mid"]}">{p}</g>')
    lab = f'Online. Latest commit: {lt[0]}, {lt[1]}' if lt else 'Online'
    lab = lab.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{lab}"><title>{lab}</title>{"".join(out)}</svg>'

if __name__ == '__main__':
    u = fetch(); os.makedirs(OUT, exist_ok=True)
    for n in TH:
        open(os.path.join(OUT, f'commits-{n}.svg'), 'w', encoding='utf-8').write(build(u, n))
        open(os.path.join(OUT, f'status-{n}.svg'), 'w', encoding='utf-8').write(status(u, n))
    print('commits ok', u['contributionsCollection']['contributionCalendar']['totalContributions'])
