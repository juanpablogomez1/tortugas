"""Pruebas del parser con fragmentos reales de Fedegolf (python -m pytest tests/ o python tests/test_parsers.py)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scraper

FX = os.path.join(os.path.dirname(__file__), 'fixtures')


class FakeResp:
    def __init__(self, text): self.text = text
    def raise_for_status(self): pass


def test_history(monkeypatch=None):
    html = open(os.path.join(FX, 'historial.html'), encoding='utf-8').read()
    scraper.S.get = lambda *a, **k: FakeResp(html)
    rounds, idx, liq = scraper.fetch_history('X')
    assert len(rounds) == 3, rounds
    r = rounds[0]
    assert r['rid'] == 'a16Ua000009csGkIAI' and r['fecha'] == '2026-10-18' and r['club'] == 'CC Medellin'
    assert r['cancha'] == 'Llano Grande' and r['marca'] == '6350 Caballeros'
    assert (r['cr'], r['slope'], r['par'], r['gross'], r['hoyos'], r['dif'], r['cuenta']) == (69.9, 126, 72, 99, 18, 24.3, False)
    assert rounds[1]['cuenta'] is True and rounds[2]['hoyos'] == 9 and rounds[2]['gross'] == 39
    assert idx[0] == {'fecha': '2026-10-18', 'indice': 13.7, 'tipo': 'dia'}
    assert idx[1]['tipo'] == 'corte'
    assert liq[0] == {'fecha': '2026-10-18', 'tipo': 'dia', 'n': 8, 'prom8': 13.65, 'publicado': None}
    assert liq[1] == {'fecha': '2026-09-30', 'tipo': 'corte', 'n': 20, 'prom8': 2.525, 'publicado': 2.525}
    print('historial OK')


def test_card():
    html = open(os.path.join(FX, 'tarjeta.html'), encoding='utf-8').read()
    scraper.S.get = lambda *a, **k: FakeResp(html)
    c = scraper.fetch_card('Y')
    assert c['hora'] == '08:11' and c['ajustado'] == 97 and c['hcpCampo'] == 13 and c['tipo'] == 'Aceptable'
    assert c['pars'] == [4,5,4,3,5,4,4,3,4,4,5,3,4,5,4,4,3,4]
    assert c['vent'] == [13,15,5,11,7,1,9,17,3,14,4,6,10,18,8,2,16,12]
    assert c['scores'] == [5,6,6,4,5,4,4,4,5,8,7,6,6,6,7,6,5,5] and sum(c['scores']) == 99
    assert c['adj'] == [5,6,6,4,5,4,4,4,5,6,7,6,6,6,7,6,5,5] and sum(c['adj']) == 97
    print('tarjeta OK')


if __name__ == '__main__':
    test_history(); test_card()
