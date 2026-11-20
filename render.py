#!/usr/bin/env python3
"""Set the Friday edition from a fixed brief, then rasterize it with Pillow."""

from argparse import ArgumentParser
from collections import Counter
from functools import lru_cache
from math import atan2, cos, sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PAPER, INK, RED, NAVY, TEAL = '#f7f4ec', '#101828', '#b42318', '#1d3557', '#0e7490'
GRAY, RULE, GHOST, WHITE = '#474d56', '#929187', '#dfd9cd', '#fffaf0'
SIZE, SCALE = 1024, 3
LEFT, RIGHT = 24, 1000
NOTO_DIR = Path('/usr/share/fonts/truetype/noto')
DEJAVU_DIR = Path('/usr/share/fonts/truetype/dejavu')
FONTS = {
    'black': ('SerifDisplay-Black', 'Serif-Bold'),
    'head': ('SerifDisplay-Bold', 'Serif-Bold'),
    'sans': ('Sans-Condensed', 'Sans'),
    'bold': ('Sans-CondensedBold', 'Sans-Bold'),
}
REGIONS = ('MID EAST', 'ASIA', 'EUROPE', 'AMERICAS', 'WORLD', 'AFRICA')
FIELDS = ('War & security', 'Politics & diplomacy', 'Economy & markets',
          'Disasters & weather', 'Space & science', 'Society & culture',
          'Climate & energy', 'Sport')
WAR, POLITICS, MARKETS, WEATHER, SPACE, CULTURE, CLIMATE, SPORT = FIELDS
MID, ASIA, EUROPE, AMERICAS, WORLD, AFRICA = REGIONS
STORIES = (
    (MID, WAR, 'Trump puts Iran decision off to 2027',
     '“No rush,” the president says — he will “see what happens” after 1 January, pushing any call on war with Iran into next year. The deferral follows Thursday\'s Shenzhen summit, where Iran topped the agenda with Xi and Putin.'),
    (ASIA, WEATHER, '300,000 flee as Cyclone Akvan bears down on Odisha',
     'Severe Cyclonic Storm Akvan makes landfall Friday near Gopalpur, between Narsapur and Puri, with gusts to 110 kmph.'),
    (MID, WAR, 'Houthi strikes hit Riyadh',
     'Four Saudi targets hit; a tanker burns after striking a mine near Hormuz.'),
    (WORLD, SPACE, 'Voyager 1 passes one light-day',
     'First human-made object that far from Earth, 49 years on.'),
    (EUROPE, WAR, 'Kyiv hit by four ballistic missiles',
     'Overnight strikes; a projectile lands by the Dutch embassy.'),
    (AMERICAS, MARKETS, "Anthropic's record $107bn IPO settles",
     'ANT closed its first day +17% at $97.17; the first listed AI lab.'),
    (WORLD, SPACE, 'Hayabusa2 gives up its asteroid landing',
     'Engine trouble ends the landing plan.'),
    (AMERICAS, CULTURE, 'GTA 6 outsells The Odyssey',
     "Sales pass the film's $1.80bn global run."),
    (EUROPE, WAR, 'Drones shut Genoa airport',
     'Unidentified drones halt all flights for four hours.'),
    (ASIA, MARKETS, "South Korea's exports top $1tn",
     'A first for the country, in a single year.'),
    (EUROPE, WAR, 'Europe ready for talks with Russia on ending the Ukraine war, leaders say.'),
    (MID, WAR, 'Israeli airstrike hits a Hezbollah missile facility in eastern Lebanon.'),
    (MID, WAR, "Israeli military completes a ground operation beyond Gaza's Yellow Line."),
    (EUROPE, POLITICS, 'US envoy: Russia is not ruling out NATO-like security guarantees for Ukraine.'),
    (EUROPE, WAR, 'Projectile lands near the Dutch embassy in Kyiv, minor damage.'),
    (ASIA, MARKETS, 'Taiwan unveils five measures to steady stocks; short-selling limits take effect today.'),
    (ASIA, POLITICS, "Japan's Sanae Takaichi declines to answer a 'Taiwan contingency' question at APEC."),
    (ASIA, POLITICS, "A day after the Shenzhen summit, Trump and Xi Jinping's accounts of their talks differ."),
    (WORLD, CLIMATE, 'Reference to fossil fuels dropped from the latest COP31 draft agreement.'),
    (WORLD, CLIMATE, 'IEA: data-centre power use could double by 2030, straining grids.'),
    (AFRICA, WEATHER, "Migrant boat sinks off Senegal's coast; dozens missing."),
    (EUROPE, WEATHER, 'One dead, 15 injured in a fire at an 18-storey apartment building in France.'),
    (AMERICAS, CULTURE, 'Fiona the hippo dies after swallowing a hat at Cincinnati Zoo.'),
    (WORLD, CULTURE, "Study: Islam to become the world's largest religion by 2035."),
    (AMERICAS, MARKETS, 'Oil flat as Hormuz tanker disruptions offset oversupply worries.'),
    (ASIA, SPORT, "India vs New Zealand, first Test: Henry Nicholls' century, NZ 243 for five."),
    (ASIA, SPORT, 'India defeat Malaysia in the Hong Kong Open badminton.'),
    (ASIA, SPORT, "Women's Asian Hockey Champions Trophy 2026 begins."),
    (ASIA, MARKETS, 'Sensex gains 1.21% and Nifty 50 rises 1.14% as Indian stocks rally.'),
    (AMERICAS, POLITICS, 'Trump warns APEC nations strict AI regulation would stifle development.'),
    (ASIA, POLITICS, "Taiwan's Chen Zhuyin released on NT$500,000 bail over alleged foreign funding."),
    (ASIA, CULTURE, "Taiwan approves Civil Code change, raising the spouse's share to two-thirds."),
    (ASIA, POLITICS, 'India announces new PUC certificate renewal rules.'),
    (EUROPE, WAR, "Putin vows a 'far more painful' response to Ukraine's Crimean Bridge strikes."),
    (ASIA, POLITICS, "A day after the Shenzhen summit, the leaders' 'peace declaration' draws mixed readings."),
)
NUMBERS = (
    ('300,000', 'evacuated ahead of Cyclone Akvan'),
    ('110 kmph', "Akvan's gusts at landfall"),
    ('$107.3bn', "Anthropic's record IPO + placement"),
    ('+17%', "ANT's first-day close, $97.17"),
    ('1 light-day', 'Voyager 1 from Earth'),
    ('$1tn', "South Korea's exports, a first"),
)
DATE_CHECK = (
    "Left out on purpose because they broke before today: the ICJ ruling that Myanmar committed genocide against the Rohingya (Thursday 19 Nov); the Trump–Xi–Putin trilateral summit in Shenzhen (Thursday 19 Nov) — today's story is the aftermath; Anthropic's first trade at $111.50 (Thursday 19 Nov) — today's story is the settlement; South Korea's court overturning Han Duck-soo's conviction (Thursday 19 Nov)."
)
FOOTER = ('Drawn entirely by program · Set in Noto Serif Display & Noto Sans Condensed · Every story happened or was first reported Friday 20 November 2026. '
          'Sources: AP, Reuters, AFP, Bloomberg, NYT, BBC, FT, The Hindu, MarketWatch, The Guardian. Original drawings.')


