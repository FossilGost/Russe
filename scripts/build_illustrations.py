"""Build local vocabulary scenes from CC BY 4.0 Twemoji vector artwork.

Run explicitly to refresh assets; the application never downloads illustrations.
"""
import concurrent.futures
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'static' / 'illustrations'
ICONS = DEST / 'icons'
BASE = 'https://raw.githubusercontent.com/jdecked/twemoji/v16.0.1/'

# Each item corresponds to the stable vocabulary ID, starting at 1.
FIRST = '''🏠|🌉|🌳🌷|🍲|🛏️💭|☂️|🏦|🧃|🐈|🔊|📅|🔥|💧|🪟|👩👶|👨👶|⛲|🥛|👗|📋✅|🍎🍎🍎|🏺|👜|👩|📦|➡️📍|📅⏳|➡️❓|📅❓|💡➡️|🚃|🍌|⏱️➡️|🏭|🧭➡️|🏫|🔤|⬅️🧭|⚛️|🚀🌌|🛁|⚖️|🛒💳|⚖️|➕🟰|🧥|📁|📷|🏙️|✍️📜|💼|👉📦|📍|📍➡️|👉|✋|🌹|👦👦|🛣️|🎭|📅🌱|🚜|🧑🤝🧑|🏅⚽|🚗🚌|🧩|🗺️|🌱|🌍|⛰️|📅➡️|🌅|❓|👖|📖✏️|🛂|💬|📖|↔️|🛏️🪟|💬💬|🏪🥕|🌤️|🛣️|💰|💬✂️|🙋|👉🧑|👨|🧑🧑|👉🧑🧑|👥|🙋📘|🙋👜|🙋🪟|👉📘|👉👜|👉🪟|👨📘|👩📘|👥📘|👥👜|👥🪟|👉👥📘|👉👥👜|👥📚|🚗|📍❓|🎶📋|🎟️|🎤🎸|🎤🎵|🧑🤝🧑|🏪☕|☕|✨🎁|✅⏱️|🌧️|🌬️|🏘️|📅|🌆|🍵|🎵|📱|🇫🇷|💬🌍|🎬|⚽|🏪🍽️|🧑🏠|🧑💼|📖✏️|👂🎵|👁️|❤️|💭⭐|🚶🌳|📱💬|🛠️|🥛|🚶|📅📍|🏠|➕|❓💭|🌟|👍|📅✅|👋|💬❓|👍😊|🧑🛠️❓|👋➡️|🚶🌳💭|❤️☕|🙋☂️|🏘️🌧️|👩👶|🐋|🌟🌟🌟|👧👧|👨|✅'''.split('|')

def assignments():
    result = {i: value for i, value in enumerate(FIRST, 1)}
    extra = {
        165:'🧑',166:'🧑🎁',167:'🪑',168:'📚',169:'🙋📚',170:'👉📚',171:'👥📚',172:'👉👥🪟',173:'👉👥📚',
        202:'👉🙋🏠',203:'👉📷',204:'👨🏠',205:'👩🏙️',206:'👩🏠',207:'✨🧥',208:'👉🏙️',209:'👩🏠',210:'📍🪟',211:'🏦➡️',212:'🙋🛏️',213:'➡️⛲',214:'👩🏠',215:'➡️🌳',216:'🙋🏫',217:'👥🏠',218:'🙋🏠',219:'👨✅❓',220:'👨🎓',221:'👥🏢',222:'👥📍❓',223:'🧑🤝🧑',224:'🙋🎓',
        225:'🙋👦',226:'👉☂️',227:'👨🛂',228:'👩📷',229:'👥☂️',230:'👥🏠🏠',231:'🙋📷',232:'🙋📋',233:'👉⏰❓',234:'👨🚗',235:'👩💡',236:'👥🧩✅',237:'👥❓',238:'👥🏅',239:'🙋📖',
        240:'👉💧',241:'👉🏺',242:'👩➡️',243:'👩',244:'👉👜',245:'👉☂️',246:'👉📷',247:'📜',248:'✍️📜',249:'🧑🤝🧑',250:'👦👦',251:'📖📖',252:'🔁',253:'🏠🏠',254:'📅📅',255:'📜',256:'💡➡️',257:'🏁',258:'📝',
        266:'🚫',267:'🎁🧑',268:'🧑🤝🧑',273:'💬🧑',274:'🚶🏘️',280:'🙋🏠',285:'☕🚫🧊',286:'🎁🧑',287:'🧑🤝🧑',295:'💬🧑',296:'🚶🏘️'}
    result.update(extra)
    for start, person in [(174,'🙋'),(178,'👉'),(182,'👥'),(186,'👉👥'),(190,'👨'),(194,'👩'),(198,'👥')]:
        for offset, obj in enumerate(['🪑','👜','🪟','📚']):
            result[start+offset] = person+obj
    return result

