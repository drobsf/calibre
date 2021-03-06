#!/usr/bin/env python2
# vim:fileencoding=utf-8
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2013, Kovid Goyal <kovid at kovidgoyal.net>'

from future_builtins import zip
from functools import wraps

try:
    from cssutils.css import PropertyValue
except ImportError:
    raise RuntimeError('You need cssutils >= 0.9.9 for calibre')
from cssutils import profile as cssprofiles, CSSParser

DEFAULTS = {'azimuth': 'center', 'background-attachment': 'scroll',  # {{{
            'background-color': 'transparent', 'background-image': 'none',
            'background-position': '0% 0%', 'background-repeat': 'repeat',
            'border-bottom-color': 'currentColor', 'border-bottom-style':
            'none', 'border-bottom-width': 'medium', 'border-collapse':
            'separate', 'border-left-color': 'currentColor',
            'border-left-style': 'none', 'border-left-width': 'medium',
            'border-right-color': 'currentColor', 'border-right-style': 'none',
            'border-right-width': 'medium', 'border-spacing': 0,
            'border-top-color': 'currentColor', 'border-top-style': 'none',
            'border-top-width': 'medium', 'bottom': 'auto', 'caption-side':
            'top', 'clear': 'none', 'clip': 'auto', 'color': 'black',
            'content': 'normal', 'counter-increment': 'none', 'counter-reset':
            'none', 'cue-after': 'none', 'cue-before': 'none', 'cursor':
            'auto', 'direction': 'ltr', 'display': 'inline', 'elevation':
            'level', 'empty-cells': 'show', 'float': 'none', 'font-family':
            'serif', 'font-size': 'medium', 'font-style': 'normal',
            'font-variant': 'normal', 'font-weight': 'normal', 'height':
            'auto', 'left': 'auto', 'letter-spacing': 'normal', 'line-height':
            'normal', 'list-style-image': 'none', 'list-style-position':
            'outside', 'list-style-type': 'disc', 'margin-bottom': 0,
            'margin-left': 0, 'margin-right': 0, 'margin-top': 0, 'max-height':
            'none', 'max-width': 'none', 'min-height': 0, 'min-width': 0,
            'orphans': '2', 'outline-color': 'invert', 'outline-style': 'none',
            'outline-width': 'medium', 'overflow': 'visible', 'padding-bottom':
            0, 'padding-left': 0, 'padding-right': 0, 'padding-top': 0,
            'page-break-after': 'auto', 'page-break-before': 'auto',
            'page-break-inside': 'auto', 'pause-after': 0, 'pause-before': 0,
            'pitch': 'medium', 'pitch-range': '50', 'play-during': 'auto',
            'position': 'static', 'quotes': u"'“' '”' '‘' '’'", 'richness':
            '50', 'right': 'auto', 'speak': 'normal', 'speak-header': 'once',
            'speak-numeral': 'continuous', 'speak-punctuation': 'none',
            'speech-rate': 'medium', 'stress': '50', 'table-layout': 'auto',
            'text-align': 'auto', 'text-decoration': 'none', 'text-indent': 0,
            'text-shadow': 'none', 'text-transform': 'none', 'top': 'auto',
            'unicode-bidi': 'normal', 'vertical-align': 'baseline',
            'visibility': 'visible', 'voice-family': 'default', 'volume':
            'medium', 'white-space': 'normal', 'widows': '2', 'width': 'auto',
            'word-spacing': 'normal', 'z-index': 'auto'}
# }}}

EDGES = ('top', 'right', 'bottom', 'left')
BORDER_PROPS = ('color', 'style', 'width')

def normalize_edge(name, cssvalue):
    style = {}
    if isinstance(cssvalue, PropertyValue):
        primitives = [v.cssText for v in cssvalue]
    else:
        primitives = [cssvalue.cssText]
    if len(primitives) == 1:
        value, = primitives
        values = (value, value, value, value)
    elif len(primitives) == 2:
        vert, horiz = primitives
        values = (vert, horiz, vert, horiz)
    elif len(primitives) == 3:
        top, horiz, bottom = primitives
        values = (top, horiz, bottom, horiz)
    else:
        values = primitives[:4]
    if '-' in name:
        l, _, r = name.partition('-')
        for edge, value in zip(EDGES, values):
            style['%s-%s-%s' % (l, edge, r)] = value
    else:
        for edge, value in zip(EDGES, values):
            style['%s-%s' % (name, edge)] = value
    return style


