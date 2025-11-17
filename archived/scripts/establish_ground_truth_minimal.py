"""
Ground Truth 최소 검증 - 30-50 샘플 수동 검증
Created: 2025-11-16

Purpose:
    실제 F1-Score 계산을 위한 Ground Truth 구축
    - DB에서 랜덤 30-50개 샘플 추출
    - 수동 검증 (title/body 존재 여부)
    - Precision, Recall, F1-Score 계산

Methodology:
    1. 각 사이트당 5-10개씩 랜덤 샘플링 (총 30-50개)
    2. 터미널에서 URL + 크롤링 결과 출력
    3. 사용자가 수동으로 Y/N 입력
    4. Ground Truth CSV 저장
    5. F1-Score 계산

Usage:
    cd /Users/charlee/Desktop/Intern/crawlagent
    poetry run python scripts/establish_ground_truth_minimal.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import csv
import random
from typing import Dict, List

from loguru import logger

from src.storage.models import CrawlResult
from src.utils.db_utils import get_db_session_no_commit

# 검증할 샘플 수
SAMPLES_PER_SITE = {
    "yonhap": 15,  # 가장 많은 데이터
    "donga": 5,
    "mk": 5,
    "bbc": 5,
    "hankyung": 5,
    "cnn": 5,
}


def extract_random_samples() -> List[Dict]:
    """
    DB에서 랜덤 샘플 추출

    Returns:
        샘플 리스트: [{url, site_name, title, body, quality_score}, ...]
    """
    logger.info("=" * 80)
    logger.info("DB에서 랜덤 샘플 추출 시작")
    logger.info("=" * 80)

    samples = []

    with get_db_session_no_commit() as db:
        for site_name, count in SAMPLES_PER_SITE.items():
            # 해당 사이트의 모든 크롤링 결과 조회
            crawl_results = db.query(CrawlResult).filter_by(site_name=site_name).all()

            if not crawl_results:
                logger.warning(f"⚠️  {site_name}: DB에 크롤링 결과 없음")
                continue

            # 랜덤 샘플링
            sample_count = min(count, len(crawl_results))
            random_samples = random.sample(crawl_results, sample_count)

            for result in random_samples:
                samples.append(
                    {
                        "url": result.url,
                        "site_name": result.site_name,
                        "title": result.title,
                        "body": result.body,
                        "quality_score": result.quality_score,
                        "predicted_success": bool(result.title and result.body),
                    }
                )

            logger.info(f"✅ {site_name}: {sample_count}개 샘플 추출")

    logger.info(f"\n총 {len(samples)}개 샘플 추출 완료")
    logger.info("=" * 80)

    return samples


def manual_validation(samples: List[Dict]) -> List[Dict]:
    """
    수동 검증 수행 (터미널 인터랙티브)

    Args:
        samples: 검증할 샘플 리스트

    Returns:
        Ground Truth 추가된 샘플 리스트
    """
    logger.info("=" * 80)
    logger.info("수동 검증 시작")
    logger.info("=" * 80)
    logger.info("각 샘플에 대해 Title과 Body가 올바르게 추출되었는지 확인하세요.")
    logger.info("Y: 정상, N: 비정상, S: 건너뛰기, Q: 종료\n")

    ground_truth_samples = []

    for i, sample in enumerate(samples, 1):
        print("\n" + "=" * 80)
        print(f"샘플 {i}/{len(samples)}")
        print("=" * 80)
        print(f"사이트: {sample['site_name']}")
        print(f"URL: {sample['url']}")
        print(f"\n--- 크롤링 결과 ---")
        print(f"Title: {sample['title'][:100] if sample['title'] else '❌ None'}...")
        print(f"Body: {sample['body'][:200] if sample['body'] else '❌ None'}...")
        print(f"Quality Score: {sample['quality_score']}")
        print(f"예측 결과: {'✅ 성공' if sample['predicted_success'] else '❌ 실패'}")
        print("=" * 80)

        while True:
            answer = input("올바른 크롤링인가요? (Y/N/S/Q): ").strip().upper()

            if answer == "Y":
                sample["ground_truth"] = True
                ground_truth_samples.append(sample)
                print("✅ 정상으로 기록")
                break
            elif answer == "N":
                sample["ground_truth"] = False
                ground_truth_samples.append(sample)
                print("❌ 비정상으로 기록")
                break
            elif answer == "S":
                print("⏭️  건너뛰기")
                break
            elif answer == "Q":
                logger.info(f"\n중단: {len(ground_truth_samples)}개 샘플 검증 완료")
                return ground_truth_samples
            else:
                print("⚠️  잘못된 입력입니다. Y/N/S/Q 중 하나를 입력하세요.")

    logger.info(f"\n✅ 총 {len(ground_truth_samples)}개 샘플 검증 완료")
    return ground_truth_samples


def save_ground_truth_csv(samples: List[Dict]):
    """
    Ground Truth를 CSV로 저장

    Args:
        samples: Ground Truth 포함된 샘플 리스트
    """
    csv_path = project_root / "docs" / "ground_truth_samples.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "site_name",
            "url",
            "title",
            "body",
            "quality_score",
            "predicted_success",
            "ground_truth",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for sample in samples:
            writer.writerow(
                {
                    "site_name": sample["site_name"],
                    "url": sample["url"],
                    "title": sample["title"][:100] if sample["title"] else "",
                    "body": sample["body"][:200] if sample["body"] else "",
                    "quality_score": sample["quality_score"],
                    "predicted_success": sample["predicted_success"],
                    "ground_truth": sample["ground_truth"],
                }
            )

    logger.success(f"✅ Ground Truth 저장 완료: {csv_path}")


def calculate_f1_score(samples: List[Dict]) -> Dict:
    """
    F1-Score 계산

    Args:
        samples: Ground Truth 포함된 샘플 리스트

    Returns:
        {precision, recall, f1_score, tp, fp, tn, fn}
    """
    logger.info("=" * 80)
    logger.info("F1-Score 계산")
    logger.info("=" * 80)

    # True Positive: 시스템 성공 + Ground Truth 성공
    tp = sum(1 for s in samples if s["predicted_success"] and s["ground_truth"])

    # False Positive: 시스템 성공 + Ground Truth 실패
    fp = sum(1 for s in samples if s["predicted_success"] and not s["ground_truth"])

    # True Negative: 시스템 실패 + Ground Truth 실패
    tn = sum(1 for s in samples if not s["predicted_success"] and not s["ground_truth"])

    # False Negative: 시스템 실패 + Ground Truth 성공
    fn = sum(1 for s in samples if not s["predicted_success"] and s["ground_truth"])

    # Precision = TP / (TP + FP)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    # Recall = TP / (TP + FN)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # F1-Score = 2 * (Precision * Recall) / (Precision + Recall)
    f1_score = (
        2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    )

    logger.info(f"\n--- Confusion Matrix ---")
    logger.info(f"True Positive (TP): {tp}")
    logger.info(f"False Positive (FP): {fp}")
    logger.info(f"True Negative (TN): {tn}")
    logger.info(f"False Negative (FN): {fn}")
    logger.info(f"\n--- Metrics ---")
    logger.info(f"Precision: {precision:.4f} ({precision*100:.2f}%)")
    logger.info(f"Recall: {recall:.4f} ({recall*100:.2f}%)")
    logger.info(f"F1-Score: {f1_score:.4f} ({f1_score*100:.2f}%)")
    logger.info("=" * 80)

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "total_samples": len(samples),
    }


def save_f1_report(metrics: Dict):
    """
    F1-Score 결과를 마크다운으로 저장

    Args:
        metrics: F1-Score 메트릭
    """
    report_path = project_root / "docs" / "GROUND_TRUTH_F1_SCORE.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Ground Truth F1-Score 검증 결과\n\n")
        f.write(f"생성 시각: 2025-11-16\n\n")

        f.write("## 1. 검증 방법론\n\n")
        f.write("### 샘플링\n\n")
        f.write("- **총 샘플 수**: 30-50개 (사이트별 5-15개)\n")
        f.write("- **샘플링 방법**: 랜덤 샘플링 (random.sample)\n")
        f.write("- **검증 방법**: 수동 검증 (사람이 직접 확인)\n\n")

        f.write("### 평가 기준\n\n")
        f.write("- **Predicted Success**: Title과 Body가 모두 추출되면 성공\n")
        f.write("- **Ground Truth**: 사람이 수동으로 확인한 실제 결과\n")
        f.write("- **F1-Score**: Precision과 Recall의 조화 평균\n\n")

        f.write("## 2. Confusion Matrix\n\n")
        f.write("| 구분 | 값 |\n")
        f.write("|------|----|\n")
        f.write(f"| True Positive (TP) | {metrics['tp']} |\n")
        f.write(f"| False Positive (FP) | {metrics['fp']} |\n")
        f.write(f"| True Negative (TN) | {metrics['tn']} |\n")
        f.write(f"| False Negative (FN) | {metrics['fn']} |\n")
        f.write(f"| **Total Samples** | {metrics['total_samples']} |\n\n")

        f.write("## 3. 평가 메트릭\n\n")
        f.write("| 메트릭 | 값 | 백분율 |\n")
        f.write("|--------|----|---------|\n")
        f.write(f"| **Precision** | {metrics['precision']:.4f} | {metrics['precision']*100:.2f}% |\n")
        f.write(f"| **Recall** | {metrics['recall']:.4f} | {metrics['recall']*100:.2f}% |\n")
        f.write(f"| **F1-Score** | {metrics['f1_score']:.4f} | {metrics['f1_score']*100:.2f}% |\n\n")

        f.write("## 4. 공식\n\n")
        f.write("```\n")
        f.write("Precision = TP / (TP + FP)\n")
        f.write("Recall = TP / (TP + FN)\n")
        f.write("F1-Score = 2 * (Precision * Recall) / (Precision + Recall)\n")
        f.write("```\n\n")

        f.write("## 5. 재현 방법\n\n")
        f.write("```bash\n")
        f.write("cd /Users/charlee/Desktop/Intern/crawlagent\n")
        f.write("poetry run python scripts/establish_ground_truth_minimal.py\n")
        f.write("```\n\n")

        f.write("---\n")
        f.write("*이 검증은 실제 수동 검증을 기반으로 작성되었습니다. Mock 데이터 없음.*\n")

    logger.success(f"✅ F1-Score 결과 저장 완료: {report_path}")


def main():
    logger.info("🚀 Ground Truth 최소 검증 시작")

    # 1. 랜덤 샘플 추출
    samples = extract_random_samples()

    if len(samples) == 0:
        logger.error("❌ 추출된 샘플이 없습니다.")
        return

    # 2. 수동 검증 (인터랙티브)
    logger.info("\n⚠️  주의: 이 단계는 인터랙티브 입력이 필요합니다.")
    logger.info("각 샘플을 확인하고 Y/N을 입력하세요.\n")

    proceed = input("계속하시겠습니까? (Y/N): ").strip().upper()
    if proceed != "Y":
        logger.info("중단됨")
        return

    ground_truth_samples = manual_validation(samples)

    if len(ground_truth_samples) == 0:
        logger.error("❌ 검증된 샘플이 없습니다.")
        return

    # 3. Ground Truth CSV 저장
    save_ground_truth_csv(ground_truth_samples)

    # 4. F1-Score 계산
    metrics = calculate_f1_score(ground_truth_samples)

    # 5. F1-Score 결과 저장
    save_f1_report(metrics)

    logger.success("🎉 Ground Truth 검증 완료!")


if __name__ == "__main__":
    main()
