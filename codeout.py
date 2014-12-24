#
# codeout.py
#
# Copyright (c) 2014 Matthew Brush <mbrush@codebrainz.ca>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

'''
Code and text output utilities.

The ``CodeOut`` class provides a simple and convenient way to write code
and similar text to a string in stream-like manner. ``CodeOut`` uses the
standard ``io.StringIO`` object as the buffer. It provides convenient state
needed when doing typical code generation tasks.

To give a real example, imagine you were using the "visitor" pattern
to generate some C-like source code from a tree of nodes representing the
abstract syntax tree, you might have something like the following example
for a "Function" node visit handler. Of note is the use of ``self.cout`` ::

    class CodePrinter(some.VisitorIface):
        ...
        def __init__(self, filename, ...):
            self.cout = CodeOut(filename, indent='  ')
        ...
        def line_directive(self, location=None):
            if location is None:
                return '#line %d "%s"\n' % (self.cout.line, self.cout.file)
            else:
                return '#line %d "%s"\n' % (location.line, location.file)
        ...
        def visit_Function(self, node):
            self.cout.write(self.line_directive(node.location))
            self.cout.iwrite('')
            node.datatype.accept(self) # visit the return type to print it
            self.cout.write(' ' + node.name + '(')
            if len(node.params):
                lastparam = node.params[-1]
                for param in node.params:
                    param.accept(self)
                    self.cout.write(', ' if param is not lastparam else '')
            self.cout.write(')\\n')
            self.cout.write(self.line_directive())
            self.cout.lwrite('{')
            if len(node.stmts) > 0:
                self.cout.indent()
                for stmt in node.stmts:
                    stmt.accept(self)
                self.cout.unindent()
                self.cout.lwrite('}')
            else:
                self.cout.write('}\\n')
        ...

The above example might hypothetically print out something like this for
a simple ``add`` function ::

    #line 123 "somefile.abc"
    int add(int a, int b)
    #line 3 "thisfile.c"
    {
      return (a + b);
    }

Refer to the documentation of the ``CodeOut`` class for more information
and examples.
'''

__all__ = [ "CodeOut" ]

import io