@lru_cache(maxsize=None)
def font(style, size):
    noto, deja = FONTS[style]
    preferred = NOTO_DIR / f'Noto{noto}.ttf'
    fallback = DEJAVU_DIR / f'DejaVu{deja}.ttf'
    return ImageFont.truetype(str(preferred if preferred.is_file() else fallback), round(size * SCALE))


def pixels(values):
    return tuple(round(value * SCALE) for value in values)


class Page:
    def __init__(self):
        self.image = Image.new('RGB', (SIZE * SCALE, SIZE * SCALE), PAPER)
        self.draw = ImageDraw.Draw(self.image)

    def rect(self, box, color, outline=None):
        self.draw.rectangle(pixels(box), fill=color, outline=outline, width=SCALE)

    def line(self, points, color=RULE, width=0.7):
        self.draw.line([pixels(point) for point in points], fill=color, width=max(1, round(width * SCALE)), joint='curve')

    def poly(self, points, color):
        self.draw.polygon([pixels(point) for point in points], fill=color)

    def oval(self, box, fill, outline=None, width=1):
        self.draw.ellipse(pixels(box), fill=fill, outline=outline, width=round(width * SCALE))

    def dot(self, x, y, radius, color):
        self.oval((x - radius, y - radius, x + radius, y + radius), color)

    @staticmethod
    def measure(text, size, style):
        return font(style, size).getlength(text) / SCALE

    def text(self, x, y, text, size, style='sans', color=INK, align='left', fit=None):
        face = font(style, size)
        width = face.getlength(text) / SCALE
        shown = min(width, fit) if fit is not None else width
        if align == 'center':
            x -= shown / 2
        elif align == 'right':
            x -= shown
        if shown >= width:
            self.draw.text(pixels((x, y)), text, font=face, fill=color, anchor='lt')
        else:
            _, top, right, bottom = face.getbbox(text, anchor='lt')
            pad = 2 * SCALE
            mask = Image.new('L', (max(round(width * SCALE), right) + pad, bottom - top + pad))
            ImageDraw.Draw(mask).text((0, 0), text, font=face, fill=255, anchor='lt')
            mask = mask.resize((round(shown * SCALE), mask.height), Image.Resampling.LANCZOS)
            self.image.paste(color, pixels((x, y)), mask)

    def wrap(self, text, width, size, style):
        lines, current = [], ''
        for word in text.split():
            candidate = f'{current} {word}' if current else word
            if current and self.measure(candidate, size, style) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        return lines + [current]

    def block(self, x, y, lines, size, step, style='sans', color=INK):
        for index, line in enumerate(lines):
            self.text(x, y + index * step, line, size, style, color)

    def rule(self, y, color=RULE, width=0.7):
        self.line(((LEFT, y), (RIGHT, y)), color, width)


