from __future__ import (
    absolute_import,
    unicode_literals,
)

import decimal

import attr
import six

from conformity.error import (
    ERROR_CODE_UNKNOWN,
    Error,
)
from conformity.utils import strip_none


@attr.s
class Base(object):
    """
    Base field type.
    """

    def errors(self, value):
        """
        Returns a list of errors with the value. An empty/None return means
        that it's valid.
        """
        return [
            Error('Validation not implemented on base type'),
        ]

    def introspect(self):
        raise NotImplementedError('You must override introspect() in a subclass')


class Constant(Base):
    """
    Value that must match exactly. You can pass a series of options
    and any will be accepted.
    """

    introspect_type = 'constant'

    def __init__(self, *args, **kwargs):
        self.values = set(args)
        if not self.values:
            raise TypeError('You must provide at least one constant value')
        self.description = kwargs.get('description', None)
        # Check they didn't pass any other kwargs
        if list(kwargs.keys()) not in ([], ['description']):
            raise TypeError('Invalid keyword arguments for Constant: {}'.format(kwargs.keys()))

        def _repr(cv):
            return '"{}"'.format(cv) if isinstance(cv, six.string_types) else '{}'.format(cv)

        if len(self.values) == 1:
            self._error_message = 'Value is not {}'.format(_repr(tuple(self.values)[0]))
        else:
            self._error_message = 'Value is not one of: {}'.format(', '.join(sorted(_repr(v) for v in self.values)))

    def errors(self, value):
        """
        Returns a list of errors with the value. An empty/None return means
        that it's valid.
        """
        if value not in self.values:
            return [Error(self._error_message, code=ERROR_CODE_UNKNOWN)]
        return []

    def introspect(self):
        result = {
            'type': self.introspect_type,
            'values': list(self.values),
        }
        if self.description is not None:
            result['description'] = self.description
        return result


@attr.s
class Anything(Base):
    """
    Accepts any value.
    """

    introspect_type = 'anything'
    description = attr.ib(default=None)

    def errors(self, value):
        pass

    def introspect(self):
        return strip_none({
            'type': self.introspect_type,
            'description': self.description,
        })


@attr.s
class Hashable(Anything):
    """
    Accepts any hashable value
    """

    introspect_type = 'hashable'

    def errors(self, value):
        try:
            hash(value)
        except TypeError:
            return [
                Error('Value is not hashable'),
            ]

    def introspect(self):
        return strip_none({
            'type': self.introspect_type,
            'description': self.description,
        })


@attr.s
class Boolean(Base):
    """
    Accepts boolean values only
    """

    introspect_type = 'boolean'

    description = attr.ib(default=None)

    def errors(self, value):
        if not isinstance(value, bool):
            return [
                Error('Not a boolean'),
            ]

    def introspect(self):
        return strip_none({
            'type': self.introspect_type,
            'description': self.description,
        })


@attr.s
class Integer(Base):
    """
    Accepts valid integers, with optional range limits.
    """

    valid_type = six.integer_types
    valid_noun = 'an integer'
    introspect_type = 'integer'

    gt = attr.ib(default=None)
    gte = attr.ib(default=None)
    lt = attr.ib(default=None)
    lte = attr.ib(default=None)
    description = attr.ib(default=None)

    def errors(self, value):
        if not isinstance(value, self.valid_type) or isinstance(value, bool):
            return [
                Error('Not %s' % self.valid_noun),
            ]
        elif self.gt is not None and value <= self.gt:
            return [
                Error('Value not > %s' % self.gt),
            ]
        elif self.lt is not None and value >= self.lt:
            return [
                Error('Value not < %s' % self.lt),
            ]
        elif self.gte is not None and value < self.gte:
            return [
                Error('Value not >= %s' % self.gte),
            ]
        elif self.lte is not None and value > self.lte:
            return [
                Error('Value not <= %s' % self.lte),
            ]

    def introspect(self):
        return strip_none({
            'type': self.introspect_type,
            'description': self.description,
            'gt': self.gt,
            'gte': self.gte,
            'lt': self.lt,
            'lte': self.lte,
        })


@attr.s
class Float(Integer):
    """
    Accepts floating point numbers as well as integers.
    """

    valid_type = six.integer_types + (float,)
    valid_noun = 'a float'
    introspect_type = 'float'


@attr.s
class Decimal(Integer):
    """
    Accepts arbitrary-precision Decimal number objects.
    """

    valid_type = decimal.Decimal
    valid_noun = 'a decimal'
    introspect_type = 'decimal'


@attr.s
class UnicodeString(Base):
    """
    Accepts only unicode strings
    """

    valid_type = six.text_type
    valid_noun = 'unicode string'
    introspect_type = 'unicode'

    min_length = attr.ib(default=None)
    max_length = attr.ib(default=None)
    description = attr.ib(default=None)
    allow_blank = attr.ib(default=True, type=bool)

    def errors(self, value):
        if not isinstance(value, self.valid_type):
            return [
                Error('Not a %s' % self.valid_noun),
            ]
        elif self.min_length is not None and len(value) < self.min_length:
            return [
                Error('String must have a length of at least %s' % self.min_length),
            ]
        elif self.max_length is not None and len(value) > self.max_length:
            return [
                Error('String must have a length no more than %s' % self.max_length),
            ]
        elif not (self.allow_blank or value.strip()):
            return [
                Error('String cannot be blank'),
            ]

    def introspect(self):
        return strip_none({
            'type': self.introspect_type,
            'description': self.description,
            'min_length': self.min_length,
            'max_length': self.max_length,
            'allow_blank': self.allow_blank and None,  # if the default True, hide it from introspection
        })


@attr.s
class ByteString(UnicodeString):
    """
    Accepts only byte strings
    """

    valid_type = six.binary_type
    valid_noun = 'byte string'
    introspect_type = 'bytes'


@attr.s
class UnicodeDecimal(Base):
    """
    A decimal value represented as its base-10 unicode string.
    """

    introspect_type = 'unicode_decimal'
    description = attr.ib(default=None)

    def errors(self, value):
        if not isinstance(value, six.text_type):
            return [
                Error('Invalid decimal value (not unicode string)'),
            ]
        try:
            decimal.Decimal(value)
        except decimal.InvalidOperation:
            return [
                Error('Invalid decimal value (parse error)'),
            ]
        return []

    def introspect(self):
        return strip_none({
            'type': self.introspect_type,
            'description': self.description,
        })
