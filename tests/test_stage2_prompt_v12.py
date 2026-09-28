from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Stage2PromptV12Tests(unittest.TestCase):
    def test_stage2_v12_preserves_confirmed_ku_and_avoids_atomic_splitting(self):
        prompt = (ROOT / "prompts" / "ku_extract" / "v1.2.md").read_text(encoding="utf-8")

        for phrase in (
            "必须原样返回",
            "不得按句子、编号、数字或 Source Block 机械拆分",
            "KU 的完整原文由程序单独保存",
        ):
            self.assertIn(phrase, prompt)
        self.assertNotIn("evidence_block_ids", prompt)

    def test_stage2_v13_uses_open_semantic_types_without_other(self):
        prompt = (ROOT / "prompts" / "ku_extract" / "v1.3.md").read_text(encoding="utf-8")

        for phrase in (
            "开放式语义类型",
            "knowledge_type_name",
            "element_type_name",
            "全大写英文下划线标识",
            "不得输出 `OTHER`",
        ):
            self.assertIn(phrase, prompt)
        self.assertNotIn('"knowledge_type": "OTHER"', prompt)
        self.assertNotIn('"element_type": "OTHER"', prompt)

    def test_stage2_v14_requires_separate_content_element_evidence(self):
        prompt = (ROOT / "prompts" / "ku_extract" / "v1.4.md").read_text(encoding="utf-8")
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn('"content_element_split"', prompt)
        self.assertIn("与全部内容要素一一对应", prompt)
        self.assertIn("不输出 `source_block_ids`", prompt)
        self.assertIn('DEFAULT_STAGE2_PROMPT_VERSION = "v1.4"', app_source)


if __name__ == "__main__":
    unittest.main()