def simple_normalizer(prefix, names, check_inherit=True):
    composition = tuple('%s-%s' %(prefix, n) for n in names)
    @wraps(normalize_simple_composition)
    def wrapper(name, cssvalue):
        return normalize_simple_composition(name, cssvalue, composition, check_inherit=check_inherit)
    return wrapper


def normalize_simple_composition(name, cssvalue, composition, check_inherit=True):
    if check_inherit and cssvalue.cssText == 'inherit':
        style = {k:'inherit' for k in composition}
    else:
        style = {k:DEFAULTS[k] for k in composition}
        try:
            primitives = [v.cssText for v in cssvalue]
        except TypeError:
            primitives = [cssvalue.cssText]
        while primitives:
            value = primitives.pop()
            for key in composition:
                if cssprofiles.validate(key, value):
                    style[key] = value
                    break
    return style

font_composition = ('font-style', 'font-variant', 'font-weight', 'font-size', 'line-height', 'font-family')

def normalize_font(cssvalue, font_family_as_list=False):
    # See https://developer.mozilla.org/en-US/docs/Web/CSS/font
    composition = font_composition
    val = cssvalue.cssText
    if val == 'inherit':
        return {k:'inherit' for k in composition}
    if val in {'caption', 'icon', 'menu', 'message-box', 'small-caption', 'status-bar'}:
        return {k:DEFAULTS[k] for k in composition}
    if getattr(cssvalue, 'length', 1) < 2:
        return {}  # Mandatory to define both font size and font family
    style = {k:DEFAULTS[k] for k in composition}
    families = []
    vals = [x.cssText for x in cssvalue]
    found_font_size = False
    while vals:
        text = vals.pop()
        if not families and text == 'inherit':
            families.append(text)
            continue
        if cssprofiles.validate('line-height', text):
            if not vals or not cssprofiles.validate('font-size', vals[-1]):
                if cssprofiles.validate('font-size', text):
                    style['font-size'] = text
                    found_font_size = True
                    break
                return {}  # must have font-size here
            style['line-height'] = text
            style['font-size'] = vals.pop()
            found_font_size = True
            break
        if cssprofiles.validate('font-size', text):
            style['font-size'] = text
            found_font_size = True
            break
        if families == ['inherit']:
            return {}  # Cannot have multiple font-families if the last one if inherit
        families.insert(0, text)
    if not families or not found_font_size:
        return {}  # font-family required
    style['font-family'] = families if font_family_as_list else ', '.join(families)
    props = ['font-style', 'font-variant', 'font-weight']
    while vals:
        for i, prop in enumerate(tuple(props)):
            if cssprofiles.validate(prop, vals[0]):
                props.pop(i)
                style[prop] = vals.pop(0)
                break
        else:
            return {}  # unrecognized value

    return style

def normalize_border(name, cssvalue):
    style = normalizers['border-' + EDGES[0]]('border-' + EDGES[0], cssvalue)
    vals = style.copy()
    for edge in EDGES[1:]:
        style.update({k.replace(EDGES[0], edge):v for k, v in vals.iteritems()})
    return style

normalizers = {
    'list-style': simple_normalizer('list-style', ('type', 'position', 'image')),
    'font': lambda prop, v: normalize_font(v),
    'border': normalize_border,
}

for x in ('margin', 'padding', 'border-style', 'border-width', 'border-color'):
    normalizers[x] = normalize_edge

for x in EDGES:
    name = 'border-' + x
    normalizers[name] = simple_normalizer(name, BORDER_PROPS, check_inherit=False)

SHORTHAND_DEFAULTS = {
    'margin': '0', 'padding': '0', 'border-style': 'none', 'border-width': '0', 'border-color': 'currentColor',
    'border':'none', 'border-left': 'none', 'border-right':'none', 'border-top': 'none', 'border-bottom': 'none',
    'list-style': 'inherit', 'font': 'inherit',
}

