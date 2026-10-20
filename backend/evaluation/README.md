# Farm Copilot 독립 평가 도구

기존 모델을 변경하기 전 평가를 준비하는 도구다. 서비스 코드, Django 설정/DB,
프론트엔드를 import하거나 수정하지 않는다. 학습·다운로드 기능은 없다.

- [출처 복원 조사와 데이터 후보](PROVENANCE.md)
- [평가셋·지표·bbox 후속 조건](DATASET_DESIGN.md)
- [이번 작업의 검증 결과](VALIDATION.md)

## 구현 범위

**이미지 단위 서비스 평가**를 구현했다. ID 2·4 의미가 미확정이므로 원시 6개 클래스
성능과 bbox mAP는 계산하지 않는다. 새 모델도 같은 5개 서비스 라벨을 대상으로
비교할 수 있지만 class_contract는 해당 아티팩트의 검증된 순서·이름에 맞춰 별도 설정한다.
현재 예시는 기존 모델의 연결을 그대로 보존한다.

| 파일 | 역할 |
|---|---|
| `evaluate.py` | CLI, 설정/manifest 검증, 선택적 YOLO 추론, 이미지 단위 지표, CSV/JSON |
| `evaluation_config.example.json` | 경로·비밀정보 없는 실행 조건과 클래스 계약 |
| `dataset_manifest.example.csv` | 실제 정답을 만들지 않은 헤더 템플릿 |
| `tests/test_evaluate.py` | 임시 합성 이미지와 Mock 모델을 이용한 로직 테스트 |
| `.gitignore` | 이 디렉터리는 도구·지정 문서·예시만 추적하고 데이터·결과는 제외 |

설정은 YAML 대신 표준 라이브러리 JSON으로 읽는다. 추가 의존성 설치는 필요 없다.
입력 검사는 기존 기본 의존성 Pillow를 사용한다. 실제 추론 시에만 기존 선택 의존성
Ultralytics/PyTorch/OpenCV 환경을 사용한다. 기본 CI에서도 AI 패키지 없이 테스트 가능하다.

## 실행 방법

아래 명령은 **저장소 root**의 PowerShell 기준이다.

데이터가 없는 지금 실행 가능한 명령:

```powershell
backend/.venv/Scripts/python.exe backend/evaluation/evaluate.py --config backend/evaluation/evaluation_config.example.json --check-config
backend/.venv/Scripts/python.exe -m unittest discover -s backend/evaluation/tests -t backend -v
```

데이터 확보 후 다음 구조를 사용할 수 있다. `data`, `local`, `runs`는 Git 제외 대상이다.

```text
backend/evaluation/
  data/                         # 사용자 승인 후 취득한 이미지와 비공개 출처 기록
    source_register.md
  local/
    manifest.csv                # validation + test 전체 목록
    validation.json
    test.json
  runs/
    baseline-validation-001/
```

이미지·정답·이용조건 검수 후 manifest를 작성하고 예시 설정을 복사한다.
파일 해시는 `Get-FileHash -Algorithm SHA256` 등으로 구해 **소문자**로 기록한다.
`validation.json`은 split=validation, `test.json`은 split=test로 지정한다.
threshold를 낮추면 prediction_confidence_floor도 threshold 이하로 설정해야 한다.

실제 데이터가 있어야 실행하는 사전 검증(모델 deserialization·추론·결과 저장 없음):

```powershell
backend/.venv/Scripts/python.exe backend/evaluation/evaluate.py --config backend/evaluation/local/validation.json --model backend/best.pt --manifest backend/evaluation/local/manifest.csv --data-root backend/evaluation/data --validate-only
```

검수된 정답으로 validation 평가:

```powershell
backend/.venv/Scripts/python.exe backend/evaluation/evaluate.py --config backend/evaluation/local/validation.json --model backend/best.pt --manifest backend/evaluation/local/manifest.csv --data-root backend/evaluation/data --output backend/evaluation/runs/baseline-validation-001
```

고정한 조건으로 test 평가:

```powershell
backend/.venv/Scripts/python.exe backend/evaluation/evaluate.py --config backend/evaluation/local/test.json --model backend/best.pt --manifest backend/evaluation/local/manifest.csv --data-root backend/evaluation/data --output backend/evaluation/runs/baseline-test-001
```

정답 미검수 데이터는 `--predict-only`를 추가할 수 있다. 이용조건 검토·경로·해시 검사는
유지되며 성능 지표는 생성하지 않는다. 검수되지 않은 참고 이미지를 정식 평가로 넣지 않는다.
이미 존재하는 output 디렉터리는 덮어쓰지 않으므로 새 실행 ID를 사용한다.
데이터 root 내부에 결과를 쓰는 것도 차단한다.

