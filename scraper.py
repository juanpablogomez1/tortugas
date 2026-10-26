"""Consulta Fedegolf para los jugadores de data/players.json y escribe data/fedegolf_latest.json.

Fuentes (todas públicas, sin login):
  1. federacioncolombianadegolf.com  (WordPress) -> admin-ajax.php
     - envio_salesforce: código -> Id de Salesforce, índice vigente, categoría, club
     - get_categories_ranking / get_info_ranking: Ranking Nacional por categoría
     - get_calendar_home: próximos torneos
  2. servicios.federacioncolombianadegolf.com (Salesforce)
     - /apex/HistorialJuegoResultadoPp?user=<Id>: últimas 20 rondas, historial de índices y detalle de cálculo
     - /apex/TarjetaJuegoWebPp?id=<id ronda>: tarjeta hoyo a hoyo
"""
import json, re, sys, time, os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data')
WP = 'https://federacioncolombianadegolf.com'
SF = 'https://servicios.federacioncolombianadegolf.com'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TablaLasTortugas/1.0', 'Accept-Language': 'es-CO,es;q=0.9'}
S = requests.Session(); S.headers.update(HEADERS)
MESES = {'jan':1,'ene':1,'feb':2,'mar':3,'apr':4,'abr':4,'may':5,'jun':6,'jul':7,'aug':8,'ago':8,'sep':9,'sept':9,'oct':10,'nov':11,'dec':12,'dic':12}


def retry(fn, tries=3, wait=3):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa
            if i == tries - 1:
                raise
            time.sleep(wait * (i + 1))


def ajax(**fields):
    r = retry(lambda: S.post(f'{WP}/wp-admin/admin-ajax.php', data=fields, timeout=60))
    r.raise_for_status()
    return r.json()


def pdate(s):  # dd/mm/yyyy -> ISO
    d, m, y = s.strip().split('/')
    if len(y) == 2: y = '20' + y
    return f'{y}-{m.zfill(2)}-{d.zfill(2)}'


def txt(el):
    return re.sub(r'\s+', ' ', el.get_text(' ')).strip() if el is not None else ''


# ---------- 1. jugador ----------
def resolve_player(codigo):
    j = ajax(action='envio_salesforce', tipo_busqueda='cod', termino_busqueda=str(codigo))
    res = (j.get('data') or {}).get('BusquedaResult') or []
    per = (res[0] or {}).get('Persona') if res else None
    if not per:
        raise RuntimeError(f'sin resultado para código {codigo}')
    # Solo lo necesario; la respuesta trae datos personales que NO se guardan.
    return {'id': per['Id'], 'nombre': f"{per.get('FirstName','')} {per.get('LastName','')}".strip(),
            'indice': per.get('Indice__c'), 'cat': per.get('Categoria__c'), 'club': per.get('FCG_Club_Federado__c'),
            'vigencia': per.get('Fecha_de_vigencia__c'), 'estado': per.get('Estado__c')}


# ---------- 2. historial ----------
def fetch_history(sf_id):
    r = retry(lambda: S.get(f'{SF}/apex/HistorialJuegoResultadoPp', params={'user': sf_id}, timeout=90))
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    home = soup.select_one('#pills-home')
    rounds = []
    for tr in home.select('table')[0].select('tbody tr'):
        td = tr.find_all('td')
        if len(td) < 8:
            continue
        a = td[0].find('a')
        m = re.search(r'id=(\w+)', a['href']) if a else None
        fecha = txt(td[1])
        if not fecha:
            continue
        score = txt(td[6])
        gross, holes = (score.split('/') + [None])[:2] if score else (None, None)
        pat = txt(td[5]).split('/')
        rounds.append({
            'rid': m.group(1) if m else None, 'fecha': pdate(fecha), 'club': txt(td[2]), 'cancha': txt(td[3]), 'marca': txt(td[4]),
            'cr': float(pat[0]), 'slope': int(pat[1]), 'par': int(pat[2]),
            'gross': int(gross) if gross else None, 'hoyos': int(holes) if holes else None,
            'dif': float(txt(td[7])), 'cuenta': txt(td[8]) == '*' if len(td) > 8 else False,
        })
    idx, liq = [], []
    prof = soup.select_one('#pills-profile')
    for tr in prof.select('tbody tr'):
        td = tr.find_all('td')
        if len(td) < 4 or not txt(td[1]):
            continue
        fecha = pdate(txt(td[1])); tipo = 'corte' if 'corte' in txt(td[3]).lower() else 'dia'
        idx.append({'fecha': fecha, 'indice': float(txt(td[2])), 'tipo': tipo})
        a = tr.find('a', attrs={'data-target': True})
        n = prom = pub = None
        if a:
            modal = soup.select_one(a['data-target'])
            t = txt(modal) if modal else ''
            mm = re.search(r'Cantidad de Diferenciales: (\d+)', t); n = int(mm.group(1)) if mm else None
            mm = re.search(r'Menores: ([-\d.]+)', t); prom = round(float(mm.group(1)), 4) if mm else None
            mm = re.search(r'Softcap: ([-\d.]+)', t); pub = round(float(mm.group(1)), 4) if mm else None
        liq.append({'fecha': fecha, 'tipo': tipo, 'n': n, 'prom8': prom, 'publicado': pub})
    return rounds, idx, liq