def normalize_filter_css(props):
    import logging
    ans = set()
    p = CSSParser(loglevel=logging.CRITICAL, validate=False)
    for prop in props:
        n = normalizers.get(prop, None)
        ans.add(prop)
        if n is not None and prop in SHORTHAND_DEFAULTS:
            dec = p.parseStyle('%s: %s' % (prop, SHORTHAND_DEFAULTS[prop]))
            cssvalue = dec.getPropertyCSSValue(dec.item(0))
            ans |= set(n(prop, cssvalue))
    return ans

def condense_edge(vals):
    edges = {x.name.rpartition('-')[-1]:x.value for x in vals}
    if len(edges) != 4 or set(edges) != {'left', 'top', 'right', 'bottom'}:
        return
    ce = {}
    for (x, y) in [('left', 'right'), ('top', 'bottom')]:
        if edges[x] == edges[y]:
            ce[x] = edges[x]
        else:
            ce[x], ce[y] = edges[x], edges[y]
    if len(ce) == 4:
        return ' '.join(ce[x] for x in ('top', 'right', 'bottom', 'left'))
    if len(ce) == 3:
        if 'right' in ce:
            return ' '.join(ce[x] for x in ('top', 'right', 'top', 'left'))
        return ' '.join(ce[x] for x in ('top', 'left', 'bottom'))
    if len(ce) == 2:
        if ce['top'] == ce['left']:
            return ce['top']
        return ' '.join(ce[x] for x in ('top', 'left'))

def simple_condenser(prefix, func):
    @wraps(func)
    def condense_simple(style, props):
        cp = func(props)
        if cp is not None:
            for prop in props:
                style.removeProperty(prop.name)
            style.setProperty(prefix, cp)
    return condense_simple

def condense_border(style, props):
    prop_map = {p.name:p for p in props}
    edge_vals = []
    for edge in EDGES:
        name = 'border-%s' % edge
        vals = []
        for prop in BORDER_PROPS:
            x = prop_map.get('%s-%s' % (name, prop), None)
            if x is not None:
                vals.append(x)
        if len(vals) == 3:
            for prop in vals:
                style.removeProperty(prop.name)
            style.setProperty(name, ' '.join(x.value for x in vals))
            prop_map[name] = style.getProperty(name)
        x = prop_map.get(name, None)
        if x is not None:
            edge_vals.append(x)
    if len(edge_vals) == 4 and len({x.value for x in edge_vals}) == 1:
        for prop in edge_vals:
            style.removeProperty(prop.name)
        style.setProperty('border', edge_vals[0].value)

condensers = {'margin': simple_condenser('margin', condense_edge), 'padding': simple_condenser('padding', condense_edge), 'border': condense_border}


def condense_rule(style):
    expanded = {'margin-':[], 'padding-':[], 'border-':[]}
    for prop in style.getProperties():
        for x in expanded:
            if prop.name and prop.name.startswith(x):
                expanded[x].append(prop)
                break
    for prefix, vals in expanded.iteritems():
        if len(vals) > 1 and {x.priority for x in vals} == {''}:
            condensers[prefix[:-1]](style, vals)

def condense_sheet(sheet):
    for rule in sheet.cssRules:
        if rule.type == rule.STYLE_RULE:
            condense_rule(rule.style)

