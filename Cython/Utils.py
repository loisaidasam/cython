#
#   Cython -- Things that don't belong
#            anywhere else in particular
#

import os, sys, re, codecs

def replace_suffix(path, newsuf):
    base, _ = os.path.splitext(path)
    return base + newsuf

def open_new_file(path):
    #  Open and truncate existing file to
    #  preserve metadata on the Mac.
    return open(path, "w+")

def castrate_file(path, st):
    #  Remove junk contents from an output file after a
    #  failed compilation, but preserve metadata on Mac.
    #  Also sets access and modification times back to
    #  those specified by st (a stat struct).
    try:
        f = open(path, "r+")
    except EnvironmentError:
        pass
    else:
        f.seek(0, 0)
        f.truncate()
        f.write(
            "#error Do not use this file, it is the result of a failed Cython compilation.\n")
        f.close()
        if st:
            os.utime(path, (st.st_atime, st.st_mtime-1))

def modification_time(path):
    st = os.stat(path)
    return st.st_mtime

def file_newer_than(path, time):
    ftime = modification_time(path)
    return ftime > time

# support for source file encoding detection and unicode decoding

def encode_filename(filename):
    if isinstance(filename, unicode):
        return filename
    try:
        filename_encoding = sys.getfilesystemencoding()
        if filename_encoding is None:
            filename_encoding = sys.getdefaultencoding()
        filename = filename.decode(filename_encoding)
    except UnicodeDecodeError:
        pass
    return filename

_match_file_encoding = re.compile(u"coding[:=]\s*([-\w.]+)").search

def detect_file_encoding(source_filename):
    # PEPs 263 and 3120
    f = codecs.open(source_filename, "rU", encoding="UTF-8")
    try:
        chars = []
        for i in range(2):
            c = f.read(1)
            while c and c != u'\n':
                chars.append(c)
                c = f.read(1)
            encoding = _match_file_encoding(u''.join(chars))
            if encoding:
                return encoding.group(1)
    finally:
        f.close()
    return "UTF-8"

def open_source_file(source_filename, mode="rU"):
    encoding = detect_file_encoding(source_filename)
    return codecs.open(source_filename, mode=mode, encoding=encoding)

class EncodedString(unicode):
    # unicode string subclass to keep track of the original encoding.
    # 'encoding' is None for unicode strings and the source encoding
    # otherwise
    encoding = None

    def byteencode(self):
        assert self.encoding is not None
        return self.encode(self.encoding)

    def utf8encode(self):
        assert self.encoding is None
        return self.encode("UTF-8")

    def is_unicode(self):
        return self.encoding is None
    is_unicode = property(is_unicode)

#    def __eq__(self, other):
#        return unicode.__eq__(self, other) and \
#            getattr(other, 'encoding', '') == self.encoding

char_from_escape_sequence = {
    r'\a' : '\a',
    r'\b' : '\b',
    r'\f' : '\f',
    r'\n' : '\n',
    r'\r' : '\r',
    r'\t' : '\t',
    r'\v' : '\v',
    }.get

def _to_escape_sequence(s):
    if s in '\n\r\t':
        return repr(s)[1:-1]
    elif s == '"':
        return r'\"'
    else:
        # oct passes much better than hex
        return ''.join(['\\%03o' % ord(c) for c in s])

_c_special = ('\0', '\n', '\r', '\t', '??', '"')
_c_special_replacements = zip(_c_special, map(_to_escape_sequence, _c_special))

def _build_specials_test():
    subexps = []
    for special in _c_special:
        regexp = ''.join(['[%s]' % c for c in special])
        subexps.append(regexp)
    return re.compile('|'.join(subexps)).search

_has_specials = _build_specials_test()

def escape_byte_string(s):
    s = s.replace('\\', '\\\\')
    if _has_specials(s):
        for special, replacement in _c_special_replacements:
            s = s.replace(special, replacement)
    try:
        s.decode("ASCII")
        return s
    except UnicodeDecodeError:
        pass
    l = []
    append = l.append
    for c in s:
        o = ord(c)
        if o >= 128:
            append('\\%3o' % o)
        else:
            append(c)
    return ''.join(l)

def long_literal(value):
    if isinstance(value, basestring):
        if len(value) < 2:
            value = int(value)
        elif value[0] == 0:
            value = int(value, 8)
        elif value[1] in 'xX':
            value = int(value[2:], 16)
        else:
            value = int(value)
    return not -2**31 <= value < 2**31
