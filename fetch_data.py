import json, urllib.request, time

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

def flag(code):
    if not code: return ''
    c = code.strip('/').split('/')[-1].upper()
    if len(c) != 2: return ''
    return chr(ord(c[0])+127397)+chr(ord(c[1])+127397)

def league_icon(lg):
    return {'Legend':'👑','Champion':'💎','Elite':'🔥','Diamond':'💠',
            'Platinum':'🪙','Gold':'🥇','Silver':'🥈','Bronze':'🥉',
            'Stone':'🪨','Wood':'🪵'}.get(lg,'')

def time_ago(ts):
    if not ts: return ''
    d = int(time.time()) - ts
    if d < 3600:   return f"{d//60}m ago"
    if d < 86400:  return f"{d//3600}h ago"
    if d < 604800: return f"{d//86400}d ago"
    return f"{d//604800}w ago"

# ── Load raw members ──
with open('data/members_raw.json') as f:
    raw = json.load(f)

weekly   = raw.get('weekly',   [])
monthly  = raw.get('monthly',  [])
all_time = raw.get('all_time', [])

print(f"weekly={len(weekly)}, monthly={len(monthly)}, all_time={len(all_time)}")

# ── Top active members (weekly + monthly, enriched with stats) ──
seen = set(m['username'] for m in weekly)
pool = (
    [dict(m, tier='weekly')  for m in weekly[:6]] +
    [dict(m, tier='monthly') for m in monthly if m['username'] not in seen][:4]
)[:6]

enriched = []
for m in pool:
    u = m['username']
    try:
        prof  = fetch(f"https://api.chess.com/pub/player/{u}")
        stats = fetch(f"https://api.chess.com/pub/player/{u}/stats")
        peak = max(filter(None, [
            (stats.get('chess_rapid',  {}).get('best', {}) or {}).get('rating'),
            (stats.get('chess_blitz',  {}).get('best', {}) or {}).get('rating'),
            (stats.get('chess_bullet', {}).get('best', {}) or {}).get('rating'),
        ]), default=None)
        current = (
            (stats.get('chess_rapid',  {}).get('last', {}) or {}).get('rating') or
            (stats.get('chess_blitz',  {}).get('last', {}) or {}).get('rating') or
            (stats.get('chess_bullet', {}).get('last', {}) or {}).get('rating')
        )
        wins = draws = losses = 0
        for fmt in ['chess_rapid','chess_blitz','chess_bullet','chess_daily']:
            rec = stats.get(fmt, {}).get('record', {}) or {}
            wins   += rec.get('win',  0)
            draws  += rec.get('draw', 0)
            losses += rec.get('loss', 0)
        enriched.append({
            'username':    u,
            'tier':        m['tier'],
            'avatar':      prof.get('avatar'),
            'title':       prof.get('title'),
            'rating':      current,
            'peak':        peak,
            'name':        prof.get('name'),
            'country':     flag(prof.get('country', '')),
            'league':      prof.get('league', ''),
            'league_icon': league_icon(prof.get('league', '')),
            'last_online': time_ago(prof.get('last_online')),
            'followers':   prof.get('followers', 0),
            'wins': wins, 'draws': draws, 'losses': losses,
        })
        time.sleep(0.35)
    except Exception as e:
        print(f"  failed {u}: {e}")
        enriched.append({'username':u,'tier':m['tier'],'avatar':None,'title':None,
            'rating':None,'peak':None,'name':None,'country':'','league':'',
            'league_icon':'','last_online':'','followers':0,'wins':0,'draws':0,'losses':0})

enriched.sort(key=lambda x: x['peak'] or x['rating'] or 0, reverse=True)

# ── Newest members ──
# all_time list has 'joined' = timestamp when they joined the club
# Sort descending to get most recent joiners
all_sorted = sorted(all_time, key=lambda x: x.get('joined', 0), reverse=True)
newest_pool = all_sorted[:10]  # take top 10, enrich 6

newest = []
for m in newest_pool:
    if len(newest) >= 6:
        break
    u = m['username']
    club_joined = m.get('joined', 0)  # when they joined the club
    try:
        prof = fetch(f"https://api.chess.com/pub/player/{u}")
        newest.append({
            'username':    u,
            'avatar':      prof.get('avatar'),
            'title':       prof.get('title'),
            'joined':      club_joined,          # club join date
            'country':     flag(prof.get('country', '')),
            'league':      prof.get('league', ''),
            'league_icon': league_icon(prof.get('league', '')),
        })
        time.sleep(0.3)
    except Exception as e:
        print(f"  newest failed {u}: {e}")
        newest.append({'username':u,'avatar':None,'title':None,'joined':club_joined,
                       'country':'','league':'','league_icon':''})

# ── Match stats ──
with open('data/matches.json') as f:
    matches = json.load(f)

fin = matches.get('finished', [])
output = {
    'weekly_count':  len(weekly),
    'total_matches': len(matches.get('in_progress',[])) + len(matches.get('registered',[])) + len(fin),
    'match_wins':    sum(1 for m in fin if m.get('result') == 'win'),
    'match_losses':  sum(1 for m in fin if m.get('result') == 'lose'),
    'match_draws':   sum(1 for m in fin if m.get('result') == 'draw'),
    'members':       enriched,
    'newest':        newest,
}

with open('data/members.json', 'w') as f:
    json.dump(output, f)

print(f"Saved: {len(enriched)} active members, {len(newest)} newest")
