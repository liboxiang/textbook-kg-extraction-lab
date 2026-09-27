import unittest

from schemas.models import (
    ContentElement,
    FinalExtraction,
    FinalKU,
    KnowledgePointInput,
    Stage1Validation,
)


class ReportGraphTests(unittest.TestCase):
    def make_result(self):
        return FinalExtraction(
            kp=KnowledgePointInput(kp_id="KP1", kp_name="测试知识点", source_text="原文。"),
            stage1_validation=Stage1Validation(
                coverage_rate=1.0,
                gap_count=0,
                overlap_count=0,
                order_valid=True,
                all_blocks_covered=True,
                status="PASS",
            ),
            knowledge_units=[
                FinalKU(
                    ku_id="KP1_KU_01",
                    kp_id="KP1",
                    order_index=1,
                    title="单元一",
                    main_question="说明什么？",
                    knowledge_object="对象一",
                    core_conclusion="结论一",
                    knowledge_type="RULE",
                    start_offset=0,
                    end_offset=3,
                    start_block_id="S0001",
                    end_block_id="S0001",
                    source_text="原文。",
                    content_elements=[
                        ContentElement(
                            element_id="CE_01",
                            element_type="DEFINITION",
                            name="定义",
                            content="定义内容",
                        )
                    ],
                )
            ],
        )

    def test_content_element_has_chinese_type_name(self):
        element = self.make_result().knowledge_units[0].content_elements[0]
        self.assertEqual(element.element_type_name, "定义")
        self.assertNotIn("evidence_block_ids", element.model_dump())

    def test_graph_contains_entities_relationships_and_attributes(self):
        from services.report_graph import build_graph_data

        graph = build_graph_data(self.make_result())
        node_ids = {node["id"] for node in graph["nodes"]}
        self.assertTrue({"kp:KP1", "ku:KP1_KU_01", "ce:KP1_KU_01:CE_01"} <= node_ids)
        self.assertIn(
            {"source": "kp:KP1", "target": "ku:KP1_KU_01", "label": "包含"},
            graph["edges"],
        )
        ce_node = next(node for node in graph["nodes"] if node["id"].startswith("ce:"))
        ku_node = next(node for node in graph["nodes"] if node["id"] == "ku:KP1_KU_01")
        self.assertEqual(ce_node["attributes"]["element_type_name"], "定义")
        self.assertIn("source_text", ku_node["attributes"])

    def test_graph_allocates_vertical_space_for_many_content_elements(self):
        from services.report_graph import build_graph_data

        result = self.make_result()
        result.knowledge_units[0].content_elements.extend(
            result.knowledge_units[0].content_elements[0].model_copy(
                update={"element_id": f"CE_{index:02d}", "name": f"要素{index}"}
            )
            for index in range(2, 7)
        )
        graph = build_graph_data(result)
        element_nodes = [node for node in graph["nodes"] if node["kind"] == "element"]
        self.assertGreaterEqual(graph["height"], 600)
        self.assertEqual(
            len({node["y"] for node in element_nodes}), len(element_nodes)
        )

    def test_report_contains_interactive_graph_and_type_name_column(self):
        from services.report_renderer import render_html_report

        html = render_html_report(self.make_result())
        self.assertIn("知识图谱", html)
        self.assertIn("element_type_name", html)
        self.assertNotIn("证据</th>", html)
        self.assertIn("全屏展示", html)
        self.assertIn("requestFullscreen", html)
        self.assertIn("教材原文", html)
        self.assertIn("detail-source", html)
        self.assertIn("KP1_KU_01", html)


if __name__ == "__main__":
    unittest.main()