class CodeOut(io.StringIO):

    '''
    Provides a simple interface for outputting code to a string.
    It handles indentation of the output and keeps track of position
    information.

    The methods for output are ``write()`` for normal output, ``iwrite()``
    for indented output, and ``lwrite()`` for writing an indented line
    (with the newline character). To control indentation use ``indent()``
    to increase one indentaton level paired with ``unindent()`` to
    decrease back one level of indentation.

    The output string can be retrieved using the ``contents`` property.
    The current output position is stored in ``line``, ``column`` and
    ``offset`` properties.

    Here's a simple example ::

        >>> from codeout import CodeOut
        >>> out = CodeOut(tab='  ')
        >>> out.lwrite('<foo>')
        ... # doctest: +ELLIPSIS
        <codeout.CodeOut object at ...>
        >>> out.indent()
        ... # doctest: +ELLIPSIS
        <codeout.CodeOut object at ...>
        >>> out.lwrite('<bar/>')
        ... # doctest: +ELLIPSIS
        <codeout.CodeOut object at ...>
        >>> out.unindent()
        ... # doctest: +ELLIPSIS
        <codeout.CodeOut object at ...>
        >>> out.lwrite('</foo>')
        ... # doctest: +ELLIPSIS
        <codeout.CodeOut object at ...>
        >>> out.contents
        '<foo>\\n  <bar/>\\n</foo>\\n'
        >>> out.line, out.column, out.offset
        (3, 0, 22)

    If you're into chaining lots of function calls together, as can be
    seen above, most of the output functions return ``self`` so you can
    make multiple calls in sequence, like this ::

        >>> CodeOut(tab='  ').lwrite('<foo>').indent().lwrite('<bar/>').unindent().lwrite('</foo>').contents
        '<foo>\\n  <bar/>\\n</foo>\\n'

    The class also provides a few useful operator overloads, for example ::

        >>> co = CodeOut()
        >>> co += 'a'
        >>> co == 'a'
        True
        >>> co != 'a'
        False
        >>> co += 'b'
        >>> co == 'ab'
        True
        >>> str(co)
        'ab'
        >>> co[0]
        'a'
        >>> co[1]
        'b'

    Additionally, since ``CodeOut`` subclasses ``io.StringIO`` it provides
    most of the file-like methods, for example ::

        >>> co = CodeOut()
        >>> co.write('12')
        ... # doctest: +ELLIPSIS
        <codeout.CodeOut object at ...>
        >>> co.tell()
        2
        >>> co.seek(0)
        0
        >>> co.write('a')
        ... # doctest: +ELLIPSIS
        <codeout.CodeOut object at ...>
        >>> str(co)
        'a2'
        >>> co.close()

    '''

    def __init__(self, fn='<string>', init='', tab='\t'):
        '''
        Initialize the instance with the given arguments. The ``fn`` argument
        should be a filename that represents the output stream, or else
        something like ``<stream>`` or ``<string>>``. The ``init`` argument
        is written to the output after it's initialized. The ``tab`` argument
        specifies the string which is multiplied by the indentation level
        top obtain the current indentation string.
        '''
        super().__init__()
        self._fn = fn
        self._tab = tab
        self._ind = ''
        self._level = self._line = self._col = self._off = 0
        if init:
            self.write(init)

    #
    # Internal methods
    #

    def _update_indent(self):
        self._ind = self._tab * self._level

    #
    # Indentation control
    #

    def indent(self):
        ' Increase output indentation by one level. '
        self._level += 1
        self._update_indent()
        return self

    def unindent(self):
        ' Decrease output indentation by one level. '
        self._level -= 1
        assert(self._level >= 0)
        self._update_indent()
        return self

    def dedent(self):
        ' Alias of ``unindent()``. '
        return self.unindent()

    def outdent(self):
        ' Alias of ``unindent()``. '
        return self.unindent()

    #
    # Output methods
    #

    def format(self, fmt, *args, **kwargs):
        '''
        Format a string using ``fmt`` with the given ``args`` and/or
        ``kwargs`` and write it to the output.
        '''
        text = fmt.format(*args, **kwargs)
        return self.write(text)

    def write(self, text):
        ' Write ``text`` to the output without any special treatment. '
        for i, ch in enumerate(text):
            if ch == '\n':
                self._line += 1
                self._col = 0
            else:
                self._col += 1
            self._off += 1
        super().write(text)
        return self

    def iwrite(self, text):
        ' Write ``text`` to the output, with leading indentation prepended. '
        return self.write(self._ind + text)

    def write_indented(self, text):
        ' Alias of ``iwrite()``. '
        return self.iwrite(text)

    def lwrite(self, text=''):
        '''
        Write ``text`` to the output, with leading indentation prepended and
        a a single newline appended. With no arguments it will just add
        a newline (same as ``newline()``).
        '''
        if not text:
            return self.write('\n')
        else:
            return self.iwrite(text + '\n')

    def write_line(self, text=''):
        ' Alias of ``lwrite()``. '
        return self.lwrite(text)

    def newline(self):
        ' Add a new line to the output. '
        return self.lwrite()

    def writelines(self, seq):
        ' Write each item of the given sequence as a string on a new line. '
        for item in seq:
            self.write_line(str(item))

    #
    # Properties
    #

    @property
    def filename(self):
        ' The filename that represents the output. '
        return self._fn
    @filename.setter
    def filename(self, value):
        self._fn = value

    @property
    def contents(self):
        ' The string contents of the output. '
        return self.getvalue()

    @property
    def tab(self):
        '''
        The string used for indentation which is multiplied by the ``level``.
        Usually it's a ``\\t`` (tab) character or some number of space
        characters.
        '''
        return self._tab
    @tab.setter
    def tab(self, value):
        self._tab = value
        self._update_indent()

    @property
    def level(self):
        ' The current indentation level. '
        return self._level
    @level.setter
    def level(self, value):
        self._level = value
        self._update_indent()

    @property
    def indentation(self):
        ' The current indentation string. '
        return self._ind

    @property
    def line(self):
        ' The number of new line characters output so far. '
        return self._line
    @property
    def column(self):
        ' The number of characters since the last new line was output. '
        return self._col
    @property
    def offset(self):
        ' The number of character written since the start of output. '
        return self._off

    #
    # Operator overloads
    #

    def __iadd__(self, rhs):
        return self.__iconcat__(rhs)

    def __iconcat__(self, rhs):
        self.write(rhs if isinstance(rhs, str) else str(rhs))
        return self

    def __str__(self):
        return self.contents

    def __eq__(self, s):
        return (self.contents == s)

    def __ne__(self, s):
        return (self.contents != s)

    def __getitem__(self, i):
        return self.contents[i]

#
# Test code when run from command-line
#

if __name__ == "__main__":
    import doctest
    doctest.testmod()
