Okay, since we're not satisfied with what we find around, let's just have fun
and implement another barcode generator in python. This TODO list starts with
the roadmap and the intent:

## roadmap

- start with a plain python API
    - convert numbers to EAN13 valid, binary codes
    - export EAN13 binary codes to nice representations (ascii, svg, pdf, maybe
      more)
    - generate random codes with or without constraints (ex: prefixes, don't
      match any in an existing database)
- export that API to a command line interface

#### further off

- add support for additionnal numbers and variable weights
- add support for EAN8, EAN128, maybe 2D codes *etc.*

