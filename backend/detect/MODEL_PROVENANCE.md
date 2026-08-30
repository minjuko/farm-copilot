# 병해 탐지 모델 출처와 클래스 계약

## 원천 데이터

- AI-Hub `식물 병 유발 통합 데이터` (데이터셋 번호 525)
- 공식 페이지: https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=data&currMenu=115&dataSetSn=525&topMenu=100
- 이 데이터셋에는 정상, 병해, 생리장해, 보호제 처리반응 이미지가 함께 포함된다.
- 현재 모델이 사용하는 작물·병해는 고추 탄저병·흰가루병, 오이 노균병·흰가루병,
  토마토 흰가루병이다.

AI-Hub는 학습 이미지와 라벨의 출처다. API가 제공하는 발생환경, 증상, 방제 설명의
출처는 아니므로 해당 설명은 농촌진흥청 NCPMS·농사로 자료를 별도로 인용한다.

## 모델 artifact

- 공개 저장소에서는 용량과 배포 정책 때문에 `best.pt`를 제외한다.
- 로컬 또는 배포 환경에서 `YOLO_MODEL_PATH`로 artifact 위치를 지정한다.
- 과거 저장소 blob `70ef43b5feda337643d2a537d36e25f0fa2a53f3`의 Ultralytics
  metadata를 2026-08-30에 다시 추출해 아래 순서를 확인했다.

| class_id | model label | 상세정보 코드 |
|---:|---|---|
| 0 | 고추 탄저병 | `PEPPER_ANTHRACNOSE` |
| 1 | 고추 흰가루병 | `PEPPER_POWDERY_MILDEW` |
| 2 | 오이 노균병 | `CUCUMBER_DOWNY_MILDEW` |
| 3 | 토마토 흰가루병 | `TOMATO_POWDERY_MILDEW` |
| 4 | 오이 노균병 | `CUCUMBER_DOWNY_MILDEW` |
| 5 | 오이 흰가루병 | `CUCUMBER_POWDERY_MILDEW` |

클래스 2와 4의 동일 라벨은 모델 metadata 원문 그대로이며 둘 다 같은 병해 상세정보로
연결한다. 현재 보존된 모델 metadata만으로 두 클래스의 수집 조건 차이는 확정할 수 없다.

## 실행 안전장치

- 모델을 로드할 때 여섯 클래스의 ID와 라벨이 위 계약과 정확히 같은지 검사한다.
- 다른 artifact이거나 클래스 순서가 바뀌면 추론하지 않고 HTTP 503 경계로 처리한다.
- `detect/fixtures/model_classes.json`은 여섯 클래스 전체와 농촌진흥청 출처가 있는
  다섯 병해 상세정보를 함께 로드한다.
- 결과는 영상 기반 추정이며 확정 진단이나 특정 농약 처방으로 사용하지 않는다.
