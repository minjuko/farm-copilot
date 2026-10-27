# 챗봇 운영·개인정보 경계

## 기능과 외부 서비스 경계

`CHATBOT_ENABLED` 기본값은 `false`입니다. 챗봇을 활성화하려면 운영자가 명시적으로 켜고 `OPENAI_API_KEY`, 선택 AI 런타임, 로컬 Chroma DB와 manifest를 제공해야 합니다. 질문과 최근 대화는 LangChain retrieval chain을 거쳐 OpenAI의 `ChatOpenAI`로 전송됩니다. Index 생성 명령도 `OPENAI_API_KEY`가 있어야 임베딩 API를 호출합니다. 이 저장소의 기본 테스트는 Mock을 사용하며 유료 호출을 하지 않습니다.

런타임 계약은 `chromadb==0.5.0`, `langchain==0.2.7`, `langchain-community==0.2.7`, `langchain-core==0.2.18`, `langchain-openai==0.1.15`, `openai==1.35.7`입니다. 기본 모델 설정은 `gpt-4o-mini`, `text-embedding-3-small`, 컬렉션 `agriculture-knowledge`입니다. 검색은 최대 3개 문서를 사용합니다. 각 LLM 요청 timeout은 20초, SDK 자동 재시도는 꺼져 있으며 답변은 최대 512 output tokens로 제한됩니다. 히스토리 기반 질의는 질의 재작성과 답변 생성으로 두 번 호출될 수 있어 총 처리시간은 20초를 넘을 수 있습니다. Frontend Axios timeout은 50초입니다.

`/selfchatbot/status/`와 `/api/capabilities/`는 공통 readiness 검사를 사용합니다: feature flag, 키 존재 여부, 선택 런타임 import, DB 파일 및 manifest의 collection·embedding·문서 수·source hash 형식입니다. 이는 외부 OpenAI 가용성이나 결제 승인, 실제 질의 성공을 시험하지 않습니다. Index 손상, 차원 불일치 또는 provider 장애는 실제 요청에서야 드러날 수 있습니다. 상태 endpoint를 확인해도 외부 API 호출은 발생하지 않습니다.

## RAG 데이터와 재현성

Index 생성 입력은 `backend/chatbot/chatbot_source.csv`이며 `python manage.py build_chatbot_index --validate-only`는 파일 구조만 검증합니다. 실제 인덱싱에는 OpenAI embedding 요청이 발생하므로 운영자가 별도 실행을 승인해야 합니다. Index DB와 manifest는 `.gitignore` 대상입니다. 현재 로컬 manifest에는 8개 문서, `text-embedding-3-small`, `agriculture-knowledge`가 기록되어 있고 소스 CSV 해시도 일치했습니다. 로컬 Chroma가 같은 컬렉션을 열고 8개 레코드를 반환했지만, 이 확인은 검색 품질 또는 OpenAI 응답 검증이 아닙니다.

현재 runtime은 manifest의 source hash 형식만 검사합니다. 원본 CSV와 hash를 매 요청마다 대조하지 않으며, manifest만으로 임베딩 차원·컬렉션 내 모든 벡터·문서 metadata의 무결성을 확인하지 않습니다. 로컬 DB와 manifest가 있어 재구성 입력은 확인 가능하지만, 생성 시점의 API 응답과 임베딩 결과를 bitwise 재현할 수는 없습니다.

검색 문서는 untrusted reference data로 취급하라는 지시를 QA system prompt에 넣었습니다. 이는 prompt-level 방어이며 모델이 문서 안의 악의적 지시를 항상 무시한다는 보장은 아닙니다. 생성 응답은 HTML로 해석하지 않고 텍스트로 반환합니다. Source metadata는 현재 사용자 응답에 포함되지 않습니다.

검색 결과가 비어 있으면 답변을 저장하지 않고 404를 반환하며, metadata에 출처명과 HTTPS URL이 없는 검색 문서는 503으로 처리합니다. 이 상황은 Frontend에서 출처 자료를 찾지 못했다는 안내로 표시합니다.

## 개인정보, 보존, 소유권

질문과 답변은 `Chatbot` 행으로 저장되고 사용자 계정에 연결됩니다. 세션 목록·이력·삭제는 로그인 사용자의 행으로 제한됩니다. 계정 삭제 시 사용자 외래키 cascade가 적용됩니다. 세션 삭제와 사용자 전체 로그 삭제 endpoint가 있지만 자동 보존 기한이나 만료 작업은 없습니다. 따라서 삭제 요청이나 계정 삭제 전까지 대화 기록이 남을 수 있습니다.

챗봇을 사용할 수 있는 상태일 때 UI는 질문과 이전 대화가 답변 생성을 위해 OpenAI로 전송되고 계정 이력에 저장된다는 점을 알립니다. 민감정보 입력을 피하도록 안내합니다. PII 자동 탐지·마스킹은 구현되어 있지 않습니다. 대화 전체 대신 최근 5개 turn만 모델 문맥으로 전달하지만, DB에는 기존 대화 전체를 보존합니다.

Provider 예외의 메시지와 traceback은 챗봇 초기화·요청·이력 조회 로그에 기록하지 않습니다. API 오류는 일반화된 503으로 응답합니다. 운영 로그 수집기와 프록시의 별도 요청-body 로깅 여부는 저장소만으로 확인할 수 없습니다.

## 비용·장애 통제와 한계

- 기본 비활성화 및 `CHATBOT_ENABLED=true`의 운영자 opt-in을 유지합니다.
- 요청 본문은 최대 16 KiB, 질문은 최대 2,000자입니다. 문맥은 최근 5개 turn으로 제한하고 답변은 512 output tokens로 제한합니다.
- Provider 요청 timeout은 20초이며 SDK 재시도는 꺼져 있습니다. 이력 기반 질의에서는 LLM 호출이 최대 두 번 발생할 수 있습니다.
- 브라우저 탭에서는 요청 중 중복 제출을 막지만 서버 전체·사용자별 rate limit, 동시성 제한, 일일 비용 한도는 구현되어 있지 않습니다.
- OpenAI 장애·timeout은 상세 예외를 숨긴 503으로 응답합니다. 정상/실패 모두 외부 API로 실제 검증하지 않았습니다.
- Feature flag, 키, index를 바꾸어도 실행 중인 process의 기존 OpenAI client를 즉시 회수하지 않습니다. 설정 변경·키 폐기 후에는 앱 process를 재시작해야 합니다. flag/key/index/runtime 준비조건은 cached chain 반환 전에 재검사합니다.

회귀 검증은 Django test database와 Mock provider에서 수행합니다. 실제 OpenAI API, embedding API, 원격 데이터 다운로드는 호출하지 않습니다.