def banner(page):
    regions = Counter(story[0] for story in STORIES)
    fields = Counter(story[1] for story in STORIES)
    assert [regions[name] for name in REGIONS] == [4, 13, 7, 5, 5, 1]
    assert [fields[name] for name in FIELDS] == [9, 7, 5, 3, 2, 4, 2, 3]
    page.text(LEFT, 23, 'LATE EDITION · ALL THE NEWS OF ONE DAY ON ONE PAGE', 13, 'bold', NAVY)
    page.text(RIGHT, 23, 'No. 2026-324', 13, 'bold', NAVY, 'right')
    page.rule(39)
    page.text(512, 47, 'THE WORLD IN ONE DAY', 71, 'black', align='center', fit=964)
    page.rule(115, INK, 1.3)
    page.rect((LEFT, 120, RIGHT, 151), RED)
    page.text(512, 126, f'FRIDAY, 20 NOVEMBER 2026 — {len(STORIES)} STORIES · {len(regions)} REGIONS · {len(fields)} FIELDS · ONE PAGE',
              20, 'bold', WHITE, 'center')
    for y, counts, names, tint, label in (
        (157, regions, REGIONS, '#e5e8e9', 'REGIONS'),
        (179, fields, FIELDS, '#eee4d9', 'FIELDS'),
    ):
        page.rect((LEFT, y, 83, y + 18), NAVY)
        page.text(54, y + 4, label, 11, 'bold', WHITE, 'center')
        weights = [page.measure(f'{name}  {counts[name]}', 12, 'bold') + 24 for name in names]
        position = 87
        for name, weight in zip(names, weights):
            width = weight * (RIGHT - 87 + 4) / sum(weights)
            page.rect((position, y, position + width - 4, y + 18), tint)
            page.text(position + (width - 4) / 2, y + 3, f'{name}  {counts[name]}', 12, 'bold', INK, 'center')
            position += width
    page.rule(204)
    for index, (number, label) in enumerate(NUMBERS):
        width = (RIGHT - LEFT) / len(NUMBERS)
        x = LEFT + width * index
        if index:
            page.line(((x, 214), (x, 253)), RULE)
        page.text(x + width / 2, 211, number, 31, 'head', RED if index < 2 else NAVY, 'center', width - 12)
        page.text(x + width / 2, 243, label, 12, 'bold', INK, 'center', width - 10)
    page.rule(263, INK, 1.5)


def leads(page):
    page.rect((LEFT, 271, RIGHT, 383), '#eee7db')
    page.rect((LEFT, 271, LEFT + 5, 383), RED)
    page.text(42, 281, 'MIDDLE EAST · WAR & SECURITY — THE LEAD', 15, 'bold', RED)
    page.text(40, 298, STORIES[0][2], 52, 'head', fit=943)
    page.block(42, 352, page.wrap(STORIES[0][3], 930, 16, 'sans'), 16, 16)
    page.rule(390)
    page.text(LEFT, 400, 'ASIA · DISASTERS & WEATHER', 14, 'bold', TEAL)
    page.text(LEFT, 420, '300,000 flee as Cyclone Akvan', 33, 'head', fit=492)
    page.text(LEFT, 454, 'bears down on Odisha', 33, 'head', fit=492)
    page.block(LEFT, 491, page.wrap(STORIES[1][3], 492, 15, 'sans'), 15, 16)
    for index, bullet in enumerate((
        '423 rescue teams deployed; 69 trains cancelled; schools shut in eight districts.',
        '9,341 shelters opened; heavy-rain alerts across Odisha and Andhra Pradesh.',
    )):
        page.dot(27, 529 + index * 14, 2, RED)
        page.text(34, 524 + index * 14, bullet, 13, 'bold', INK, fit=479)
    cyclone(page)


