"""Fusiona data/fedegolf_latest.json con el archivo acumulado data/historial.json y produce data/tortugas.json.

Fedegolf solo expone las últimas 20 rondas por jugador; el historial guarda todas las que se hayan visto alguna vez.
Las rondas que ya no están en Fedegolf quedan con vigente=False (y cuenta=False).
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data')
LATEST = os.path.join(DATA, 'fedegolf_latest.json')
HIST = os.path.join(DATA, 'historial.json')

rkey = lambda r: f"{r['fecha']}|{r.get('hora')}|{r['cancha']}|{r['marca']}|{r.get('gross')}|{r['dif']}"
ikey = lambda e: f"{e['fecha']}|{e['tipo']}|{e['indice']}"
lkey = lambda l: f"{l['fecha']}|{l['tipo']}|{l.get('prom8')}"


def main():
    players = json.load(open(os.path.join(DATA, 'players.json'), encoding='utf-8'))
    latest = json.load(open(LATEST, encoding='utf-8')) if os.path.exists(LATEST) else {'jugadores': [], 'actualizado': None}
    hist = json.load(open(HIST, encoding='utf-8')) if os.path.exists(HIST) else {}
    fresh = {p['codigo']: p for p in latest.get('jugadores', [])}
    out = []
    for base in players:
        code = base['codigo']
        hp = hist.setdefault(str(code), {'rondas': [], 'indices': [], 'liquidaciones': []})
        f = fresh.get(code)
        if f:
            seen = {rkey(x): x for x in hp['rondas']}
            cur = set()
            for r in f['rondas']:
                r = dict(r); r['vigente'] = True
                k = rkey(r); cur.add(k)
                old = seen.get(k) or {}
                seen[k] = {**old, **r}
            for k, x in seen.items():
                if k not in cur:
                    x['vigente'] = False; x['cuenta'] = False
            hp['rondas'] = sorted(seen.values(), key=lambda x: (x['fecha'], x.get('hora') or ''), reverse=True)
            iseen = {ikey(e): e for e in hp['indices']}
            for e in f['historialIndice']: iseen[ikey(e)] = e
            hp['indices'] = sorted(iseen.values(), key=lambda e: e['fecha'], reverse=True)
            lseen = {lkey(l): l for l in hp['liquidaciones']}
            for l in f['liquidaciones']: lseen[lkey(l)] = l
            hp['liquidaciones'] = sorted(lseen.values(), key=lambda l: l['fecha'], reverse=True)
            for k in ('id', 'indice', 'cat', 'club', 'vigencia', 'nombreFedegolf'):
                if f.get(k) is not None: hp[k] = f[k]
            hp['ultimaConsulta'] = latest.get('actualizado')
        else:
            print(f"sin datos nuevos para {code}; se usa el archivo ({hp.get('ultimaConsulta')})")
        rec = {**base}
        for k in ('id', 'indice', 'cat'):
            if hp.get(k) is not None: rec[k] = hp[k]
        rec.update({'rondas': hp['rondas'], 'historialIndice': hp['indices'], 'liquidaciones': hp['liquidaciones'], 'ultimaConsulta': hp.get('ultimaConsulta')})
        out.append(rec)
    ranking = latest.get('ranking') or (json.load(open(os.path.join(DATA, 'ranking.json'), encoding='utf-8')) if os.path.exists(os.path.join(DATA, 'ranking.json')) else {'publicado': None, 'categorias': []})
    if not ranking.get('categorias') and os.path.exists(os.path.join(DATA, 'ranking.json')):
        ranking = json.load(open(os.path.join(DATA, 'ranking.json'), encoding='utf-8'))
    torneos = latest.get('torneos') or (json.load(open(os.path.join(DATA, 'torneos.json'), encoding='utf-8')) if os.path.exists(os.path.join(DATA, 'torneos.json')) else [])
    data = {'actualizado': latest.get('actualizado') or max((p.get('ultimaConsulta') or '' for p in out), default=None),
            'fuente': 'Federación Colombiana de Golf (consulta de hándicap / historial de juego)',
            'jugadores': out, 'ranking': ranking, 'torneos': torneos, 'errores': latest.get('errores', [])}
    json.dump(data, open(os.path.join(DATA, 'tortugas.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(hist, open(HIST, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(ranking, open(os.path.join(DATA, 'ranking.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(torneos, open(os.path.join(DATA, 'torneos.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('jugadores', len(out), '| rondas en archivo', sum(len(p['rondas']) for p in out), '| actualizado', data['actualizado'])


if __name__ == '__main__':
    main()