def test_normalization():  # {{{
    import unittest
    from cssutils import parseStyle
    from itertools import product

    class TestNormalization(unittest.TestCase):
        longMessage = True
        maxDiff = None

        def test_font_normalization(self):
            def font_dict(expected):
                ans = {k:DEFAULTS[k] for k in font_composition} if expected else {}
                ans.update(expected)
                return ans

            for raw, expected in {
                'some_font': {}, 'none': {}, 'inherit':{k:'inherit' for k in font_composition},
                '1.2pt/1.4 A_Font': {'font-family':'A_Font', 'font-size':'1.2pt', 'line-height':'1.4'},
                'bad font': {}, '10% serif': {'font-family':'serif', 'font-size':'10%'},
                '12px "My Font", serif': {'font-family':'"My Font", serif', 'font-size': '12px'},
                'normal 0.6em/135% arial,sans-serif': {'font-family': 'arial, sans-serif', 'font-size': '0.6em', 'line-height':'135%', 'font-style':'normal'},
                'bold italic large serif': {'font-family':'serif', 'font-weight':'bold', 'font-style':'italic', 'font-size':'large'},
                'bold italic small-caps larger/normal serif':
                {'font-family':'serif', 'font-weight':'bold', 'font-style':'italic', 'font-size':'larger',
                 'line-height':'normal', 'font-variant':'small-caps'},
            }.iteritems():
                val = tuple(parseStyle('font: %s' % raw, validate=False))[0].cssValue
                style = normalizers['font']('font', val)
                self.assertDictEqual(font_dict(expected), style, raw)

        def test_border_normalization(self):
            def border_edge_dict(expected, edge='right'):
                ans = {'border-%s-%s' % (edge, x): DEFAULTS['border-%s-%s' % (edge, x)] for x in ('style', 'width', 'color')}
                for x, v in expected.iteritems():
                    ans['border-%s-%s' % (edge, x)] = v
                return ans
            def border_dict(expected):
                ans = {}
                for edge in EDGES:
                    ans.update(border_edge_dict(expected, edge))
                return ans
            def border_val_dict(expected, val='color'):
                ans = {'border-%s-%s' % (edge, val): DEFAULTS['border-%s-%s' % (edge, val)] for edge in EDGES}
                for edge in EDGES:
                    ans['border-%s-%s' % (edge, val)] = expected
                return ans

            for raw, expected in {
                'solid 1px red': {'color':'red', 'width':'1px', 'style':'solid'},
                '1px': {'width': '1px'}, '#aaa': {'color': '#aaa'},
                '2em groove': {'width':'2em', 'style':'groove'},
            }.iteritems():
                for edge in EDGES:
                    br = 'border-%s' % edge
                    val = tuple(parseStyle('%s: %s' % (br, raw), validate=False))[0].cssValue
                    self.assertDictEqual(border_edge_dict(expected, edge), normalizers[br](br, val))

            for raw, expected in {
                'solid 1px red': {'color':'red', 'width':'1px', 'style':'solid'},
                '1px': {'width': '1px'}, '#aaa': {'color': '#aaa'},
                'thin groove': {'width':'thin', 'style':'groove'},
            }.iteritems():
                val = tuple(parseStyle('%s: %s' % ('border', raw), validate=False))[0].cssValue
                self.assertDictEqual(border_dict(expected), normalizers['border']('border', val))

            for name, val in {
                'width': '10%', 'color': 'rgb(0, 1, 1)', 'style': 'double',
            }.iteritems():
                cval = tuple(parseStyle('border-%s: %s' % (name, val), validate=False))[0].cssValue
                self.assertDictEqual(border_val_dict(val, name), normalizers['border-'+name]('border-'+name, cval))

        def test_edge_normalization(self):
            def edge_dict(prefix, expected):
                return {'%s-%s' % (prefix, edge) : x for edge, x in zip(EDGES, expected)}
            for raw, expected in {
                '2px': ('2px', '2px', '2px', '2px'),
                '1em 2em': ('1em', '2em', '1em', '2em'),
                '1em 2em 3em': ('1em', '2em', '3em', '2em'),
                '1 2 3 4': ('1', '2', '3', '4'),
            }.iteritems():
                for prefix in ('margin', 'padding'):
                    cval = tuple(parseStyle('%s: %s' % (prefix, raw), validate=False))[0].cssValue
                    self.assertDictEqual(edge_dict(prefix, expected), normalizers[prefix](prefix, cval))

        def test_list_style_normalization(self):
            def ls_dict(expected):
                ans = {'list-style-%s' % x : DEFAULTS['list-style-%s' % x] for x in ('type', 'image', 'position')}
                for k, v in expected.iteritems():
                    ans['list-style-%s' % k] = v
                return ans
            for raw, expected in {
                'url(http://www.example.com/images/list.png)': {'image': 'url(http://www.example.com/images/list.png)'},
                'inside square': {'position':'inside', 'type':'square'},
                'upper-roman url(img) outside': {'position':'outside', 'type':'upper-roman', 'image':'url(img)'},
            }.iteritems():
                cval = tuple(parseStyle('list-style: %s' % raw, validate=False))[0].cssValue
                self.assertDictEqual(ls_dict(expected), normalizers['list-style']('list-style', cval))

        def test_filter_css_normalization(self):
            ae = self.assertEqual
            ae({'font'} | set(font_composition), normalize_filter_css({'font'}))
            for p in ('margin', 'padding'):
                ae({p} | {p + '-' + x for x in EDGES}, normalize_filter_css({p}))
            bvals = {'border-%s-%s' % (edge, x) for edge in EDGES for x in BORDER_PROPS}
            ae(bvals | {'border'}, normalize_filter_css({'border'}))
            for x in BORDER_PROPS:
                sbvals = {'border-%s-%s' % (e, x) for e in EDGES}
                ae(sbvals | {'border-%s' % x}, normalize_filter_css({'border-%s' % x}))
            for e in EDGES:
                sbvals = {'border-%s-%s' % (e, x) for x in BORDER_PROPS}
                ae(sbvals | {'border-%s' % e}, normalize_filter_css({'border-%s' % e}))
            ae({'list-style', 'list-style-image', 'list-style-type', 'list-style-position'}, normalize_filter_css({'list-style'}))

        def test_edge_condensation(self):
            for s, v in {
                (1, 1, 3) : None,
                (1, 2, 3, 4) : '2pt 3pt 4pt 1pt',
                (1, 2, 3, 2) : '2pt 3pt 2pt 1pt',
                (1, 2, 1, 3) : '2pt 1pt 3pt',
                (1, 2, 1, 2) : '2pt 1pt',
                (1, 1, 1, 1) : '1pt',
                ('2%', '2%', '2%', '2%') : '2%',
                tuple('0 0 0 0'.split()) : '0',
            }.iteritems():
                for prefix in ('margin', 'padding'):
                    css = {'%s-%s' % (prefix, x) : str(y)+'pt' if isinstance(y, (int, float)) else y for x, y in zip(('left', 'top', 'right', 'bottom'), s)}
                    css = '; '.join(('%s:%s' % (k, v) for k, v in css.iteritems()))
                    style = parseStyle(css)
                    condense_rule(style)
                    val = getattr(style.getProperty(prefix), 'value', None)
                    self.assertEqual(v, val)
                    if val is not None:
                        for edge in EDGES:
                            self.assertFalse(getattr(style.getProperty('%s-%s' % (prefix, edge)), 'value', None))

        def test_border_condensation(self):
            vals = 'red solid 5px'
            css = '; '.join('border-%s-%s: %s' % (edge, p, v) for edge in EDGES for p, v in zip(BORDER_PROPS, vals.split()))
            style = parseStyle(css)
            condense_rule(style)
            for e, p in product(EDGES, BORDER_PROPS):
                self.assertFalse(style.getProperty('border-%s-%s' % (e, p)))
                self.assertFalse(style.getProperty('border-%s' % e))
                self.assertFalse(style.getProperty('border-%s' % p))
            self.assertEqual(style.getProperty('border').value, vals)
            css = '; '.join('border-%s-%s: %s' % (edge, p, v) for edge in ('top',) for p, v in zip(BORDER_PROPS, vals.split()))
            style = parseStyle(css)
            condense_rule(style)
            self.assertEqual(style.cssText, 'border-top: %s' % vals)
            css += ';' + '; '.join('border-%s-%s: %s' % (edge, p, v) for edge in ('right', 'left', 'bottom') for p, v in
                             zip(BORDER_PROPS, vals.replace('red', 'green').split()))
            style = parseStyle(css)
            condense_rule(style)
            self.assertEqual(len(style.getProperties()), 4)
            self.assertEqual(style.getProperty('border-top').value, vals)
            self.assertEqual(style.getProperty('border-left').value, vals.replace('red', 'green'))

    tests = unittest.defaultTestLoader.loadTestsFromTestCase(TestNormalization)
    unittest.TextTestRunner(verbosity=4).run(tests)
# }}}

if __name__ == '__main__':
    test_normalization()
