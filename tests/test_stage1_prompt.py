from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Stage1PromptV16Tests(unittest.TestCase):
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

    def test_stage1_v16_requires_separate_natural_language_evidence(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.6.md").read_text(encoding="utf-8")

        self.assertIn('"evidence"', prompt)
        self.assertIn('"ku_split"', prompt)
        self.assertIn("与 KU 一一对应", prompt)
        self.assertIn("不输出 `source_block_ids`", prompt)

    def test_stage1_default_prompt_version_is_v16(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn('DEFAULT_STAGE1_PROMPT_VERSION = "v1.6"', app_source)
        self.assertIn('RECOMMENDED_STAGE1_PROMPT_VERSIONS = {"v1.6", "v1.10"}', app_source)
        self.assertIn('f"{version}｜推荐"', app_source)

    def test_v17_uses_conservative_boundary_gate(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.7.md").read_text(encoding="utf-8")
        self.assertIn("边界证据不足或存在两种合理划分时，默认合并", prompt)
        self.assertIn("对象或任务转换", prompt)
        self.assertIn("独立交付", prompt)
        self.assertIn("非从属关系", prompt)
        self.assertIn("合并不可行", prompt)

    def test_v18_handles_nested_numbering_without_overfitting(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.8.md").read_text(encoding="utf-8")

        self.assertIn("编号层级的解释规则", prompt)
        self.assertIn("子项数量多、内容长或各自可以概括，都不能单独证明", prompt)
        self.assertIn("过度拆分检查", prompt)
        self.assertIn("过度合并检查", prompt)
        self.assertIn("可以拆分", prompt)
        for domain_example in ("双壁钢围堰", "钢管柱", "钢管拱", "钻孔灌注桩"):
            self.assertNotIn(domain_example, prompt)

    def test_v19_balances_over_splitting_and_over_merging(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.9.md").read_text(encoding="utf-8")

        for principle in (
            "最少但足够",
            "同一知识对象下可以存在多个",
            "从属内容检查",
            "独立模块检查",
            "连续作业链检查",
            "自然主问题检查",
            "双向反证复核",
            "宽泛",
            "最近一级",
        ):
            self.assertIn(principle, prompt)

        self.assertNotIn("边界证据不足或存在两种合理划分时，默认合并", prompt)
        self.assertNotIn("任一条件不成立，必须合并", prompt)
        for domain_example in ("双壁钢围堰", "钢管柱", "钢管拱", "钻孔灌注桩", "箱涵"):
            self.assertNotIn(domain_example, prompt)

    def test_v110_prioritizes_merge_checks_before_split_checks(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.10.md").read_text(encoding="utf-8")

        for principle in (
            "第一轮：合并优先检查",
            "连续任务模块",
            "分类主题模块",
            "单一控制目标模块",
            "第二轮：独立任务拆分检查",
            "共享对象、存在标题差异或内容可以单独概括，不足以拆分",
            "数量更少但仍能独立输出",
        ):
            self.assertIn(principle, prompt)

        for domain_example in ("双壁钢围堰", "钢管柱", "钢管拱", "钻孔灌注桩", "箱涵"):
            self.assertNotIn(domain_example, prompt)

    def test_v111_uses_generic_object_and_direct_goal_language(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.11.md").read_text(encoding="utf-8")
        self.assertIn("同一知识对象、同一专业任务或同一直接目标", prompt)
        self.assertIn("判断合并时关注直接目标和结果，不看对象名称是否相同", prompt)
        self.assertIn("分类主题下的分类维度或类别是否被错误拆开", prompt)
        self.assertNotIn("同一施工对象", prompt)

    def test_v112_distinguishes_sequence_and_classification_perspective(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.12.md").read_text(encoding="utf-8")
        for principle in (
            "时间顺序或作业顺序只能证明内容相关，不能单独证明应合并",
            "分类对象、分类目的和分类视角均相同",
            "合并反证",
            "分别用一句话概括两侧的直接结果",
            "不同且非从属的结果，撤销合并",
        ):
            self.assertIn(principle, prompt)
        for domain_example in ("双壁钢围堰", "钢管柱", "钢管拱", "钻孔灌注桩", "箱涵"):
            self.assertNotIn(domain_example, prompt)

    def test_v113_uses_top_level_candidate_and_nested_default_rules(self):
        prompt = (ROOT / "prompts" / "ku_split" / "v1.13.md").read_text(encoding="utf-8")
        for principle in (
            "一级主题是候选边界",
            "①②③、子编号、表格、条件、参数和操作步骤，默认属于该主题的内部结构",
            "时间顺序只能说明内容相关，不能单独证明应合并或应拆分",
            "能够单独概括",
            "独立的知识目的和完整结果",
            "分类内部的具体类别不因为出现①②③或多个小标题而独立成 KU",
        ):
            self.assertIn(principle, prompt)
        self.assertNotIn("合并反证", prompt)
        for domain_example in ("双壁钢围堰", "钢管柱", "钢管拱", "钻孔灌注桩", "箱涵"):
            self.assertNotIn(domain_example, prompt)

    def test_mode_switch_uses_replaceable_api_panel(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('key="run_mode"', app_source)
        self.assertIn("api_panel = st.empty()", app_source)
        self.assertIn("with api_panel.container():", app_source)
        self.assertIn('mode == "模式B｜API自动调用"', app_source)


if __name__ == "__main__":
    unittest.main()
