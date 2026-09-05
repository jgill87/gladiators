"""Optional publishing helper. The app itself remains a single static HTML file."""
from pathlib import Path
import os
import re
import json
source = Path(__file__).with_name('index.html').read_text()
for name in ('SUPABASE_URL', 'SUPABASE_KEY'):
    value = os.environ.get(name)
    if value:
        source = re.sub(r'(const '+name+r'\s*=\s*)"[^"]*"', lambda m: m[1]+json.dumps(value), source)
if 'PASTE_YOUR_' in source:
    raise SystemExit('Provide SUPABASE_URL and SUPABASE_KEY to build the connected app.')
out = Path(__file__).with_name('dist')
out.mkdir(exist_ok=True)
(out / 'index.html').write_text(source)
print('Built connected static app.')
