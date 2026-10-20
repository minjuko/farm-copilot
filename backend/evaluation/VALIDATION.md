# 평가 도구 검증 기록 — 2026-10-20

## 실행한 검사

| 검사 | 결과 |
|---|---|
| 평가 도구 unittest, 합성 Pillow 이미지·Mock predictor | 32개 통과 |
| Django 전체 테스트, SQLite 임시 테스트 DB | 170개 통과 |
| 설정 CLI `--check-config` | 정상: 설정만 검사하고 모델/데이터/지표 사용 안 함 |
| Ruff check 및 format check (`backend/pyproject.toml`) | 통과 |
| `git diff --check` | 통과 |
| 실제 가중치 추론·평가셋 성능 측정 | **수행하지 않음. 정답 데이터셋이 없음** |

평가 도구 테스트는 config의 중복 키·필드·범위·자료형, manifest header와 빈 split,
경로 탈출·누락·손상 이미지·해시·중복 파일·그룹 교차, 검수/라이선스/학습 중복 상태,
class ID와 confidence, 0.6 경계·최고 confidence, 다중 클래스 서비스 매핑,
정상/미지원 오탐 분모, 0분모 null, 미탐지 abstention, quality 분리,
정답 없는 predict-only의 metrics 부재, YOLO adapter 추론 인자, 모델/가중치 보존,
기존 출력 덮어쓰기 방지, 부분 보고서 미생성, 오류 메시지 경로 노출 방지를 확인한다.

평가 도구 변경은 `backend/evaluation/` 안에 한정했다. 기존 모델 파일과 두 로컬 DB의
SHA-256은 실행 전후 같았다. 임시 서비스 테스트 DB는 `:memory:`에서 만들고 테스트가
종료될 때 제거됐다. 실제 학습·외부 다운로드·fixture load·서비스 DB 기록은 없었다.

## 실제 데이터 준비 후

평가를 시작하려면 이미지와 정답 외에도 출처/버전, 이용 승인 범위, 코드북·정답 근거,
식물/촬영 원본 그룹, augmentation provenance, 학습셋과의 overlap 검토가 필요하다.
이 자료 중 하나라도 모르면 해당 필드에 `unknown`/`pending`을 정직하게 유지하고,
평가 도구의 실행 차단 메시지를 임의로 우회하지 않는다.

도구 테스트 재실행:

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/evaluation/tests -t backend -v
```

전체 백엔드 테스트:

```powershell
$env:DJANGO_SECRET_KEY='evaluation-tests-only-not-a-production-secret'
$env:DJANGO_DEBUG='true'
$env:DJANGO_USE_SQLITE='true'
$env:SQLITE_DATABASE_PATH=':memory:'
$env:DJANGO_USE_S3='false'
Push-Location backend
try {
  ./.venv/Scripts/python.exe manage.py test --noinput
} finally {
  Pop-Location
}
```

실제 모델 평가는 수집·검수된 로컬 manifest와 데이터 경로를 지정한 뒤
[README 실행 절차](README.md)를 따른다. 결과의 metric scope는 서비스 매핑의 이미지
단위 평가다. mAP와 6개 원시 클래스의 의미 성능은 포함하지 않는다.
