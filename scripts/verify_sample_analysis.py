from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models.sample_analysis import CreateJobPayload, SampleUpload
from backend.app.providers.heuristic_video_analysis import HeuristicVideoAnalysisProvider
from backend.app.repositories.in_memory_sample_analysis import InMemorySampleAnalysisRepository
from backend.app.services.sample_analysis import SampleAnalysisService


def make_fake_file(path: Path, size_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        file.write(b"0" * size_bytes)


def main() -> None:
    workspace = Path("tmp/sample-analysis-verification")
    single_file = workspace / "single_demo.mp4"
    multi_file_a = workspace / "promo_buy_now.mp4"
    multi_file_b = workspace / "product_story.mp4"

    make_fake_file(single_file, 1_600_000)
    make_fake_file(multi_file_a, 2_200_000)
    make_fake_file(multi_file_b, 900_000)

    service = SampleAnalysisService(
        repository=InMemorySampleAnalysisRepository(),
        provider=HeuristicVideoAnalysisProvider(),
        public_base_url="http://localhost:8000",
    )

    single_job = service.create_job(
        CreateJobPayload(
            session_name="single-session",
            uploads=[
                SampleUpload(
                    original_filename=single_file.name,
                    saved_filename=single_file.name,
                    storage_path=str(single_file),
                    content_type="video/mp4",
                    notes="开头展示产品卖点，中段说明使用场景，结尾引导关注。",
                )
            ],
        )
    )

    multi_job = service.create_job(
        CreateJobPayload(
            session_name="multi-session",
            uploads=[
                SampleUpload(
                    original_filename=multi_file_a.name,
                    saved_filename=multi_file_a.name,
                    storage_path=str(multi_file_a),
                    content_type="video/mp4",
                    notes="开头强调价格优势，结尾提示立即下单。",
                ),
                SampleUpload(
                    original_filename=multi_file_b.name,
                    saved_filename=multi_file_b.name,
                    storage_path=str(multi_file_b),
                    content_type="video/mp4",
                    notes=None,
                ),
            ],
        )
    )

    print("Single job:")
    print(json.dumps(single_job.to_dict(), ensure_ascii=False, indent=2))
    print("\nMulti job:")
    print(json.dumps(multi_job.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
