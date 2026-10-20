# 평가 데이터 설계 v1

이 문서는 확보할 데이터의 설계다. 현재 실제 평가 이미지는 0장이다.
예시 CSV는 헤더만 제공하며, 검수되지 않은 참고 이미지나 생성 이미지를 채워 넣지 않는다.
테스트 안의 합성 이미지·정답은 도구 로직 검증 전용이다.

## 평가 범주·규모

| category | subcategory | 내용 |
|---|---|---|
| supported | disease | 고추 탄저병·흰가루병, 오이 노균병·흰가루병, 토마토 흰가루병 |
| normal | healthy | 고추·오이·토마토 정상 |
| unsupported | crop / disease / general_plant | 미지원 작물, 지원 작물의 미지원 질병, 일반 식물 |
| quality | blur / dark / bright / small_lesion | 흐림·노출 불량·작은 병반. 정상/미지원과 별도 층으로 관리 |

우선 목표는 파이프라인 검수를 위한 **지원 병해별 20장, 정상 작물별 20장,
미지원 하위범주별 20장, 품질 유형별 10장**이다(총 260장, 확보량이 아닌 계획).
표본 수가 충분하다는 통계적 보장은 아니다. 각 층의 validation/test 목표를 절반씩
배정하되 식물·원본 그룹을 나누지 않는다. 작은 test 분모로 품질 우수성을 주장하지 않는다.
정식 비교 전 클래스별 오차 범위와 수집 예산을 보고 표본 수를 확정하고 test를 동결한다.

합성 흐림/노출 변형을 만들 경우 원본과 같은 origin_id·group_id·split에 두고 별도
강건성 시험으로 명시한다. 원본과 변형본을 독립 이미지처럼 총정확도에 합산하지 않는다.
현재 도구는 품질 이미지를 주요 품질 지표에서 제외하고 거절률을 따로 기록한다.

## Manifest

UTF-8 CSV. [예시](dataset_manifest.example.csv)와 헤더 이름·순서가 같아야 한다.
하나의 manifest에 validation/test를 함께 넣어 교차 중복을 검사한다.
경로는 `--data-root` 기준 POSIX 상대경로다. 개인 경로·API key·검수자 실명은 넣지 않는다.

| 필드 | 내용 |
|---|---|
| image_id | 익명 고유 식별자 |
| relative_path | 데이터 root 안의 파일. 절대경로, `..`, 역슬래시, 외부 symlink 차단 |
| sha256 | 파일 내용 SHA-256 소문자 64자리. 실행 시 재계산 |
| split | `validation` 또는 `test` |
| group_id | 같은 식물·연속 촬영·획득 세션의 전역 그룹 ID |
| origin_id | 원본과 모든 증강본이 공유하는 전역 ID |
| category / subcategory | 위 범주 |
| crop | `pepper`, `cucumber`, `tomato`, 또는 익명화된 미지원 작물 코드 |
| target_labels | 아래 서비스 라벨, `healthy`, `unsupported`. 복수 질병은 `|`로 연결. 미확정은 공란 |
| review_status | `verified` / `unreviewed` |
| label_evidence | 진단/검수 근거 문서의 익명 참조 ID. 예: `review-batch-001` |
| source_id / source_version | 취득 출처 및 고정 버전/릴리스 식별자 |
| license_id / license_review | 조건 기록의 ID와 `approved` / `pending` |
| training_overlap | `unknown`, `not_found`, `overlap`. `not_found`도 독립성 증명은 아님 |

식별자 필드는 영숫자로 시작하고 영숫자·`_`·`.`·`-`만 허용한다.
실제 출처 URL, 라이선스 전문, 검수 절차, 원본 라벨 코드/박스 의미, 사용 승인 범위는
비공개 `data/source_register.md`에서 source_id/license_id/label_evidence와 연결한다.
일반 URL은 근거 문서에 기록할 수 있으나 signed URL·토큰·개인정보는 기록하지 않는다.

서비스 라벨:

```text
PEPPER_ANTHRACNOSE
PEPPER_POWDERY_MILDEW
CUCUMBER_DOWNY_MILDEW
CUCUMBER_POWDERY_MILDEW
TOMATO_POWDERY_MILDEW
```

`verified`는 모델 예측을 보고 맞춘 이름이 아니라 원천 코드북과 전문가/출처의 정답
근거를 대조한 상태다. `approved`도 도구가 이용권한을 부여한다는 뜻이 아니며 사람이
해당 평가 목적의 이용조건을 확인했다는 기록이다. 도구는 이 진술의 진실성을 보장하지 못한다.

## 분할·중복 검수

1. 이용 조건과 원천 라벨을 검토한 뒤 원본 목록·해시를 만든다.
2. 같은 잎/식물/연속 촬영, 원본/변형본에 전역 그룹을 부여한다. 서로 다른 출처의
   재배포 사본도 같은 origin/group으로 연결한다.
3. **그룹 단위**로 층별 분할(seed 2024)을 정하고 manifest를 동결한다.
   현재 도구는 자동 분할하지 않는다. 분할 근거를 수집 기록에 남긴다.
4. 전체 manifest의 SHA-256 동일 파일은 split에 관계없이 차단한다.
   group_id 또는 origin_id가 validation/test에 걸치면 차단한다.
5. 재인코딩·crop·배경 제거는 해시만으로 못 잡는다. 썸네일 비교와 필요시 pHash 등
   유사도 도구로 후보를 찾고 사람이 판정한다. 이 버전에는 유사도 자동 검사가 없다.
