"""Start developping here as in a sandbox.
Let's first use pseudo-"binary" codes stored and manipulated as python
strings for simplicity.
"""

# to subclass `str` in a lazy way
# https://stackoverflow.com/questions/46868085/
from collections import UserString

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


class EAN13(object):
    """Embed EAN13 code concept.. still a sandbox.
    'id': stands for the numeric [0-9]digits value of the code
    'code': stands for its binary "bars" value [0-1]digits values

    >>> c = EAN13(978294019961)
    >>> c.checksum
    '7'
    >>> c = EAN13(9782940199617) # allright if you already know it.
    >>> c
    EAN13:9-782940-199617
    10101110110001001001101100010110011101000110101010110011011101001110100101000011001101000100101
    >>> c.code_dashed
    '101-0111011-0001001-0011011-0001011-0011101-0001101-01010-1100110-1110100-1110100-1010000-1100110-1000100-101'
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
        return str(checksum)

    def __init__(self, id):
        """Create and store the code, given as an int
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

