#!/usr/bin/python3

"""Start developping here as in a sandbox.
Let's first use pseudo-"binary" codes stored and manipulated as python
strings for simplicity.
"""

# to draw and export pdf barcodes
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from matplotlib.textpath import TextPath
from math import ceil
import numpy as np
import numpy.random as rd
# to subclass `str` in a lazy way
# https://stackoverflow.com/questions/46868085/
from collections import UserString
# for grouping successive similar bits together
# https://stackoverflow.com/a/34444401/3719101
from itertools import groupby
# to compose pdf layout from many barcode files
import svgutils.compose as sc
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from PyPDF2 import PdfFileWriter, PdfFileReader
# for handling temporary files
import os
# for processing command line arguments
import sys

def append_pdf(input,output):
    """concatenate pdf's together
    https://stackoverflow.com/a/3444735/3719101
    """
    [output.addPage(input.getPage(page_num))
            for page_num in range(input.numPages)]

def loopstep(start, digits='0123456789'):
    """Iterate forever on all digit combinations of fixed length
    (strongest left), starting from the string given as a start, going
    frontwards, looping, then going on :P

    recursive

    >>> g = loopstep('bcc', 'abc')
    >>> for i in range(100):
    ...     print(next(g)) # doctest: +NORMALIZE_WHITESPACE
    bcc caa cab cac cba cbb cbc cca ccb ccc aaa aab aac aba abb abc aca acb acc
    baa bab bac bba bbb bbc bca bcb bcc caa cab cac cba cbb cbc cca ccb ccc aaa
    aab aac aba abb abc aca acb acc baa bab bac bba bbb bbc bca bcb bcc caa cab
    cac cba cbb cbc cca ccb ccc aaa aab aac aba abb abc aca acb acc baa bab bac
    bba bbb bbc bca bcb bcc caa cab cac cba cbb cbc cca ccb ccc aaa aab aac aba
    abb abc aca acb acc
    >>> g = loopstep('89', '0123456789')
    >>> for i in range(222):
    ...     print(next(g)) # doctest: +NORMALIZE_WHITESPACE
    89 90 91 92 93 94 95 96 97 98 99 00 01 02 03 04 05 06 07 08 09 10 11 12 13
    14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38
    39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63
    64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88
    89 90 91 92 93 94 95 96 97 98 99 00 01 02 03 04 05 06 07 08 09 10 11 12 13
    14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38
    39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63
    64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88
    89 90 91 92 93 94 95 96 97 98 99 00 01 02 03 04 05 06 07 08 09 10
    """
    l = len(start)
    if l == 1:
        # loop forever on digits, starting from the first one
        found = False # dont yield until we have found the first one
        g = iter(digits)
        while True:
            try:
                d = next(g)
            except StopIteration:
                g = iter(digits)
                d = next(g)
            if found:
                yield d
            elif d == start:
                found = True
                yield d
    else:
        first = start[0]
        end = start[1:]
        last = digits[-1:]
        zero = digits[0] * (l - 1)
        for f in loopstep(first, digits):
            for e in loopstep(end, digits):
                yield f + e
                if all(d == last for d in e):
                    break
            end = zero
            continue

def loop_round(start, digits='0123456789', stop=None, include_last=False):
    """Iterate with loopstep, but only until the next time we get back
    on start.. or any stop you'd like

    >>> for i in loop_round('ba', 'abc'):
    ...     print(i) # doctest: +NORMALIZE_WHITESPACE
    ba bb bc ca cb cc aa ab ac
    >>> for i in loop_round('ba', 'abc', include_last=True):
    ...     print(i) # doctest: +NORMALIZE_WHITESPACE
    ba bb bc ca cb cc aa ab ac ba
    >>> for i in loop_round('89', '0123456789', stop='13'):
    ...     print(i) # doctest: +NORMALIZE_WHITESPACE
    89 90 91 92 93 94 95 96 97 98 99 00 01 02 03 04 05 06 07 08 09 10 11 12
    """
    if not stop:
        stop = start
    g = loopstep(start, digits)
    yield next(g)
    for i in g:
        if i == stop:
            if include_last:
                yield i
            break
        yield i

