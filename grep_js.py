import re

files = [r'C:\Users\habib\AppData\Local\Temp\vyce_index.js',
         r'C:\Users\habib\AppData\Local\Temp\vyce_router.js']
pats = [r'captcha\w*Token', r'"captcha"', r'captchaToken', r'turnstile', r'verify.{0,12}halleng',
        r'/user/register', r'powNonce', r'fingerprint']
for f in files:
    try:
        s = open(f, encoding='utf-8', errors='replace').read()
    except Exception as e:
        print(f, 'MISSING', e)
        continue
    name = f.replace(chr(92), '/').split('/')[-1]
    print('=' * 25, name, len(s))
    for p in pats:
        hits = re.findall(r'.{60}' + p + r'.{100}', s)
        if hits:
            print('##', p, '->', len(hits))
            for h in hits[:3]:
                print('   *', h.replace('\n', ' ')[:170])
