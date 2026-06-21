"""소비 분석 시스템 평가 인프라.

정답을 코드로 독립 계산한 벤치마크로, 시스템들의 수치 정확도·환각을
정량 비교한다. 핵심 질문: '숫자는 도구로 계산한다'는 설계가 실제로
환각을 줄이는가?
"""

from .dataset import Question, build_benchmark
from .verify import score_answer

__all__ = ["Question", "build_benchmark", "score_answer"]
