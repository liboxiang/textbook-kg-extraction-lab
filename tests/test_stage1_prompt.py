from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Stage1PromptV15Tests(unittest.TestCase):
    def test_stage1_v15_is_generic_and_audits_over_splitting(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.5.md").read_text(encoding="utf-8")

        self.assertNotIn("总起句与并列分项的完整性规则", prompt)
        for sample_term in ("垫层", "基层", "面层", "纵缝", "横缝", "传力杆", "抗滑构造"):
            self.assertNotIn(sample_term, prompt)

        for generic_concept in (
            "章节语义树",
            "递进式完整论述",
            "统领问题合并测试",
            "相邻 KU 二次合并复核",
            "较长表格",
            "section_path",
        ):
            self.assertIn(generic_concept, prompt)

    def test_stage1_default_prompt_version_is_v15(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn('DEFAULT_STAGE1_PROMPT_VERSION = "v1.5"', app_source)

    def test_mode_switch_uses_replaceable_api_panel(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('key="run_mode"', app_source)
        self.assertIn("api_panel = st.empty()", app_source)
        self.assertIn("with api_panel.container():", app_source)
        self.assertIn('mode == "模式B｜API自动调用"', app_source)


if __name__ == "__main__":
    unittest.main()
