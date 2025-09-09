from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Protocol, overload

from narwhals._compliant.typing import (
    CompliantDataFrameT,
    CompliantExprT,
    CompliantFrameT,
    CompliantLazyFrameT,
    CompliantSeriesT_co,
    DepthTrackingExprT,
    EagerExprT,
    EagerImplDataFrameT,
    EagerImplExprT,
    EagerImplSeriesT,
    LazyExprT,
    NativeFrameT,
    NativeFrameT_co,
    NativeSeriesT,
)
from narwhals._expression_parsing import is_expr, is_series
from narwhals._utils import (
    exclude_column_names,
    get_column_names,
    passthrough_column_names,
)
from narwhals.dependencies import is_numpy_array, is_numpy_array_2d

if TYPE_CHECKING:
    from collections.abc import Container, Iterable, Sequence

    from typing_extensions import TypeAlias

    from narwhals._compliant.selectors import CompliantSelectorNamespace
    from narwhals._compliant.when_then import CompliantWhen, EagerImplWhen
    from narwhals._utils import Implementation, Version
    from narwhals.expr import Expr
    from narwhals.series import Series
    from narwhals.typing import (
        ConcatMethod,
        Into1DArray,
        IntoDType,
        IntoSchema,
        NonNestedLiteral,
        _1DArray,
        _2DArray,
    )

    Incomplete: TypeAlias = Any

__all__ = [
    "CompliantNamespace",
    "DepthTrackingNamespace",
    "EagerImplNamespace",
    "LazyNamespace",
]


class CompliantNamespace(Protocol[CompliantFrameT, CompliantExprT]):
    # NOTE: `narwhals`
    _implementation: Implementation
    _version: Version

    @property
    def _expr(self) -> type[CompliantExprT]: ...
    def parse_into_expr(
        self, data: Expr | NonNestedLiteral | Any, /, *, str_as_lit: bool
    ) -> CompliantExprT | NonNestedLiteral:
        if is_expr(data):
            expr = data._to_compliant_expr(self)
            assert isinstance(expr, self._expr)  # noqa: S101
            return expr
        if isinstance(data, str) and not str_as_lit:
            return self.col(data)
        return data

    # NOTE: `polars`
    def all(self) -> CompliantExprT:
        return self._expr.from_column_names(get_column_names, context=self)

    def col(self, *column_names: str) -> CompliantExprT:
        return self._expr.from_column_names(
            passthrough_column_names(column_names), context=self
        )

    def exclude(self, excluded_names: Container[str]) -> CompliantExprT:
        return self._expr.from_column_names(
            partial(exclude_column_names, names=excluded_names), context=self
        )

    def nth(self, *column_indices: int) -> CompliantExprT:
        return self._expr.from_column_indices(*column_indices, context=self)

    def len(self) -> CompliantExprT: ...
    def lit(self, value: NonNestedLiteral, dtype: IntoDType | None) -> CompliantExprT: ...
    def all_horizontal(
        self, *exprs: CompliantExprT, ignore_nulls: bool
    ) -> CompliantExprT: ...
    def any_horizontal(
        self, *exprs: CompliantExprT, ignore_nulls: bool
    ) -> CompliantExprT: ...
    def sum_horizontal(self, *exprs: CompliantExprT) -> CompliantExprT: ...
    def mean_horizontal(self, *exprs: CompliantExprT) -> CompliantExprT: ...
    def min_horizontal(self, *exprs: CompliantExprT) -> CompliantExprT: ...
    def max_horizontal(self, *exprs: CompliantExprT) -> CompliantExprT: ...
    def concat(
        self, items: Iterable[CompliantFrameT], *, how: ConcatMethod
    ) -> CompliantFrameT: ...
    def when(
        self, predicate: CompliantExprT
    ) -> CompliantWhen[CompliantFrameT, Incomplete, CompliantExprT]: ...
    def concat_str(
        self, *exprs: CompliantExprT, separator: str, ignore_nulls: bool
    ) -> CompliantExprT: ...
    @property
    def selectors(self) -> CompliantSelectorNamespace[Any, Any]: ...
    def coalesce(self, *exprs: CompliantExprT) -> CompliantExprT: ...


class DepthTrackingNamespace(
    CompliantNamespace[CompliantFrameT, DepthTrackingExprT],
    Protocol[CompliantFrameT, DepthTrackingExprT],
):
    def all(self) -> DepthTrackingExprT:
        return self._expr.from_column_names(
            get_column_names, function_name="all", context=self
        )

    def col(self, *column_names: str) -> DepthTrackingExprT:
        return self._expr.from_column_names(
            passthrough_column_names(column_names), function_name="col", context=self
        )

    def exclude(self, excluded_names: Container[str]) -> DepthTrackingExprT:
        return self._expr.from_column_names(
            partial(exclude_column_names, names=excluded_names),
            function_name="exclude",
            context=self,
        )