def cyclone(page):
    page.rect((532, 398, RIGHT, 551), '#dcecf0')
    for x in range(552, RIGHT, 36):
        page.line(((x, 399), (x, 550)), '#c9dfe6', 0.5)
    for y in range(409, 551, 26):
        page.line(((533, y), (999, y)), '#c9dfe6', 0.5)
    coast = ((868, 398), (862, 411), (843, 420), (820, 422), (800, 433),
             (779, 438), (762, 453), (744, 457), (711, 474), (693, 480),
             (679, 493), (659, 497), (644, 509), (627, 510), (615, 525),
             (608, 542), (593, 551))
    page.poly(((532, 398), *coast, (532, 551)), '#eee1c7')
    page.line(coast, TEAL, 1.7)
    page.line(((554, 424), (601, 436), (642, 447), (682, 438), (731, 464)), '#afa184', 0.9)
    page.line(((623, 399), (671, 418), (696, 412), (717, 418), (752, 411), (780, 437)), '#afa184', 0.9)
    page.text(700, 426, 'ODISHA', 16, 'bold', NAVY)
    page.text(553, 457, 'ANDHRA PRADESH', 15, 'bold', NAVY)
    for name, dot, elbow, end in (
        ('PURI', (779, 438), (798, 458), (812, 458)),
        ('GOPALPUR', (744, 457), (722, 449), (689, 449)),
        ('NARSAPUR', (659, 497), (674, 514), (689, 514)),
    ):
        page.line((dot, elbow, end), GRAY, 0.9)
        page.dot(*dot, 3.4, WHITE)
        page.dot(*dot, 2.4, RED if name == 'GOPALPUR' else NAVY)
        if name == 'GOPALPUR':
            page.text(689, 443, name, 12, 'bold', RED, 'right')
        else:
            page.text(end[0] + 3, end[1] - 5, name, 12, 'bold', INK)
    page.text(973, 528, 'BAY OF BENGAL', 17, 'bold', TEAL, 'right')
    for phase in (0, 3.14159):
        spiral = []
        for step in range(38):
            angle = phase + step * 0.115
            radius = 3 + step * 0.63
            spiral.append((869 + radius * cos(angle), 485 + radius * sin(angle)))
        page.line(spiral, RED, 3.5)
    page.dot(869, 485, 2, RED)
    track = ((844, 501), (818, 505), (792, 497), (770, 480), (750, 461))
    page.line(track, RED, 2.2)
    tip, previous = track[-1], track[-2]
    angle = atan2(tip[1] - previous[1], tip[0] - previous[0])
    page.poly((tip, *((tip[0] - 11 * cos(angle + spread), tip[1] - 11 * sin(angle + spread))
                      for spread in (-0.53, 0.53))), RED)
    page.text(906, 478, 'AKVAN', 15, 'bold', RED)
    page.text(906, 493, 'TRACK TO LANDFALL', 11, 'bold', TEAL)
    page.line(((974, 439), (974, 419)), NAVY, 1)
    page.poly(((970, 424), (974, 417), (978, 424)), NAVY)
    page.text(974, 405, 'N', 11, 'bold', NAVY, 'center')


