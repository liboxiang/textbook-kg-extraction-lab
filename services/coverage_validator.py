from __future__ import annotations

from schemas.models import (
    KnowledgePointInput,
    SourceBlock,
    Stage1LLMResult,
    Stage1ResolvedResult,
    Stage1Validation,
    KUResolved,
)


def validate_and_resolve_stage1(
    kp: KnowledgePointInput,
    blocks: list[SourceBlock],
    result: Stage1LLMResult,
) -> Stage1ResolvedResult:
    errors: list[str] = []
    block_index = {b.block_id: i for i, b in enumerate(blocks)}
    total_blocks = len(blocks)
    covered_counts = [0] * total_blocks
    resolved: list[KUResolved] = []

    units = sorted(result.knowledge_units, key=lambda x: x.order_index)
    expected_orders = list(range(1, len(units) + 1))
    actual_orders = [u.order_index for u in units]
    order_valid = actual_orders == expected_orders
    if not order_valid:
        errors.append(f"order_index 必须从1连续递增，当前为 {actual_orders}")

    ids = [u.temp_ku_id for u in units]
    if len(ids) != len(set(ids)):
        errors.append("temp_ku_id 存在重复")

    last_end = -1
    for unit in units:
        if unit.start_block_id not in block_index:
            errors.append(f"{unit.temp_ku_id}: start_block_id 不存在: {unit.start_block_id}")
            continue
        if unit.end_block_id not in block_index:
            errors.append(f"{unit.temp_ku_id}: end_block_id 不存在: {unit.end_block_id}")
            continue
        s = block_index[unit.start_block_id]
        e = block_index[unit.end_block_id]
        if s > e:
            errors.append(f"{unit.temp_ku_id}: start_block 位于 end_block 之后")
            continue
        if s <= last_end:
            errors.append(f"{unit.temp_ku_id}: 与前一个KU存在重叠或顺序错误")
        last_end = max(last_end, e)
        for i in range(s, e + 1):
            covered_counts[i] += 1
        source_text = "".join(b.text for b in blocks[s : e + 1])
        resolved.append(
            KUResolved(
                temp_ku_id=unit.temp_ku_id,
                order_index=unit.order_index,
                title=unit.title,
                main_question=unit.main_question,
                section_path=unit.section_path,
                start_block_id=unit.start_block_id,
                end_block_id=unit.end_block_id,
                start_offset=blocks[s].start_offset,
                end_offset=blocks[e].end_offset,
                source_text=source_text,
                page_start=kp.page_start,
                page_end=kp.page_end,
            )
        )

    gap_count = sum(1 for c in covered_counts if c == 0)
    overlap_count = sum(1 for c in covered_counts if c > 1)
    covered = sum(1 for c in covered_counts if c > 0)
    coverage_rate = (covered / total_blocks) if total_blocks else 0.0
    all_blocks_covered = gap_count == 0 and total_blocks > 0

    if gap_count:
        missing = [blocks[i].block_id for i, c in enumerate(covered_counts) if c == 0]
        errors.append(f"存在未覆盖Source Block: {', '.join(missing)}")
    if overlap_count:
        duplicated = [blocks[i].block_id for i, c in enumerate(covered_counts) if c > 1]
        errors.append(f"存在重复覆盖Source Block: {', '.join(duplicated)}")

    # Exact source reconstruction check.
    reconstructed = "".join(u.source_text for u in sorted(resolved, key=lambda x: x.order_index))
    exact_reconstruction = reconstructed == kp.source_text
    if not exact_reconstruction:
        errors.append("KU原文按顺序拼接后不能精确还原KP原文")

    passed = (
        bool(units)
        and order_valid
        and all_blocks_covered
        and overlap_count == 0
        and exact_reconstruction
        and not errors
    )
    validation = Stage1Validation(
        coverage_rate=coverage_rate,
        gap_count=gap_count,
        overlap_count=overlap_count,
        order_valid=order_valid,
        all_blocks_covered=all_blocks_covered,
        status="PASS" if passed else "FAIL",
        errors=errors,
    )
    return Stage1ResolvedResult(
        kp_id=kp.kp_id,
        kp_name=kp.kp_name,
        source_blocks=blocks,
        knowledge_units=resolved,
        validation=validation,
    )