class LazyNamespace(
    CompliantNamespace[CompliantLazyFrameT, LazyExprT],
    Protocol[CompliantLazyFrameT, LazyExprT, NativeFrameT_co],
):
    @property
    def _backend_version(self) -> tuple[int, ...]:
        return self._implementation._backend_version()

    @property
    def _lazyframe(self) -> type[CompliantLazyFrameT]: ...

    def from_native(self, data: NativeFrameT_co | Any, /) -> CompliantLazyFrameT:
        if self._lazyframe._is_native(data):
            return self._lazyframe.from_native(data, context=self)
        msg = f"Unsupported type: {type(data).__name__!r}"  # pragma: no cover
        raise TypeError(msg)


class EagerNamespace(
    CompliantNamespace[CompliantDataFrameT, EagerExprT],
    Protocol[CompliantDataFrameT, CompliantSeriesT_co, EagerExprT],
):
    @property
    def _dataframe(self) -> type[CompliantDataFrameT]: ...
    @property
    def _series(self) -> type[CompliantSeriesT_co]: ...
    @overload
    def from_numpy(
        self, data: Into1DArray, /, schema: None = ...
    ) -> CompliantSeriesT_co: ...
    @overload
    def from_numpy(
        self, data: _2DArray, /, schema: IntoSchema | Sequence[str] | None
    ) -> CompliantDataFrameT: ...
    def from_numpy(
        self,
        data: Into1DArray | _2DArray,
        /,
        schema: IntoSchema | Sequence[str] | None = None,
    ) -> CompliantDataFrameT | CompliantSeriesT_co:
        if is_numpy_array_2d(data):
            return self._dataframe.from_numpy(data, schema=schema, context=self)
        return self._series.from_numpy(data, context=self)


class EagerImplNamespace(
    EagerNamespace[EagerImplDataFrameT, EagerImplSeriesT, EagerImplExprT],
    DepthTrackingNamespace[EagerImplDataFrameT, EagerImplExprT],
    Protocol[
        EagerImplDataFrameT, EagerImplSeriesT, EagerImplExprT, NativeFrameT, NativeSeriesT
    ],
):
    @property
    def _backend_version(self) -> tuple[int, ...]:
        return self._implementation._backend_version()

    def when(
        self, predicate: EagerImplExprT
    ) -> EagerImplWhen[
        EagerImplDataFrameT, EagerImplSeriesT, EagerImplExprT, NativeSeriesT
    ]: ...

    @overload
    def from_native(self, data: NativeFrameT, /) -> EagerImplDataFrameT: ...
    @overload
    def from_native(self, data: NativeSeriesT, /) -> EagerImplSeriesT: ...
    def from_native(
        self, data: NativeFrameT | NativeSeriesT | Any, /
    ) -> EagerImplDataFrameT | EagerImplSeriesT:
        if self._dataframe._is_native(data):
            return self._dataframe.from_native(data, context=self)
        if self._series._is_native(data):
            return self._series.from_native(data, context=self)
        msg = f"Unsupported type: {type(data).__name__!r}"
        raise TypeError(msg)

    def parse_into_expr(
        self,
        data: Expr | Series[NativeSeriesT] | _1DArray | NonNestedLiteral,
        /,
        *,
        str_as_lit: bool,
    ) -> EagerImplExprT | NonNestedLiteral:
        if not (is_series(data) or is_numpy_array(data)):
            return super().parse_into_expr(data, str_as_lit=str_as_lit)
        return self._expr._from_series(
            data._compliant_series
            if is_series(data)
            else self._series.from_numpy(data, context=self)
        )

    def _concat_diagonal(self, dfs: Sequence[NativeFrameT], /) -> NativeFrameT: ...
    def _concat_horizontal(
        self, dfs: Sequence[NativeFrameT | Any], /
    ) -> NativeFrameT: ...
    def _concat_vertical(self, dfs: Sequence[NativeFrameT], /) -> NativeFrameT: ...
    def concat(
        self, items: Iterable[EagerImplDataFrameT], *, how: ConcatMethod
    ) -> EagerImplDataFrameT:
        dfs = [item.native for item in items]
        if how == "horizontal":
            native = self._concat_horizontal(dfs)
        elif how == "vertical":
            native = self._concat_vertical(dfs)
        elif how == "diagonal":
            native = self._concat_diagonal(dfs)
        else:  # pragma: no cover
            raise NotImplementedError
        return self._dataframe.from_native(native, context=self)