def emoji_parts(value):
    # All scenes use individual emoji; no ZWJ or skin tone sequences.
    parts = []
    for char in value:
        if ord(char) == 0xfe0f:
            continue
        if 0x1f1e6 <= ord(char) <= 0x1f1ff and parts and len(parts[-1]) == 1 and 0x1f1e6 <= ord(parts[-1]) <= 0x1f1ff:
            parts[-1] += char
        else:
            parts.append(char)
    return parts

def code(emoji):
    return '-'.join(f'{ord(char):x}' for char in emoji)

def download(emoji):
    path = ICONS / (code(emoji)+'.svg')
    if not path.exists():
        payload = urllib.request.urlopen(BASE+'assets/svg/'+path.name, timeout=30).read()
        ET.fromstring(payload)
        path.write_bytes(payload)
    return emoji, path

def frame(content):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 160"><rect width="320" height="160" rx="18" fill="#f2f7fc"/><ellipse cx="160" cy="137" rx="125" ry="7" fill="#dce8f2"/>'+content+'</svg>'

# Pedagogical spatial diagrams: dot = object/person, outline = house/table.
SPATIAL = {
    259:('house','inside',False),260:('table','above',False),261:('house','near',False),262:('house','near',True),263:('house','out',True),264:('house','away',True),265:('house','near',True),269:('table','under',False),270:('table','high',False),271:('house','front',False),272:('house','behind',False),
    275:('house','inside',False),276:('house','inside',True),277:('table','above',False),278:('table','above',True),279:('house','near',False),281:('house','near',True),282:('house','out',True),283:('house','away',True),284:('house','near',True),288:('table','out',True),289:('table','under',False),290:('table','under',True),291:('table','high',False),292:('house','front',False),293:('house','behind',False),294:('house','behind',True)}

def spatial(obj, relation, motion):
    shape = '<path d="M110 80 L170 32 L230 80 V137 H110 Z" fill="#c8ddeb" stroke="#51758e" stroke-width="4"/>' if obj=='house' else '<path d="M95 90 H245 M115 90 V140 M225 90 V140" fill="none" stroke="#51758e" stroke-width="10" stroke-linecap="round"/>'
    x,y = {'inside':(170,110),'above':(170,68),'under':(170,120),'high':(170,30),'near':(70,119),'front':(170,137),'behind':(210,56),'out':(277,110),'away':(280,120)}[relation]
    dot = f'<circle cx="{x}" cy="{y}" r="14" fill="#ed8759" stroke="#fff" stroke-width="3"/>'
    if relation=='behind':
        shape = dot+shape
        dot = ''
    arrow = ''
    if motion:
        start = (170,110) if relation in ('out','away') else (30,50)
        arrow = f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10Z" fill="#28614c"/></marker></defs><path d="M{start[0]} {start[1]} L{x} {y}" stroke="#28614c" stroke-width="4" fill="none" marker-end="url(#a)"/>'
    return frame(shape+arrow+dot)

def main():
    ICONS.mkdir(parents=True, exist_ok=True)
    scenes = assignments()
    words = json.loads((ROOT/'data/vocabulary.json').read_text(encoding='utf-8'))['words']
    assert set(scenes) | set(SPATIAL) == {w['id'] for w in words}
    emojis = {emoji for value in scenes.values() for emoji in emoji_parts(value)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        icons = dict(executor.map(download, sorted(emojis)))
    manifest = {}
    for word in words:
        word_id = word['id']
        if word_id in SPATIAL:
            content = spatial(*SPATIAL[word_id])
            caption = 'Schéma : '+word['fr']+' · point orange = personne ou objet'
        else:
            parts = emoji_parts(scenes[word_id])
            size = min(100, 250/len(parts))
            content = ''
            for index, emoji in enumerate(parts):
                element = ET.fromstring(icons[emoji].read_text(encoding='utf-8'))
                element.set('x', str(160-len(parts)*size/2+index*size))
                element.set('y', str(80-size/2))
                element.set('width', str(size))
                element.set('height', str(size))
                content += ET.tostring(element, encoding='unicode')
            content = frame(content)
            caption = 'Repère visuel : '+word['fr']
        (DEST/f'{word_id}.svg').write_text(content, encoding='utf-8')
        manifest[str(word_id)] = {'caption':caption}
    (ROOT/'data/illustrations.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    license_text = urllib.request.urlopen(BASE+'LICENSE-GRAPHICS', timeout=30).read()
    (DEST/'LICENSE-GRAPHICS.txt').write_bytes(license_text)
    (DEST/'CREDITS.md').write_text('Illustrations: Twemoji, Twitter, Inc. and other contributors.\nSource: https://github.com/jdecked/twemoji/tree/v16.0.1/assets/svg\nLicense: CC BY 4.0 https://creativecommons.org/licenses/by/4.0/\nModifications: grouped and resized into vocabulary scenes on a background.\nSpatial diagrams: original Slovo pedagogical illustrations.\n',encoding='utf-8')
    print(f'{len(manifest)} illustrated entries; {len(icons)} local source icons.')

if __name__ == '__main__':
    main()
