from services.source_segmenter import segment_source_text


def test_segmenter_lossless():
    text = "第一句。\n第二句；第三句！\n\n最后一句"
    blocks = segment_source_text(text)
    assert blocks
    assert "".join(b.text for b in blocks) == text
    assert blocks[0].start_offset == 0
    assert blocks[-1].end_offset == len(text)
