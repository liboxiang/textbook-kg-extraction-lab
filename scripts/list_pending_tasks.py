from pathlib import Path

root = Path(__file__).resolve().parents[1] / ".kg_tasks" / "pending"
for p in sorted(root.glob("*"), reverse=True):
    if p.is_dir():
        status = "DONE" if (p / "result.json").exists() else "PENDING"
        print(f"{status:7} {p}")
