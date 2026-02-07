from pathlib import Path
import os

svc_file = Path(r"c:\Users\Betopia\Downloads\djdutts-20260205T094532Z-1-001\djdutts\app\services\interview\services.py")

candidates = [
    None,
    os.getenv("QA_DATASET_PATH"),
    str(svc_file.resolve().parents[2] / "files" / "hr_interview_questions_dataset.json"),
    str(Path.cwd() / "files" / "hr_interview_questions_dataset.json"),
]

for i, c in enumerate(candidates):
    if not c:
        print(f"{i}: (no value)")
        continue
    print(f"{i}: {c} -> {Path(c).exists()}")

# Print the first existing candidate (or None)
resolved = next((c for c in candidates if c and Path(c).exists()), None)
print('\nresolved:', resolved)
