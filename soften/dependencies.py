import attr

@attr.s
class Dependency(object):
    name = attr.ib()
    version = attr.ib()
    operator = attr.ib(default='~=')

    def __str__(self):
        return ''.join((self.name, self.operator, self.version))


@attr.s
class Dependencies(object):
    dependencies = attr.ib()

    @classmethod
    def from_pairs(cls, pairs):
        deps = []
        for name, version in pairs:
            deps.append(Dependency(name, version))
        return cls(deps)

    def format_requirements(self):
        return '\n'.join((str(dep) for dep in self.dependencies))