6. 기존 학습 목록을 확보하면 원본·변형·그룹 중복을 함께 비교한다. 확인된 중복은
   `overlap`으로 표시해 평가에서 차단한다. 목록이 없으면 `unknown`을 유지한다.
7. validation으로 threshold/TTA를 선택하고 test는 최종 비교에만 사용한다.
   test 결과를 보고 수정했다면 그 test는 이후 선택용으로 사용됐음을 기록한다.

동일 manifest hash는 파일 내용이 고정됐다는 의미일 뿐, 라벨의 의학적/병리학적
정확성·검수 품질·독립성을 보증하지 않는다. 출처별 결과와 분모도 따로 검토한다.

## 이미지 단위 정책과 지표

- 추론 결과의 모든 반환 박스 confidence/class ID를 검증한다.
- threshold **이상**인 박스 중 최고 confidence 하나를 선택한다. 동점은 반환 순서상 첫 번째.
- ID 2·4를 현재 서비스의 `CUCUMBER_DOWNY_MILDEW`로 연결하되 원시 ID도 보존한다.
  이 연결로 평가하는 것은 **현재 서비스 표시 결과**다. 두 원시 클래스의 의미를 입증하지 않는다.
- 후보가 없거나 threshold 미만이면 `abstain`. 정상 진단 또는 미지원 입력 식별 성공이라는 뜻은 아니다.
- 정상/미지원 입력에서 어떤 지원 질병이든 수락하면 해당 범주의 오탐이다.
- 여러 질병 정답은 주요 단일 라벨 지표에서 제외한다. 별도의 top1-in-truth 진단 지표만
  제공하며 모든 질병을 찾았다는 의미로 해석하지 않는다.
- 품질 층은 주요 지표에서 제외하고 이미지별 예측·거절률을 따로 제공한다.

주요 지표는 검수된 단일 정답의 supported/normal/unsupported에 한정한다.

| 지표 | 정의 |
|---|---|
| supported_match_rate | 지원 질병 정답과 일치한 이미지 / 지원 질병 단일 정답 이미지. 거절은 미일치 |
| 질병별 Precision | 그 질병 TP / (TP+FP). 정상·미지원에서 해당 질병 예측도 FP |
| 질병별 Recall | 그 질병 TP / (TP+FN). 다른 질병 예측과 거절은 FN |
| normal/unsupported false positive rate | 해당 범주에서 질병 판단을 수락한 이미지 / 해당 범주 이미지 |
| abstention_rate | 판단 거절 이미지 / 주요 평가 이미지 |
| accepted_error_rate | 수락한 오답 / 수락한 결과. 수락 0건이면 null |
| confusion_matrix | 행=정답, 열=예측. 정답에 healthy/unsupported, 예측에 abstain 포함 |

모든 비율에 numerator/denominator/value를 기록한다. 분모 0은 0점이나 100점이 아닌 null.
unknown 정답 또는 unreviewed 표본이 선택 split에 있으면 점수 계산 전체를 차단한다.
`--predict-only`는 정답 없이 실행할 수 있지만 **항상 metrics=null**이다.

## Bounding box 평가는 별도 경로

현 버전 실행기는 이미지 평가만 구현한다. `mode=bbox`는 명시적으로 거부한다.
ID 2·4가 미해결인 상태에서 임의로 정답 클래스를 복제하거나 6개 클래스 mAP를 산출하지 않는다.
다음 조건이 충족된 뒤 별도 bbox 실행기를 추가한다.

1. 정답과 출력의 원시 클래스 의미·순서를 근거로 확정.
2. 객체 전체인지 병반인지 **박스 의미** 일치 검수. AI Hub 525의 bbox/part 혼동 금지.
3. 검수된 YOLO 정규화 `class x_center y_center width height` 라벨,
   이미지·라벨 일대일 목록, 정상의 빈 라벨, bounds와 누락 검사 준비.
4. Ultralytics `model.val(data=명시적_local_yaml, split=명시적_split, ...)` 사용.
   체크포인트 안의 `/content/...` 기본값에 의존하지 않는다.
5. 버전·가중치·설정·데이터 해시와 per-image 정답/박스 예측 저장 계약을 별도 검증.

[Ultralytics 공식 validation 문서](https://docs.ultralytics.com/modes/val/)의
P/R, mAP50, mAP50-95, 클래스별 지표와 confusion matrix를 우선 사용한다.
현재 웹 문서는 신버전 기능도 포함하므로 설치된 8.3.169 소스를 함께 조사했다.
`models/yolo/detect/val.py`는 지표를 수집하고, confusion matrix 갱신은 `plots` 조건부다.
현재 구현되지 않은 bbox용 실행 예시를 실행 가능한 평가 명령처럼 제공하지 않는다.

주의할 설정 차이:

- bbox AP는 confidence 순위 곡선 평가다. 후보 confidence floor(예: 설치 기본값 0.001)와
  서비스 수락 threshold 0.6을 구분한다. 0.6으로 후보를 미리 잘라 AP를 왜곡하지 않는다.
- `iou` 인자는 NMS IoU이고 mAP50/50-95의 정답 매칭 IoU와 같은 설정이 아니다.
- Ultralytics 집계 P/R의 operating point를 서비스 0.6 지표와 동일하다고 가정하지 않는다.
- 5개 질병으로 통합한 bbox 평가는 prediction과 GT 모두 별도 의미·NMS 정책을 정의해야
  하므로 원시 6개 클래스 평가와 별도 보고해야 한다.
- 이미지 정답만으로는 박스 위치·개수·IoU를 알 수 없다. 현재 출력의 mAP는 null이다.