# ---------- 3. tarjeta ----------
def fetch_card(rid):
    r = retry(lambda: S.get(f'{SF}/apex/TarjetaJuegoWebPp', params={'id': rid}, timeout=90))
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    body = txt(soup.body)
    g = lambda rx: (re.search(rx, body) or [None, None])[1]
    rows = {}
    for tr in soup.select('table tr'):
        cells = [txt(c) for c in tr.find_all(['th', 'td'])]
        if len(cells) >= 20 and cells[0].upper() in ('PAR', 'VENTAJA', 'SCORE', 'AJUSTADO'):
            vals = [c for i, c in enumerate(cells[1:]) if i not in (9, 19) and i < 20]  # quita OUT/IN/TOTAL
            rows[cells[0].upper()] = [int(v) if v.isdigit() else None for v in vals]
    fecha_hora = g(r'Fecha:\s*(.+?)\s+Club:') or ''
    hora = (re.search(r'(\d{2}:\d{2}):\d{2}', fecha_hora) or [None, None])[1]
    ajust = g(r'Score Ajustado:\s*(\d+)'); hcp = g(r'H[áa]ndicap:\s*(-?\d+)'); tipo = g(r'Tipo Score:\s*([A-Za-z ]+?)\s+Indice')
    return {'hora': hora, 'ajustado': int(ajust) if ajust else None, 'hcpCampo': int(hcp) if hcp else None,
            'tipo': (tipo or 'Aceptable').strip(), 'pars': rows.get('PAR'), 'vent': rows.get('VENTAJA'),
            'scores': rows.get('SCORE'), 'adj': rows.get('AJUSTADO')}


# ---------- 4. ranking y torneos ----------
def fetch_ranking(ids_by_sf):
    out = {'publicado': None, 'categorias': []}
    try:
        cats = ajax(action='get_categories_ranking')['data']['categories']['Masculino']
    except Exception as e:  # noqa
        print('ranking: no disponible', e); return out
    for c in cats:
        if c['Name'] not in ('Aficionados Caballeros', 'Pre Mid-Am Caballeros', 'Mid Amateur Caballeros', 'Juveniles Caballeros', 'Senior Caballeros'):
            continue
        try:
            L = ajax(IdCategoria=c['Id'], action='get_info_ranking')['data'].get('RetornaCategoriasResult') or []
        except Exception as e:  # noqa
            print('ranking', c['Name'], e); continue
        ours = []
        for x in L:
            code = ids_by_sf.get(x.get('Federado_Id'))
            if code:
                ours.append({'codigo': code, 'pos': x['Posicion'], 'pts': round(x['Puntos'], 2), 'prom': round(x['Puntos_Promedio'], 2),
                             'mov': x.get('Movimiento'), 'movN': x.get('Movimiento_Cantidad_De_Posiciones'), 'eventos': x.get('Cantidad_de_Eventos')})
            if L and not out['publicado']:
                out['publicado'] = (x.get('Fecha_de_Publicacion') or '')[:10]
        out['categorias'].append({'nombre': c['Name'], 'total': len(L), 'jugadores': ours})
    return out


def fetch_torneos():
    try:
        j = ajax(month='', divisional='', wordSearch='', action='get_calendar_home')
        L = j if isinstance(j, list) else (j.get('data') or [])
        return [{'inicio': t['StartDate'], 'fin': t['FinishDate'], 'nombre': t['Name'], 'club': t['ClubName'], 'ciudad': t['ClubCity'], 'division': (t.get('Division') or '').title()} for t in L]
    except Exception as e:  # noqa
        print('torneos: no disponible', e); return []


# ---------- main ----------
def scrape_player(p):
    code = p['codigo']
    info = resolve_player(code)
    rounds, idx, liq = fetch_history(info['id'])
    for r in rounds:
        card = fetch_card(r['rid']) if r['rid'] else {}
        r.update(card)
        if r.get('pars') and r.get('scores') and r.get('gross') and r['hoyos'] == 18:
            if sum(x or 0 for x in r['scores']) != r['gross']:
                print(f"  aviso {code} {r['fecha']}: suma de hoyos {sum(x or 0 for x in r['scores'])} != gross {r['gross']}")
    print(f"ok {code} {info['nombre']}: {len(rounds)} rondas, índice {info['indice']}")
    return {**p, **{k: v for k, v in info.items() if k != 'nombre'}, 'nombreFedegolf': info['nombre'], 'rondas': rounds, 'historialIndice': idx, 'liquidaciones': liq}


def main():
    players = json.load(open(os.path.join(DATA, 'players.json'), encoding='utf-8'))
    out, errors = [], []
    with ThreadPoolExecutor(max_workers=3) as ex:
        for p, res in zip(players, ex.map(lambda p: _safe(scrape_player, p), players)):
            if isinstance(res, Exception):
                errors.append((p['codigo'], str(res))); print(f"ERROR {p['codigo']}: {res}")
            else:
                out.append(res)
    ids_by_sf = {p['id']: p['codigo'] for p in out}
    data = {'actualizado': date.today().isoformat(), 'jugadores': out, 'errores': errors,
            'ranking': fetch_ranking(ids_by_sf), 'torneos': fetch_torneos()}
    json.dump(data, open(os.path.join(DATA, 'fedegolf_latest.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"jugadores ok: {len(out)} / {len(players)}; errores: {len(errors)}")
    if len(out) < max(1, len(players) // 2):
        sys.exit('Demasiados errores: no se actualiza el tablero')


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception as e:  # noqa
        return e


if __name__ == '__main__':
    main()
