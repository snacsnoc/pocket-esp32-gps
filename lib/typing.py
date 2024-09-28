# Expanded version of typing.py from https://github.com/Josverl/micropython-stubs/tree/main/mip
# Copyright (c) 2020-2024 Jos Verlinde


def cast(type, val):
    return val


def get_origin(type):
    return getattr(type, "__origin__", None)


def get_args(type):
    return getattr(type, "__args__", ())


def no_type_check(arg):
    return arg


def overload(func):
    return func


class _AnyCall:
    def __call__(self, *args, **kwargs):
        return self

    def __getitem__(self, item):
        return self


_anyCall = _AnyCall()


class _SubscriptableType:
    def __getitem__(self, item):
        return _anyCall


_Subscriptable = _SubscriptableType()


def TypeVar(name, *constraints, bound=None, covariant=False, contravariant=False):
    return _anyCall


class Any:
    pass


class BinaryIO:
    pass


class ClassVar:
    pass


class Hashable:
    pass


class IO:
    pass


class NoReturn:
    pass


class Sized:
    pass


class SupportsInt:
    pass


class SupportsFloat:
    pass


class SupportsComplex:
    pass


class SupportsBytes:
    pass


class SupportsIndex:
    pass


class SupportsAbs:
    pass


class SupportsRound:
    pass


class TextIO:
    pass


AnyStr = TypeVar("AnyStr", str, bytes)
Text = str
Pattern = _Subscriptable
Match = _Subscriptable


class _TupleType(_SubscriptableType):
    def __getitem__(self, parameters):
        if parameters == ():
            return tuple
        if parameters == Ellipsis:
            return _anyCall
        return super().__getitem__(parameters)


Tuple = _TupleType()

float = float


class _UnionType(_SubscriptableType):
    def __getitem__(self, parameters):
        if not isinstance(parameters, tuple):
            parameters = (parameters,)
        return _anyCall


Union = _UnionType()


def Optional(type):
    return Union[type, type(None)]


class _LiteralType(_SubscriptableType):
    def __getitem__(self, parameters):
        if not isinstance(parameters, tuple):
            parameters = (parameters,)
        return _anyCall


Literal = _LiteralType()


def runtime_checkable(cls):
    return cls


class Protocol:
    pass


class TypeGuard(_SubscriptableType):
    pass


class Annotated(_SubscriptableType):
    pass


class Final(_SubscriptableType):
    pass


class Required(_SubscriptableType):
    pass


class NotRequired(_SubscriptableType):
    pass


def TypedDict(name, fields, total=True):
    return dict


def NewType(name, tp):
    def new_type(x):
        return x

    new_type.__name__ = name
    new_type.__supertype__ = tp
    return new_type


AbstractSet = _Subscriptable
AsyncContextManager = _Subscriptable
AsyncGenerator = _Subscriptable
AsyncIterable = _Subscriptable
AsyncIterator = _Subscriptable
Awaitable = _Subscriptable
Callable = _Subscriptable
ChainMap = _Subscriptable
Collection = _Subscriptable
Container = _Subscriptable
ContextManager = _Subscriptable
Coroutine = _Subscriptable
Counter = _Subscriptable
DefaultDict = _Subscriptable
Deque = _Subscriptable
Dict = _Subscriptable
FrozenSet = _Subscriptable
Generator = _Subscriptable
Generic = _Subscriptable
Iterable = _Subscriptable
Iterator = _Subscriptable
List = _Subscriptable
Mapping = _Subscriptable
MutableMapping = _Subscriptable
MutableSequence = _Subscriptable
MutableSet = _Subscriptable
NamedTuple = _Subscriptable
OrderedDict = _Subscriptable
Sequence = _Subscriptable
Set = _Subscriptable
Type = _Subscriptable

TYPE_CHECKING = False


def is_typeddict(tp):
    return isinstance(tp, type) and issubclass(tp, dict)


def get_type_hints(obj, globalns=None, localns=None):
    return getattr(obj, "__annotations__", {})


ForwardRef = _AnyCall