## 입력·출력 계약

- config: schema v1, 알 수 없는 키/중복 JSON 키/잘못된 타입·범위 거부.
- 경로는 CLI로만 전달. 모델은 기존 local `.pt` 필수로 자동 모델 다운로드를 방지.
- 모든 split의 파일 해시·이미지 디코딩·원본/그룹 중복을 검사.
- 선택 split의 이용조건 미검토·알려진 학습 중복은 실행 거부.
- 점수 모드는 선택 split의 모든 정답·검수·근거 필수. 빈 데이터셋은 종료 코드 2.
- `--check-config`는 설정만 확인, `--validate-only`는 파일 입력만 확인한다.
  둘 모두 모델 로딩 성공이나 성능 평가를 뜻하지 않는다.
- confidence는 원시 0~1. 결과에 백분율로 저장하지 않는다.
- `report.json`: config, 모델/manifest/도구 SHA-256, 클래스 계약, 패키지 버전,
  OS/아키텍처, runtime, UTC 실행 시각, 모델 로딩 시간, 이미지별 정답·전체 반환 예측·최종 선택,
  출처/검수/라이선스 참조, 지표·분모·제약.
- `predictions.csv`: 동일 이미지별 레코드. target_labels와 boxes는 JSON 문자열 셀.
- 절대 모델/이미지 경로·원본 상대 파일명·환경변수·사용자명·API key는 결과에 쓰지 않는다.
  source/group/evidence ID도 사용자가 익명으로 작성해야 한다.
- 결과 생성 전 입력·모델·manifest 변경을 검사. 추론 실패는 성공 보고서를 만들지 않는다.
- `.pt`는 사용자 소유의 신뢰할 수 있는 체크포인트만 사용한다. 파일 존재 검증이
  pickle 안전성 검증을 뜻하지 않는다.

## 재현성·서비스와의 관계

예시 설정은 CPU, 640, TTA=true, threshold=0.6, 후보 floor=0.25, NMS IoU=0.7,
max_det=300, FP32, rect=true, batch=1이다. 최고 confidence 선택과 ID→질병 연결은
현재 서비스 계약을 따른다. 이름 목록이 달라지면 추론을 중단한다.
평가용 seed·deterministic 설정을 기록하며 비결정적 연산은 조용히 허용하지 않는다.
다른 하드웨어/패키지 버전에서 비트 단위 동일 결과를 보장하지 않는다.

추론은 YOLO 설정을 임시 디렉터리로 격리하고 offline 모드를 사용한다. 이미지 annotation,
학습, 데이터 변환, 네트워크 데이터 취득을 하지 않는다. Django API의 업로드·DB 저장·
이력·주석 이미지 동작은 이 평가의 측정 대상이 아니다. UI와 별도 정책으로 분기할 때는
향후 해당 차이를 계약 테스트로 검증해야 한다.

첫 predict 호출에는 초기화가 포함된다. 기록된 시간은 반복 측정의 p50/p95나 API 응답시간이
아니다. 비교는 동일 manifest·서비스 라벨·설정·환경에서 수행하고, 변경된 모델 hash와
threshold/TTA 차이를 보고서에 명시한다.

## 완료·개선 판단 기준

평가 준비 완료: 출처·조건·정답 근거 검수, 지원/정상/미지원/품질 층의 목록과 그룹 분할,
미확인 독립성 기록, 사전 검사 통과, 설정과 test 동결.

기준 평가 완료: 누락/오류 없이 전체 선택 split의 결과 저장, 분모·실패 사례 검토,
같은 조건 재실행 확인, 두 결과의 정답/예측 비교(타임스탬프·경과시간은 제외).
작은 표본이나 미확정 라벨을 근거로 절대적인 성능을 주장하지 않는다.

모델 개선 판단: 먼저 오류가 정답/매핑 문제인지 모델 오류인지 검수한다. 정상·미지원
오탐과 지원 질병 미탐 간 trade-off를 validation에서 확인한다. 사용자와 목표 오탐률·
재현율·CPU 지연 허용치를 사전에 정한 뒤, 고정 test에서 클래스별 회귀가 없는지 비교한다.
기존 클래스 의미가 끝내 복원되지 않으면 임의 재명명/병합 대신 근거가 명확한 새 학습
체계를 별도 제안한다. 본 도구와 이번 작업은 학습·파인튜닝을 수행하지 않는다.
