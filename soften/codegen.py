import attr
from yapf.yapflib import yapf_api

@attr.s(init=False, slots=True)
class Call(object):
    name = attr.ib()
    args = attr.ib()
    kwargs = attr.ib()

    def __init__(self, *args, **kwargs):
        self.name = args[0]
        self.args = args[1:]
        self.kwargs = kwargs

    def formatted_kwargs(self):
        for key, value in self.kwargs.items():
            yield "{}='{}'".format(key, value)

    def __str__(self):
        all_args = list(self.args) + list(self.formatted_kwargs())
        return '{}({})'.format(self.name, ', '.join(all_args))


@attr.s(slots=True)
class Import(object):
    module = attr.ib()
    items = attr.ib(default=None)

    def __str__(self):
        if self.items:
            items = ', '.join(items)
            return 'from {} import {}'.format(self.module, items)
        else:
            return 'import {}'.format(self.module)


@attr.s(slots=True)
class Module(object):
    contents = attr.ib()
    executable = attr.ib(default=False)

    def __str__(self):
        output = []
        if self.executable:
            output.append('#!/usr/bin/env python')
        output.append('# File autogenerated by soften, do not edit')
        for item in self.contents:
            output.append(str(item))
        return yapf_api.FormatCode('\n\n'.join(output))[0]