def vignette(page, number, x, y):
    height_scale = .9

    def rect(left, top, right, bottom, color):
        page.rect((x + left, y + top * height_scale, x + right, y + bottom * height_scale), color)

    def poly(points, color):
        page.poly([(x + horizontal, y + vertical * height_scale) for horizontal, vertical in points], color)

    def line(points, color, width=1):
        page.line([(x + horizontal, y + vertical * height_scale) for horizontal, vertical in points], color, width)

    def dot(horizontal, vertical, radius, color):
        page.dot(x + horizontal, y + vertical * height_scale, radius, color)

    def skyline(buildings, color):
        for left, width, top in buildings:
            rect(left, top, left + width, 30, color)

    def probe(horizontal, vertical, hull, panels):
        rect(horizontal - 24, vertical - 4, horizontal + 24, vertical + 4, panels)
        for offset in (-18, -12, 12, 18):
            line(((horizontal + offset, vertical - 4), (horizontal + offset, vertical + 4)), hull, 0.5)
        rect(horizontal - 7, vertical - 5, horizontal + 7, vertical + 6, hull)
        poly(((horizontal - 10, vertical - 8), (horizontal + 8, vertical - 12),
              (horizontal + 3, vertical - 5), (horizontal - 4, vertical - 4)), hull)

    if number == 3:
        rect(0, 0, 234, 30, '#e8ba91')
        dot(188, 13, 10, '#f6d6aa')
        skyline(((0, 18, 22), (20, 14, 18), (37, 14, 24), (65, 20, 20),
                 (89, 20, 24), (114, 14, 20), (133, 18, 18), (192, 22, 24), (221, 13, 18)), '#896b69')
        poly(((45, 30), (49, 5), (53, 4), (54, 10), (58, 14), (62, 10), (63, 4),
              (67, 5), (71, 30)), NAVY)
        for horizontal, vertical in ((101, 8), (127, 11), (153, 6)):
            dot(horizontal, vertical, 1.5, RED)
            line(((horizontal - 5, vertical), (horizontal + 5, vertical)), RED)
        poly(((164, 29), (161, 24), (166, 18), (167, 23), (172, 15),
              (175, 24), (178, 21), (179, 28), (175, 30)), RED)
    elif number == 4:
        rect(0, 0, 234, 30, '#182740')
        for horizontal, vertical in ((10, 5), (21, 20), (46, 8), (72, 21), (80, 5), (111, 24),
                                     (141, 6), (159, 24), (173, 8), (189, 13), (207, 25), (222, 6)):
            dot(horizontal, vertical, 0.8, '#d3d9e8')
        for offset in range(3):
            line(((31 + offset * 10, 23), (95 + offset * 4, 16)), '#587492', .65)
        probe(119, 16, '#e8d6ae', '#5d779f')
        line(((121, 8), (128, 3)), '#e8d6ae')
    elif number == 5:
        rect(0, 0, 234, 30, '#c6d3e0')
        skyline(((0, 18, 21), (22, 15, 17), (40, 23, 23), (66, 13, 16), (89, 20, 21),
                 (115, 14, 18), (170, 22, 22), (194, 13, 15), (212, 22, 20)), '#52708d')
        for offset in (9, 30, 49, 68):
            line([(offset + step * 3, 5 + step * step * .21) for step in range(10)], RED, 1)
        poly(((137, 7), (151, 4), (164, 7), (162, 18), (151, 27), (140, 18)), NAVY)
        line(((145, 15), (149, 19), (157, 11)), '#e8d6ae', 1.7)
    elif number == 6:
        rect(0, 0, 234, 30, '#d4e9df')
        for horizontal in range(12, 230, 18):
            line(((horizontal, 2), (horizontal, 28)), '#add2c6', .6)
        for vertical in (7, 15, 23):
            line(((1, vertical), (233, vertical)), '#add2c6', .6)
        line(((59, 25), (82, 18), (102, 21), (131, 12), (153, 15), (174, 9), (192, 10), (220, 4)), '#126c65', 2.4)
        poly(((220, 4), (211, 3), (216, 11)), '#126c65')
        rect(9, 6, 49, 24, '#126c65')
        page.text(x + 29, y + 9, 'ANT', 14, 'bold', WHITE, 'center')
    elif number == 7:
        rect(0, 0, 234, 30, '#3c3650')
        for horizontal, vertical in ((9, 9), (23, 21), (52, 4), (75, 21), (98, 5), (147, 4), (222, 6), (229, 20)):
            dot(horizontal, vertical, .75, '#e1d8ea')
        probe(105, 15, '#e2cbaa', '#9387b5')
        poly(((138, 30), (147, 21), (161, 16), (181, 18), (191, 12), (207, 17), (222, 30)), '#b2a9ae')
        poly(((166, 30), (170, 23), (191, 21), (207, 17), (222, 30)), '#807a8b')
        line(((133, 19), (141, 21)), '#e2cbaa')
    elif number == 8:
        for vertical in range(30):
            start, end = (123, 76, 142), (240, 154, 99)
            color = tuple(start[channel] + (end[channel] - start[channel]) * vertical // 29 for channel in range(3))
            rect(0, vertical, 234, vertical + 1, color)
        dot(150, 18, 11, '#f3bc81')
        skyline(((0, 27, 23), (35, 15, 14), (54, 16, 20), (75, 12, 9), (91, 19, 15),
                 (114, 17, 23), (143, 13, 21), (162, 28, 24), (221, 13, 22)), '#523858')
        line(((204, 30), (204, 18), (200, 10)), '#302640', 2.5)
        poly(((200, 10), (190, 6), (179, 12), (192, 10), (185, 17), (198, 12),
              (209, 17), (205, 10), (219, 12), (207, 6)), '#302640')
    elif number == 9:
        rect(0, 0, 234, 30, '#c2d6de')
        rect(0, 16, 234, 30, '#9db8ab')
        poly(((28, 30), (131, 14), (157, 14), (129, 30)), '#4a586a')
        for horizontal, vertical, length in ((84, 27, 13), (109, 22, 10), (130, 17.5, 6)):
            line(((horizontal, vertical), (horizontal + length, vertical)), WHITE, 1)
        for horizontal, vertical in ((82, 8), (117, 5), (153, 9)):
            line(((horizontal - 5, vertical), (horizontal + 5, vertical)), NAVY)
            dot(horizontal, vertical, 1.5, NAVY)
        dot(194, 15, 11, RED)
        rect(187, 13, 201, 17, WHITE)
    else:
        rect(0, 0, 234, 30, '#cee5e8')
        rect(0, 19, 234, 30, '#7aadb6')
        for horizontal in (10, 38, 169, 188, 211):
            line(((horizontal, 28), (horizontal + 10, 28)), '#cae0e3', .7)
        poly(((52, 19), (172, 19), (157, 27), (63, 27)), NAVY)
        rect(135, 7, 151, 18, WHITE)
        rect(139, 9, 148, 11, TEAL)
        for index, color in enumerate(('#b45344', '#d5945b', '#467896', '#837369')):
            horizontal = 67 + index * 16
            rect(horizontal, 12, horizontal + 14, 18, color)
            if index < 3:
                rect(horizontal + 4, 6, horizontal + 18, 11, color)


def grid(page):
    labels = ('WAR', 'SPACE', 'WAR', 'MARKETS', 'SPACE', 'CULTURE', 'WAR', 'MARKETS')
    for index, (region, _, title, deck) in enumerate(STORIES[2:10]):
        row, column = divmod(index, 4)
        x = LEFT + column * 247
        y = 562 + row * 96
        if not column:
            page.rule(y - 3)
        else:
            page.line(((x - 7, y), (x - 7, y + 85)), RULE)
        vignette(page, index + 3, x, y)
        page.text(x, y + 31, f'{index + 3} · {region} · {labels[index]}', 11, 'bold', RED)
        titles = page.wrap(title, 234, 19, 'head')
        assert len(titles) <= 2, title
        page.block(x, y + 43, titles, 19, 17, 'head')
        page.text(x, y + 80, deck, 11.7, 'sans', GRAY, fit=234)


CONTINENTS = (
    ((4, 27), (12, 17), (26, 16), (41, 8), (56, 11), (62, 6), (78, 8), (89, 15),
     (81, 22), (72, 25), (69, 34), (57, 40), (60, 46), (54, 45), (51, 40),
     (42, 40), (38, 35), (28, 31), (25, 25), (13, 26), (7, 30)),
    ((80, 10), (96, 5), (107, 7), (104, 17), (94, 26), (87, 23), (88, 17)),
    ((54, 47), (60, 43), (69, 47), (73, 52), (84, 54), (80, 64), (72, 70),
     (69, 80), (61, 88), (58, 79), (59, 70), (54, 60), (51, 54)),
    ((93, 28), (100, 21), (102, 13), (115, 10), (127, 12), (135, 8), (147, 13),
     (161, 11), (177, 12), (190, 10), (206, 17), (200, 22), (188, 22), (191, 28),
     (181, 33), (170, 35), (164, 44), (156, 43), (160, 53), (155, 52), (147, 43),
     (143, 40), (140, 49), (134, 52), (127, 43), (122, 38), (116, 44), (112, 38),
     (105, 33), (99, 34), (96, 30)),
    ((101, 33), (112, 35), (117, 42), (124, 45), (118, 53), (116, 65), (109, 74),
     (103, 70), (101, 62), (103, 55), (93, 52), (89, 45), (93, 37)),
    ((153, 53), (160, 54), (170, 58), (178, 59), (181, 62), (168, 63), (157, 59)),
    ((163, 68), (175, 65), (183, 68), (190, 65), (196, 72), (194, 82), (186, 85),
     (178, 78), (166, 80), (161, 76)),
    ((178, 30), (184, 28), (185, 32), (179, 38), (175, 37)),
    ((121, 64), (125, 59), (127, 61), (124, 69), (121, 70)),
    ((200, 80), (205, 76), (207, 80), (200, 87), (197, 86)),
)


def atlas(page):
    page.rule(752, INK, 1.3)
    page.text(LEFT, 759, 'WHERE IT HAPPENED', 18, 'head')
    page.text(250, 759, 'ALSO ON FRIDAY 20 NOVEMBER', 18, 'head')
    page.rule(780)
    page.line(((242, 758), (242, 938)), RULE)
    page.line(((620, 785), (620, 937)), RULE)
    page.rect((LEFT, 787, 233, 892), '#e8ece8')
    mask = Image.new('1', (210, 92))
    stencil = ImageDraw.Draw(mask)
    for continent in CONTINENTS:
        stencil.polygon(continent, fill=1)
    origin_x, origin_y = LEFT, 797
    for vertical in range(4, 91, 3):
        for horizontal in range(2, 210, 3):
            if mask.getpixel((horizontal, vertical)):
                page.dot(origin_x + horizontal, origin_y + vertical, .89, TEAL)
    for number, (horizontal, vertical), (anchor_x, anchor_y) in (
        (1, (132, 24), (121, 36)), (2, (146, 54), (137, 44)),
        (3, (116, 58), (115, 42)), (5, (117, 14), (109, 24)),
        (6, (40, 19), (48, 28)), (8, (22, 43), (39, 33)),
        (9, (84, 25), (102, 29)), (10, (184, 41), (173, 34)),
    ):
        page.line(((origin_x + horizontal, origin_y + vertical), (origin_x + anchor_x, origin_y + anchor_y)), RED, .95)
        page.dot(origin_x + anchor_x, origin_y + anchor_y, 1.7, RED)
        pin(page, origin_x + horizontal, origin_y + vertical, number)
    page.rect((LEFT, 898, 233, 919), '#e5e8e9')
    page.text(31, 903, 'OFF WORLD', 11, 'bold', NAVY)
    pin(page, 97, 908.5, 4)
    page.text(106, 903, 'Voyager 1', 11, 'bold', NAVY)
    pin(page, 164, 908.5, 7)
    page.text(173, 903, 'Hayabusa2', 11, 'bold', NAVY)
    page.text(LEFT, 925, 'Pins show approximate story locations.', 11, 'sans', GRAY)
    for index, (region, _, news) in enumerate(STORIES[10:]):
        column, row = divmod(index, 13)
        x = 250 + 378 * column
        y = 785 + 11.85 * row
        prefix = f'{index + 11}  {region} — '
        width = page.measure(prefix, 11, 'bold')
        if row % 2 == 0:
            page.rect((x - 2, y - 1, x + 370, y + 10.7), '#efeade')
        page.text(x, y, prefix, 11, 'bold', NAVY)
        page.text(x + width, y, news, 11, 'sans', fit=369 - width)


def pin(page, x, y, number):
    page.oval((x - 7, y - 7, x + 7, y + 7), RED, WHITE, .7)
    page.text(x, y - 4.5, str(number), 11, 'bold', WHITE, 'center', 11)


def closing(page):
    page.rect((LEFT, 944, RIGHT, 981), '#f4e9e0', RED)
    page.text(32, 956, 'DATE CHECK', 14, 'bold', RED)
    page.text(111, 956, '—', 14, 'bold', RED)
    lines = page.wrap(DATE_CHECK, 863, 11.4, 'sans')
    assert len(lines) <= 3
    page.block(130, 947, lines, 11.4, 11.4)
    page.text(LEFT, 990, FOOTER, 11, 'sans', GRAY, fit=976)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().with_name('entry.png'))
    args = parser.parse_args()
    page = Page()
    banner(page)
    leads(page)
    grid(page)
    atlas(page)
    closing(page)
    image = page.image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    image.save(args.output, format='PNG', optimize=True)


if __name__ == '__main__':
    main()
