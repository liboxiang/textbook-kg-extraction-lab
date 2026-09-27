from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Stage1PromptV14Tests(unittest.TestCase):
    def test_stage1_v14_is_generic_and_avoids_sample_specific_rules(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.4.md").read_text(encoding="utf-8")

        self.assertNotIn("总起句与并列分项的完整性规则", prompt)
        for sample_term in ("垫层", "基层", "面层", "纵缝", "横缝", "传力杆", "抗滑构造"):
            self.assertNotIn(sample_term, prompt)

        for generic_concept in ("知识对象", "统领性主问题", "语义依赖", "专业任务"):
            self.assertIn(generic_concept, prompt)

    def test_stage1_default_prompt_version_is_v14(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")


        self.assertIn('DEFAULT_STAGE1_PROMPT_VERSION = "v1.4"', app_source)


if __name__ == "__main__":
    unittest.main()
