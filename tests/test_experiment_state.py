import unittest

from services.experiment_state import get_experiment_stage, reset_experiment_state


class ExperimentStateTests(unittest.TestCase):
    def test_stage_progression(self):
        state = {}
        self.assertEqual(get_experiment_stage(state), "输入 KP")
        state.update(kp_id="KP1", source_text="原文")
        self.assertEqual(get_experiment_stage(state), "输入完成")
        state["stage1_resolved"] = {}
        self.assertEqual(get_experiment_stage(state), "阶段1进行中")
        state["stage1_confirmed"] = True
        self.assertEqual(get_experiment_stage(state), "阶段2待执行")
        state["stage2_llm"] = {}
        self.assertEqual(get_experiment_stage(state), "阶段2进行中")
        state["final_result"] = {}
        self.assertEqual(get_experiment_stage(state), "结果完成")

    def test_reset_only_clears_current_batch(self):
        state = {"kp_id": "KP1", "stage1_resolved": {}, "stage1_confirmed": True,
                 "final_result": {}, "unrelated": "keep"}
        reset_experiment_state(state)
        self.assertEqual(state, {"kp_id": "KP1", "unrelated": "keep"})


if __name__ == "__main__":
    unittest.main()