class XY(np.ndarray):
    """Hold coordinates with convenience operators :P
    Also statically holds conversion towards and from svg standard user
    units only: https://www.w3.org/TR/SVG/coords.html#Units

    >>> a = XY(1., 5.)
    >>> a
    XY(1.0, 5.0)
    >>> (a.x, a.y)
    (1.0, 5.0)
    >>> a.x *= 2
    >>> a
    XY(2.0, 5.0)
    >>> # and all common np.ndarray operators ;)
    >>> a + a
    XY(4.0, 10.0)
    >>> a = WH(1., 5.) # alias
    >>> a
    XY(1.0, 5.0)
    >>> (a.w, a.h)
    (1.0, 5.0)
    """

    inch = 90. # ui
    pt = 1.25 # ui
    mm = 3.543307 # ui
    cm = 35.43307 # ui

    def __new__(self, x, y):
        return np.ndarray.__new__(self, shape=2, dtype=float)

    def __init__(self, x, y):
        self[0] = x
        self[1] = y

    def __repr__(self):
        return "XY({}, {})".format(self.x, self.y)

    @property
    def x(self):
        return self[0]

    @x.setter
    def x(self, value):
        self[0] = value

    @property
    def y(self):
        return self[1]

    @y.setter
    def y(self, value):
        self[1] = value

    @property
    def w(self):
        return self.x

    @w.setter
    def w(self, value):
        self.x = value

    @property
    def h(self):
        return self.y

    @h.setter
    def h(self, value):
        self.y = value

class WH(XY):
    """alias for holding widths and heights
    """
    pass


class Code(UserString, str):
    """our python view on a EAN13 'code': a serie of bits stored as
    a plain string of 0 or 1

    >>> c = Code('001010')
    >>> c
    <001010>
    >>> # custom interface
    >>> c.flip
    <110101>
    >>> # usual `str` operators
    >>> c * 2
    <001010001010>
    >>> c + c
    <001010001010>
    """

    @property
    def flip(self):
        return Code(''.join(['1' if b == '0' else '0' for b in self]))

    def __repr__(self):
        return "<{}>".format(self.data)


class EAN13Data(object):
    """Holds static information about EAN13 encoding
    For information:
    https://fr.wikipedia.org/wiki/Code-barres_EAN
    https://en.wikipedia.org/wiki/International_Article_Number
    """

    white = Code('0')
    black = Code('1')
    length = 13

    # "elements" of encoding, alternance of lengths
    A_lengths = {
          '0': '3211',
          '1': '2221',
          '2': '2122',
          '3': '1411',
          '4': '1132',
          '5': '1231',
          '6': '1114',
          '7': '1312',
          '8': '1213',
          '9': '3112',
          'first': white, # color of first bar
        }
    C_lengths = A_lengths.copy()
    C_lengths['first'] = black
    B_lengths = {
            '0': '1123',
            '1': '1222',
            '2': '2212',
            '3': '1141',
            '4': '2311',
            '5': '1321',
            '6': '4111',
            '7': '2131',
            '8': '3121',
            '9': '2113',
            'first': white, # color of first bar
            }
    guards = {'normal': Code('101'),
              'central': Code('01010')}
    for k, v in guards.copy().items(): # add shortcuts
        guards[k[0]] = v

    def _lengths_to_code(dico):
        """Convert one above dictionnary of lengths to an actual
        dictionnary of code
        """
        res = {}
        color = dico.pop('first')
        for i, lens in dico.items():
            seq = Code('')
            for l in lens:
                seq += color * int(l)
                color = color.flip
            res[i] = seq
        return res

    # actual element codes for each numbers or guards
    elements = {
            'n': guards['normal'],
            'A': _lengths_to_code(A_lengths),
            'B': _lengths_to_code(B_lengths),
            'c': guards['central'],
            'C': _lengths_to_code(C_lengths),
            }

    # "structure" of the EAN13 code, in terms of A-B-C alternance,
    # depending on its first number:
    structure = {
            '0': 'AAAAAA',
            '1': 'AABABB',
            '2': 'AABBAB',
            '3': 'AABBBA',
            '4': 'ABAABB',
            '5': 'ABBAAB',
            '6': 'ABBBAA',
            '7': 'ABABAB',
            '8': 'ABABBA',
            '9': 'ABBABA',
            }
    structure = {i: 'n{}cCCCCCCn'.format(v) for i, v in structure.items()}

    n_bars = 2*len(elements['n']) + len(elements['c']) \
            + 6 * len(elements['A']['0']) \
            + 6 * len(elements['C']['0'])

    # dimensions in ui according to
    # http://www.gs1.fr/content/download/2694/19049/version/2/file/
    # GS1_mes%20codes%20a%CC%80%20barres%20premiers%20pas%202016%20.pdf
    mm = XY.mm
    code_size = WH(37.29, 26.26) * mm # size of the printed code
    before_white = 3.63 * mm # padding white
    after_white = 2.31 * mm # padding white
    full_size = WH(before_white + code_size.w + after_white, code_size.h)
    elts_size = WH(31.35, 22.85) * mm # all small elements
    label_size = WH(code_size.w, code_size.h - elts_size.h) # text
    elt_size = WH(elts_size.w / n_bars, elts_size.h) # one small bar
    guard_size = WH(elt_size.w, .5 * (code_size.h + elts_size.h)) # guard
    # this length seems missing from the doc. make a choice: space between
    # beginning of the first digit and the first bar:
    shift = 3 * mm
    del mm


