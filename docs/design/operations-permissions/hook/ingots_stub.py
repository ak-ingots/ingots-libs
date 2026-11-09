"""
What the prototype needs of ingots, cut down: the flags and the masks as
they are; the operation, the checker and the runner as 0.33 would make them.
"""

import abc
import enum
import inspect
import typing as t
from collections.abc import Iterator, Mapping


class PermissionFlags(enum.IntFlag, boundary=enum.KEEP):
    DOMAIN: t.ClassVar[str]

    @classmethod
    def __init_subclass__(cls, *, domain: str, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.DOMAIN = domain


class Permissions(Mapping[str, int]):
    def __init__(self, *items: "PermissionFlags | Mapping[str, int]") -> None:
        masks: dict[str, int] = {}
        for item in items:
            pairs = (
                [(item.DOMAIN, int(item))]
                if isinstance(item, PermissionFlags)
                else item.items()
            )
            for domain, mask in pairs:
                masks[domain] = masks.get(domain, 0) | int(mask)
        self._masks = {domain: mask for domain, mask in masks.items() if mask}

    def __getitem__(self, domain: str) -> int:
        return self._masks[domain]

    def __iter__(self) -> Iterator[str]:
        return iter(self._masks)

    def __len__(self) -> int:
        return len(self._masks)

    def has(self, required: Mapping[str, int]) -> bool:
        return all(
            self._masks.get(domain, 0) & mask == mask
            for domain, mask in required.items()
        )


class Project:
    pass


class BaseOperation[ParametersType, ResultType]:
    """
    The operation of 0.33. What a caller needs is :meth:`get_permissions`:
    the constant :attr:`PERMISSIONS` by default, one instance a process,
    readable from the class; an operation whose permissions depend on the
    project overrides :meth:`_get_permissions`, computed on every run. A
    concrete operation does one or the other, checked when its class is
    created.
    """

    PERMISSIONS: t.ClassVar[Permissions]

    project: Project

    @classmethod
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        overridden = cls._get_permissions is not BaseOperation._get_permissions
        if not inspect.isabstract(cls) and not overridden:
            try:
                cls.PERMISSIONS
            except AttributeError:
                raise TypeError(
                    f"{cls.__qualname__} declares no PERMISSIONS: "
                    f"Permissions() for none, or _get_permissions()"
                ) from None

    def __init__(self, project: Project) -> None:
        self.project = project

    @t.final
    def get_permissions(self) -> Permissions:
        return self._get_permissions()

    def _get_permissions(self) -> Permissions:
        return self.PERMISSIONS

    @abc.abstractmethod
    async def _run(self, parameters: ParametersType) -> ResultType:
        raise NotImplementedError


class OperationPermissionsError(Exception):
    pass


async def run[ParametersType, ResultType](
    project: Project,
    operation_cls: type[BaseOperation[ParametersType, ResultType]],
    parameters: ParametersType,
    caller: Permissions,
) -> ResultType:
    """The runner: the operation first, then its permissions, then the run."""
    operation = operation_cls(project)
    required = operation.get_permissions()
    if not caller.has(required):
        raise OperationPermissionsError(type(operation).__qualname__, dict(required))
    return await operation._run(parameters)
