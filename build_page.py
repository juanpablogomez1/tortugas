"""Genera docs/index.html (página completa) a partir de template.html y data/tortugas.json."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(H, 'data', 'tortugas.json'), encoding='utf-8'))
js = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
tpl = open(os.path.join(H, 'template.html'), encoding='utf-8').read()
MESES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
y, m, d = (data['actualizado'] or '2026-01-01').split('-')
body = tpl.replace('__DATA__', js).replace('__UPD__', f"{int(d)} {MESES[int(m)-1]} {y}")
head = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<meta name="color-scheme" content="light dark">\n')
i = body.index('<style>'); j = body.index('</style>') + len('</style>')
page = head + body[:j] + '\n</head>\n<body>\n' + body[j:] + '\n</body>\n</html>\n'
os.makedirs(os.path.join(H, 'docs'), exist_ok=True)
open(os.path.join(H, 'docs', 'index.html'), 'w', encoding='utf-8').write(page)
open(os.path.join(H, 'docs', '.nojekyll'), 'w').close()
print('docs/index.html', len(page), 'bytes')