class EAN13(object):
    """Embed EAN13 code concept.. still a sandbox.
    'id': stands for the numeric [0-9]digits value of the code
    'code': stands for its binary "bars" value [0-1]digits values

    >>> c = EAN13('041259863013') # with a string or an integer
    >>> c.checksum
    '0'
    >>> c = EAN13(9782940199617) # allright if you already know the checksum.
    >>> c # doctest:
    EAN13:9-782940-199617
    10101110110001001001101100010110011101000110101010110011011101001110100101000011001101000100101
    >>> c.code_dashed
    '101-0111011-0001001-0011011-0001011-0011101-0001101-01010-1100110-1110100-1110100-1010000-1100110-1000100-101'
    >>> c.structure
    'nABBABAcCCCCCCn'
    """

    def _encode(self):
        """translate id to a binary code, also fill structure and
        dissociated elements information
        called during __init__
        """
        data = EAN13Data
        digits = list(self.id)
        # first digit in encoded as code structure
        first = digits.pop(0)
        structure = data.structure[first]
        # now just read it :)
        code = Code('')
        elements = []
        for element in structure:
            if element in data.guards:
                elt_cd = data.elements[element]
            else:
                elt_cd = data.elements[element][digits.pop(0)]
            elements.append(elt_cd)
            code += elt_cd
        self.structure = structure
        self.code = code
        self.elements = elements

    def _compute_checksum(self):
        """compute and return the checksum
        """
        id = [int(c) for c in self.id[0:12]]
        hln = len(id) // 2 # half length
        odds = [id[2 * i] for i in range(hln)]
        evens = [id[(2 * i) + 1] for i in range(hln)]
        checksum = 3 * sum(evens) + sum(odds)
        checksum = 10 - (checksum % 10)
        return str(checksum % 10)

    def __init__(self, id):
        """Create and store the code, given as a string of [0-9]digits
        """
        id_len = EAN13Data.length
        id = str(id).zfill(id_len - 1)
        self.id = id
        # if not present, compute checksum, if present, check it :)
        cs = self._compute_checksum() # reads self.id
        l = len(id)
        if l < id_len:
            self.id += cs
        elif id[-1:] != cs:
            raise ValueError('Wrong length or checksum !')
        # not all wrong cases are handled, we'e all consenting adults here
        self.checksum = cs
        self._encode() # reads self.id

    def __repr__(self):
        return "EAN13:{}\n{}".format(self.id_dashed, self.code)

    @property
    def id_dashed(self):
        """for clarity, return id with dashes
        """
        id = self.id
        return "{}-{}-{}".format(id[0], id[1:7], id[7:13])

    @property
    def code_dashed(self):
        """for clarity, return code with dashes between each elements
        """
        return '-'.join(self.elements)

    def draw(self, filename=None):
        """export a pyplot version of the code :)
        pick your extension with `filename`, or it'll be the
        <code-id>.pdf by default.
        """

        full_size = EAN13Data.full_size
        # then, *relative* dimensions according to pyplot logic
        code_size = EAN13Data.code_size / full_size
        elts_size = EAN13Data.elts_size / full_size
        elt_size = EAN13Data.elt_size / full_size
        label_size = EAN13Data.label_size / full_size
        guard_size = EAN13Data.guard_size / full_size
        before_white = EAN13Data.before_white / full_size.w
        after_white = EAN13Data.after_white / full_size.w
        shift = EAN13Data.shift / full_size.w
        # open new blank figure
        fig, ax = plt.subplots()
        # watch out! the final .svg file size will be *rounded* pts
        # so yeah, we'll basically get a small size error on the overall
        # file size -_-"
        fig.set_size_inches(full_size / XY.inch)
        plt.axis('off')
        # read code and prepare all bars :)
        # draw one full-code-range series of small bars (guards included)
        # then superimpose taller guards bars :P
        x = before_white + shift
        bar_width = elt_size.w
        # iterate over grouped successive identical bits
        g = ((i, sum(1 for _ in it)) for i, it in groupby(self.code))
        # on the way, check whether we stand on a guard on not:
        def guards(g):
            seq = zip((list(elt) for elt in self.elements), self.structure)
            elt, typ = next(seq)
            for bit, number in g:
                for _ in range(number):
                    try:
                        elt.pop(0)
                    except IndexError:
                        elt, typ = next(seq)
                        elt.pop(0)
                yield bit, number, typ
        for bit, number, typ in guards(g):
            width = bar_width * number
            if typ in EAN13Data.guards:
                height = guard_size.h
                y = code_size.h - guard_size.h
            else:
                height = elts_size.h
                y = code_size.h - elts_size.h
            color = 'white' if bit == EAN13Data.white else 'black'
            bar = mpatches.Rectangle(XY(x, y), width, height,
                    ec=None, fc=color)
            ax.add_patch(bar)
            x += width
        # add label, splat into several parts.. we need them now because one
        shrink = .73 # shrink size coeff so that numbers do not crush ceiling
        spacing = .0079 # horizontal spacing of digits as a `height` factor
        first, second, third = self.id_dashed.split('-')
        height = label_size.h * full_size.h * shrink / XY.pt
        # center between elements and the floor
        y = .5 * (code_size.h - elts_size.h)
        plt.text(before_white, y, first, color='black', size=height,
                verticalalignment='center')
        normal_guard_length = len(EAN13Data.elements['n'])
        x = before_white + shift + normal_guard_length * bar_width
        for digit in second:
            plt.text(x, y, digit, color='black', size=height,
                verticalalignment='center')
            x += height * spacing
        x = before_white + shift + elts_size.w - normal_guard_length*bar_width
        for digit in reversed(third):
            plt.text(x, y, digit, color='black', size=height, ha='right',
                verticalalignment='center')
            x -= height * spacing
        # ah.. there's a kind of `>` at the end..
        last = '>'
        x = before_white + shift + elts_size.w + bar_width
        plt.text(x, y, last, color='black', size=height, ha='left')
        if not filename:
            filename = self.id + '.pdf'
        plt.savefig(filename)
        plt.close()

    @staticmethod
    def generate(prefix, database=()):
        """Return a random barcode with the given prefix (string of
        digits). It is guaranteed NOT to be identical to one in the
        given database (an iterable structure yielding barcodes)

        >>> rd.seed(12)
        >>> database = [
        ...     EAN13('753698456218'),
        ...     EAN13('026530148950'),
        ...     EAN13('041259863011'),
        ...     ]
        >>> EAN13.generate('041', database)
        EAN13:0-416123-306149
        10101000110011001010111100110010010011011110101010100001011100101010000110011010111001110100101

        >>> database = [
        ...     EAN13('041259863010'),
        ...     EAN13('041259863011'),
        ...     EAN13('041259863012'),
        ...     EAN13('041259863013'),
        ...     EAN13('041259863014'),
        ...     EAN13('041259863015'),
        ...     EAN13('041259863016'),
        ...     EAN13('041259863017'),
        ...     EAN13('041259863018'),
        ...     EAN13('041259863019'),
        ...     ]
        >>> EAN13.generate('04125986301', database)
        Traceback (most recent call last):
            ...
        Exception: Database is full!
        """

        pl = len(prefix)
        # retrieve only ids with no checksums
        database = [ean.id[pl:-1] for ean in database if ean.id[:pl] == prefix]

        # number of digits to draw
        to_draw = EAN13Data.length - 1 - pl
        rand = ''.join(str(i) for i in rd.randint(10, size=to_draw))
        # Check against the database. Do not draw another random one if
        # there is a match, just step one code further until the whole
        # loop has been done. If it has, then there is no such free
        # barcode anymore.
        loop = loop_round(rand, '0123456789')
        while rand in database:
            try:
                rand = next(loop)
            except StopIteration as e:
                raise Exception("Database is full!")
        return EAN13(prefix + rand)

    @staticmethod
    def layout(codes, filename):
        """export pdf A4 pages filled with these barcodes, so that they
        can be printed as stickers
        filename will prefix temporary files produced and removed during
        the process, it shouldn't have any extension

        TODO: I guess it's possible achieving this without creating so
        many intermediate files. Try to get rid of them ;)
        """
        # A4
        sheet_size = WH(210., 297.) * XY.mm
        sticker_size = EAN13Data.full_size
        # so how many codes fit on one sheet?
        n_stickers = sheet_size / sticker_size
        n_stickers = np.floor(n_stickers).astype(int)
        stickers_per_sheet = n_stickers.w * n_stickers.h
        # so how many sheets do we need?
        n_sheets = ceil(len(codes) / stickers_per_sheet)
        sheets = [] # store produced .pdf sheets filenames here
        # iterate until they are all consumed
        stickers = iter(codes)
        for n in range(n_sheets):
            panels = [] # according to sc logic
            try:
                for i in range(n_stickers.w):
                    for j in range(n_stickers.h):
                        # export this code as svg temp file
                        code = next(stickers)
                        tpfile = code.id + '.svg'
                        code.draw(tpfile)
                        panels.append(sc.Panel(sc.SVG(tpfile)
                            .scale(1.).move(i * sticker_size.w,
                                            j * sticker_size.h)))
                        # cleanup
                        os.remove(tpfile)
            except StopIteration:
                pass # no more stickers to print
            sheetname = filename + ('-' + str(n + 1) if n_sheets > 1 else '')
            ssvg = sheetname + '.svg'
            spdf = sheetname + '.pdf'
            sc.Figure(sheet_size.w, sheet_size.h, *panels).save(ssvg)
            # convert to .pdf
            renderPDF.drawToFile(svg2rlg(ssvg), spdf)
            # remove .svg file
            os.remove(ssvg)
            # remember this other temp file
            sheets.append(spdf)

        # bring all sheets together into pdf pages
        if n_sheets > 1:
            final = PdfFileWriter()
            for sheet in sheets:
                append_pdf(PdfFileReader(sheet), final)
            final.write(open(filename + '.pdf', 'wb'))
            # so we can now supress them
            while sheets:
                os.remove(sheets.pop())


if __name__ == "main":
    # Sandbox to playaround

    # build a code with additionnal checksum digit
    code = EAN13(978294019961)
    # export pdf
    code.draw()

    # prepare random stickers to be printed
    # TODO: build them directly with no duplicates
    # guard it because it's a bit long and still experimental
    output_many_stickers = False
    if output_many_stickers:
        stickers = [EAN13.generate('041') for _ in range(60)]
        EAN13.layout(stickers, 'stickers')

else:
    # process command line arguments like barcodes to generate
    args = sys.argv[1:]
    # For now, they should all be valid codes
    if args:
        for code in args:
            print("processing {}".format(code))
            code = EAN13(code)
            print("built: {}".format(code))
            print("exporting..")
            code.draw()
            print()
        print("done.".format())
    else:
        print("no codes given. Don't hesitate and provide "
              "12-digits long space-separated strings.")
        print("Example:")
        print("./main.py 123456789123 987654321654")

