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


class EAN13(object):
    """For now, just hold static information about EAN13 encoding.
    Read:
    https://fr.wikipedia.org/wiki/Code-barres_EAN
    https://en.wikipedia.org/wiki/International_Article_Number
    """

    white = Code('0')
    black = Code('1')

    # "elements" of encoding, alternance of lengths
    A_lengths = { 0: '3211',
          1: '2221',
          2: '2122',
          3: '1411',
          4: '1132',
          5: '1231',
          6: '1114',
          7: '1312',
          8: '1213',
          9: '3112',
          'first': white, # color of first bar
        }
    C_lengths = A_lengths.copy()
    C_lengths['first'] = black
    B_lengths = {
            0: '1123',
            1: '1222',
            2: '2212',
            3: '1141',
            4: '2311',
            5: '1321',
            6: '4111',
            7: '2131',
            8: '3121',
            9: '2113',
            'first': white, # color of first bar
            }
    guards = {'normal': Code('101'),
              'central': Code('01010')}

    def _lengths_to_code(dico):
        """Convert one above dictionnary of lengths to an actual
        dictionnary of code
        """
        res = {}
        color = dico.pop('first')
        for i, lens in dico.items():
            seq = []
            for l in lens:
                seq.append(color * int(l))
                color = color.flip
            res[i] = sum(seq)
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
            0: 'AAAAAA',
            1: 'AABABB',
            2: 'AABBAB',
            3: 'AABBBA',
            4: 'ABAABB',
            5: 'ABBAAB',
            6: 'ABBBAA',
            7: 'ABABAB',
            8: 'ABABBA',
            9: 'ABBABA',
            }
    structure = {i: 'n{}cCCCCCCn'.format(v) for i, v in structure.items()}

