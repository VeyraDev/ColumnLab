from __future__ import annotations

import time
from typing import Any

from app.engine.codecs.base import EncodedBlock, PredicateEq, PredicateIn, PredicateRange
from app.engine.codecs.dictionary import DictionaryCodec
from app.engine.codecs.raw import RawCodec
from app.engine.codecs.rle import RleCodec
from app.engine.execution.context import ExecutionContext, OperatorMetric
from app.engine.execution.predicate_eval import predicate_dict_to_codec
from app.engine.types import Encoding
from app.engine.vectors import NullBitmap, SelectionVector

CODEC_BY_ENCODING = {
    Encoding.RAW: RawCodec,
    Encoding.RLE: RleCodec,
    Encoding.DICTIONARY: DictionaryCodec,
}


def apply_filter(
    ctx: ExecutionContext,
    block: EncodedBlock,
    predicate: object,
    *,
    operator_id: str,
    operator_type: str,
) -> SelectionVector:
    ctx.check_cancel()
    start = time.perf_counter_ns()
    pred = _normalize_predicate(predicate, block)
    codec = CODEC_BY_ENCODING[block.encoding]
    result = codec.filter(block, pred)
    if isinstance(result, SelectionVector):
        ctx.metrics.compressed_operator_blocks += 1
    else:
        decoded = codec.decode(block)
        ctx.metrics.decoded_blocks += 1
        result = _filter_decoded(decoded.values, pred, block)
    elapsed = time.perf_counter_ns() - start
    out_rows = result.selected_count()
    ctx.metrics.rows_examined += result.length
    ctx.metrics.operators.append(
        OperatorMetric(
            operator_id=operator_id,
            operator_type=operator_type,
            input_rows=result.length,
            output_rows=out_rows,
            elapsed_ns=elapsed,
        )
    )
    return result


def filter_from_dict(
    ctx: ExecutionContext,
    block: EncodedBlock,
    pred_dict: dict[str, Any],
    *,
    operator_id: str,
    operator_type: str,
) -> SelectionVector:
    pred = predicate_dict_to_codec(pred_dict)
    if pred is None:
        nulls, _ = NullBitmap.deserialize(block.payload)
        return SelectionVector.all_true(nulls.length)
    return apply_filter(ctx, block, pred, operator_id=operator_id, operator_type=operator_type)


def _normalize_predicate(predicate: object, block: EncodedBlock) -> object:
    if isinstance(predicate, tuple):
        tag = predicate[0]
        if tag == "not_eq":
            return ("not", PredicateEq(value=predicate[1]))
        if tag == "not_in":
            return ("not", PredicateIn(values=predicate[1]))
        if tag == "not_range":
            return ("not", predicate[1])
        if tag == "is_null":
            return predicate
        if tag == "not":
            return predicate
    return predicate


def _filter_decoded(values: tuple[Any, ...], predicate: object, block: EncodedBlock) -> SelectionVector:
    from app.engine.execution.predicate_eval import expr_to_codec_predicate
    from app.engine.vectors import canonical_key, sort_key, values_equal

    lt = block.logical_type
    bits: list[bool] = []
    pred = predicate
    if isinstance(pred, tuple) and pred[0] == "is_null":
        negated = pred[1]
        nulls, _ = NullBitmap.deserialize(block.payload)
        bits = [nulls.is_null(i) if not negated else not nulls.is_null(i) for i in range(len(values))]
        return _bits_to_selection(bits)
    if isinstance(pred, tuple) and pred[0] == "not":
        inner = apply_filter_simple(values, pred[1], lt)
        return inner.invert()
    if isinstance(pred, PredicateEq):
        bits = [v is not None and values_equal(lt, v, pred.value) for v in values]
    elif isinstance(pred, PredicateIn):
        keys = {canonical_key(lt, x) for x in pred.values}
        bits = [v is not None and canonical_key(lt, v) in keys for v in values]
    elif isinstance(pred, PredicateRange):
        bits = []
        for v in values:
            if v is None:
                bits.append(False)
                continue
            ok = True
            if pred.lower is not None:
                ok = ok and (
                    sort_key(lt, v) >= sort_key(lt, pred.lower)
                    if pred.lower_inclusive
                    else sort_key(lt, v) > sort_key(lt, pred.lower)
                )
            if pred.upper is not None:
                ok = ok and (
                    sort_key(lt, v) <= sort_key(lt, pred.upper)
                    if pred.upper_inclusive
                    else sort_key(lt, v) < sort_key(lt, pred.upper)
                )
            bits.append(ok)
    else:
        bits = [True] * len(values)
    return _bits_to_selection(bits)


def apply_filter_simple(values: tuple[Any, ...], predicate: object, lt) -> SelectionVector:
    block = EncodedBlock(
        encoding=Encoding.RAW,
        logical_type=lt,
        payload=b"",
        raw_bytes=0,
        encoded_bytes=0,
        null_count=0,
    )
    return _filter_decoded(values, predicate, block)


def _bits_to_selection(bits: list[bool]) -> SelectionVector:
    n = len(bits)
    buf = bytearray((n + 7) // 8)
    for i, selected in enumerate(bits):
        if selected:
            buf[i // 8] |= 1 << (i % 8)
    return SelectionVector(length=n, bits=bytes(buf))
