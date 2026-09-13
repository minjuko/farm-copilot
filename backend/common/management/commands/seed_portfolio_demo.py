from datetime import timedelta

from django.core.management import BaseCommand, call_command
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from chatbot.models import Chatbot
from community.models import Comment, Post
from detect.models import Pest, PestDetection
from prediction.models import PredictionResult, PredictionSession
from soil.models import CropData

DEMO_EMAILS = [
    'doyun.farm@example.com',
    'youngsoo.pepper@example.com',
    'junghui.greenhouse@example.com',
    'minseok.returnfarm@example.com',
]


class Command(BaseCommand):
    help = '촬영용 농업인 계정과 포트폴리오 샘플 데이터를 재생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='FarmDemo!2026')

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        User.objects.filter(email__in=DEMO_EMAILS).delete()
        call_command('loaddata', 'detect/fixtures/model_classes.json', verbosity=0)

        users = {}
        for email, username in [
            (DEMO_EMAILS[0], '김도윤'),
            (DEMO_EMAILS[1], '박영수'),
            (DEMO_EMAILS[2], '이정희'),
            (DEMO_EMAILS[3], '최민석'),
        ]:
            users[email] = User.objects.create_user(
                email=email, username=username, password=password
            )

        self._create_community(users)
        self._create_predictions(users[DEMO_EMAILS[0]])
        self._create_soil_history(users[DEMO_EMAILS[0]])
        self._create_detections(users[DEMO_EMAILS[0]])
        self._create_chats(users[DEMO_EMAILS[0]])

        self.stdout.write(self.style.SUCCESS('촬영용 샘플 데이터 생성 완료'))
        self.stdout.write(f'대표 계정: {DEMO_EMAILS[0]} / {password}')

    def _stamp(self, instance, field, days, hours=0):
        value = timezone.now() - timedelta(days=days, hours=hours)
        type(instance).objects.filter(pk=instance.pk).update(**{field: value})

    def _create_community(self, users):
        doy = users[DEMO_EMAILS[0]]
        park = users[DEMO_EMAILS[1]]
        lee = users[DEMO_EMAILS[2]]
        choi = users[DEMO_EMAILS[3]]
        posts = [
            (
                'buy',
                doy,
                '건고추 20kg 구매 희망합니다',
                '김장용 건고추를 알아보고 있습니다. 색이 선명하고 꼭지를 제거하지 않은 상태면 좋겠습니다. 완주나 전주 인근은 직접 가지러 갈 수 있습니다.',
                None,
            ),
            (
                'buy',
                choi,
                '전북 완주 로컬푸드용 애호박 모종 구합니다',
                '이번 주말에 정식할 애호박 모종 80주 정도 구합니다. 웃자라지 않고 뿌리가 잘 잡힌 모종이면 좋겠습니다.',
                None,
            ),
            (
                'buy',
                lee,
                '하우스용 점적호스 남는 분 계실까요',
                '20mm 점적호스 약 300m가 필요합니다. 한 철 사용한 제품도 누수만 없으면 괜찮습니다.',
                None,
            ),
            (
                'buy',
                doy,
                '볏짚 사각베일 30개 구합니다',
                '축사 깔짚으로 사용할 마른 볏짚을 구합니다. 김제·익산 지역이면 운반 일정 맞춰보겠습니다.',
                None,
            ),
            (
                'buy',
                choi,
                '퇴비 살포기 단기 대여 희망합니다',
                '밭 1,200평에 사용할 소형 퇴비 살포기를 이틀 정도 빌리고 싶습니다. 사용료와 운반 조건 알려주세요.',
                None,
            ),
            (
                'buy',
                park,
                '중고 관수 타이머 찾습니다',
                '하우스 두 동에 연결할 수 있는 관수 타이머 구합니다. 작동 확인 가능한 제품이면 좋겠습니다.',
                None,
            ),
            (
                'sell',
                park,
                '올해 수확한 건고추 판매합니다',
                '완주 봉동 노지에서 재배한 고추입니다. 수확 후 바로 세척하고 건조했습니다. 6kg 단위이며 직거래 우선입니다.',
                'post/demo/chili-harvest.png',
            ),
            (
                'sell',
                lee,
                '완숙 토마토 5kg 단위 판매',
                '하우스에서 완숙 수확한 토마토입니다. 크기가 조금 고르지 않지만 단단하고 맛이 좋습니다. 전주 로컬 직거래 가능합니다.',
                'post/demo/tomato-harvest.png',
            ),
            (
                'sell',
                park,
                '사용 횟수 적은 동력 관리기 판매',
                '로터리 포함 소형 관리기입니다. 봄가을 밭 갈 때만 사용했고 시동과 전진·후진 모두 정상입니다. 직접 보고 결정하셔도 됩니다.',
                'post/demo/used-tiller.png',
            ),
            (
                'sell',
                lee,
                '육묘 후 남은 고추와 가지 모종',
                '정식하고 남은 튼튼한 모종입니다. 고추 60주, 가지 30주 있으며 소량도 가능합니다.',
                'post/demo/seedling-trays.png',
            ),
            (
                'sell',
                doy,
                '직접 말린 무농약 시래기 판매합니다',
                '겨울 바람에 자연 건조한 시래기입니다. 한 묶음씩 손질해 두었고 필요하면 삶아서 드릴 수도 있습니다.',
                None,
            ),
            (
                'sell',
                choi,
                '감자 수확용 망과 상자 정리합니다',
                '작년에 한 번 사용한 감자망 100장과 플라스틱 상자 12개입니다. 일괄 구매하시면 가격 조정하겠습니다.',
                None,
            ),
            (
                'exchange',
                doy,
                '감자 종서와 고구마 순 교환 원합니다',
                '남은 수미 감자 종서 10kg이 있습니다. 꿀고구마 순과 교환하고 싶습니다. 전주 북부권에서 만나면 좋겠습니다.',
                None,
            ),
            (
                'exchange',
                lee,
                '청양고추 모종과 가지 모종 교환',
                '청양고추 모종이 40주 정도 남았습니다. 가지나 대추방울토마토 모종과 비슷한 수량으로 교환 원합니다.',
                'post/demo/seedling-trays.png',
            ),
            (
                'exchange',
                park,
                '남은 멀칭비닐을 유인끈과 교환합니다',
                '폭 90cm 검정 멀칭비닐 한 롤이 남았습니다. 하우스용 유인끈이나 집게와 교환하고 싶습니다.',
                None,
            ),
            (
                'exchange',
                choi,
                '소형 농기구 서로 교환하실 분',
                '여분 호미와 쇠스랑이 있습니다. 전지가위나 삽과 교환 가능합니다. 상태는 사진으로 먼저 확인해 드립니다.',
                None,
            ),
            (
                'exchange',
                doy,
                '완주 로컬푸드 출하 정보 공유합니다',
                '올해 처음 출하를 준비하고 있습니다. 포장 규격과 오전 입고 시간 관련 경험을 나눌 분을 찾습니다.',
                None,
            ),
            (
                'exchange',
                lee,
                '장마 전 공동 방제 일정 맞추실 분',
                '인근 하우스 농가끼리 장마 전 방제 날짜를 맞추면 좋겠습니다. 백구면 주변 농가 연락 부탁드립니다.',
                None,
            ),
        ]
        made = []
        for index, (kind, owner, title, content, image) in enumerate(posts):
            post = Post.objects.create(
                user=owner, post_type=kind, title=title, content=content, image=image
            )
            self._stamp(post, 'creation_date', 18 - index)
            made.append(post)

        comments = [
            (0, park, '저희 농장 건고추가 있습니다. 10kg씩 나눠서도 가능합니다.', None),
            (0, doy, '색과 건조 상태 확인하고 싶습니다. 주말에 방문 가능할까요?', 0),
            (1, lee, '모종이 조금 남았습니다. 봉동 쪽이면 토요일 오전에 전달 가능합니다.', None),
            (3, park, '김제 백구면에 20개 있습니다. 운반 차량만 준비하시면 됩니다.', None),
            (6, doy, '혹시 12kg 구매하면 가격 조정이 가능할까요?', None),
            (6, park, '네, 직접 오시면 조금 맞춰드리겠습니다.', 4),
            (7, choi, '토마토가 단단해 보이네요. 이번 금요일 10kg 예약 가능할까요?', None),
            (8, doy, '관리기 연식과 최근 엔진오일 교환 시기를 알 수 있을까요?', None),
            (8, park, '2019년식이고 지난봄에 엔진오일 교환했습니다.', 7),
            (9, choi, '귀농 첫해라 모종이 필요합니다. 고추 20주만도 가능할까요?', None),
            (12, lee, '꿀고구마 순이 다음 주에 나옵니다. 수량 맞춰 연락드릴게요.', None),
            (16, park, '봉동 출하장은 오전 8시 전 입고가 가장 수월했습니다.', None),
            (17, doy, '저도 일정 맞추겠습니다. 비 예보 이틀 전쯤 다시 연락하시죠.', None),
            (
                2,
                park,
                '사용한 호스라도 연결 부위만 괜찮으면 제가 150m 정도 나눌 수 있습니다.',
                None,
            ),
            (2, lee, '감사합니다. 규격 확인해서 쪽지 드리겠습니다.', 13),
            (4, lee, '농협 임대사업소도 예약 확인해 보세요. 평일은 자리가 종종 있습니다.', None),
            (5, doy, '배터리식인가요, 전원 연결식인가요?', None),
            (10, park, '삶지 않은 시래기 두 묶음 예약하고 싶습니다.', None),
            (11, doy, '상자만 5개 따로 구매할 수 있을까요?', None),
            (13, choi, '대추방울토마토 20주와 교환 가능합니다.', None),
            (13, lee, '좋습니다. 뿌리 상태 사진 보내드리고 장소 정하겠습니다.', 19),
            (14, doy, '유인끈 새것 한 타래가 있는데 멀칭비닐 폭이 맞으면 교환하고 싶습니다.', None),
            (15, park, '전지가위 여분이 있습니다. 쇠스랑 상태가 궁금합니다.', None),
            (16, choi, '포장재는 출하장 공동구매 때 신청하면 단가가 조금 낮았습니다.', None),
            (17, choi, '백구면 쪽 세 농가가 함께하고 있습니다. 일정 정해지면 알려드릴게요.', None),
        ]
        made_comments = []
        for post_index, owner, content, parent_index in comments:
            parent = made_comments[parent_index] if parent_index is not None else None
            comment = Comment.objects.create(
                post=made[post_index], user=owner, content=content, parent=parent
            )
            self._stamp(comment, 'created_at', max(0, 12 - len(made_comments)), 2)
            made_comments.append(comment)

    def _create_predictions(self, user):
        sessions = [
            (
                'demo-prediction-pepper-2026',
                '2026년 노지 고추 재배 계획',
                '고추, 대파',
                900,
                '대전',
                [('고추', 7420000, 4100), ('대파', 2860000, 2350)],
            ),
            (
                'demo-prediction-greenhouse-2026',
                '시설채소 수익 비교',
                '토마토, 오이',
                600,
                '광주',
                [('토마토', 9850000, 3850), ('오이', 6240000, 2180)],
            ),
            (
                'demo-prediction-field-2026',
                '밭작물 전환 검토',
                '감자, 고구마',
                1200,
                '대구',
                [('감자', 5360000, 1680), ('고구마', 7180000, 2940)],
            ),
        ]
        for offset, (sid, name, crops, area, region, results) in enumerate(sessions):
            session = PredictionSession.objects.create(
                user=user,
                session_id=sid,
                session_name=name,
                crop_names=crops,
                land_area=area,
                region=region,
                total_income=sum(r[1] for r in results),
            )
            self._stamp(session, 'created_at', 21 - offset * 7)
            crop_ratio = 1 / len(results)
            for crop, income, price in results:
                management_cost = int(income * 0.72)
                hired_labor = int(income * 0.09)
                machinery_rent = int(income * 0.07)
                land_rent = int(income * 0.08)
                outsourced_farming = int(income * 0.03)
                adjusted = {
                    '작물명': crop,
                    '시점': 2025,
                    '총수입 (원)': income + management_cost,
                    '총경영비': management_cost,
                    '소득 (원)': income,
                    '자가노동비': int(income * 0.16),
                    '고용노동비': hired_labor,
                    '농약비': int(income * 0.035),
                    '초기투자비용': int(income * 0.08),
                    '보통(무기질)비료비': int(income * 0.045),
                    '부산물(유기질)비료비': int(income * 0.025),
                    '기타재료비': int(income * 0.03),
                    '수도광열비': int(income * 0.025),
                    '수리·유지비': int(income * 0.02),
                    '농기계·시설 임차료': machinery_rent,
                    '토지임차료': land_rent,
                    '위탁영농비': outsourced_farming,
                    '총중간재비': management_cost - hired_labor - machinery_rent - land_rent - outsourced_farming,
                    '기타비용': int(income * 0.015),
                }
                PredictionResult.objects.create(
                    session=session,
                    crop_name=crop,
                    crop_ratio=crop_ratio,
                    predicted_income=income,
                    adjusted_data=adjusted,
                    price=price,
                    latest_year=2025,
                    r2_score=0.82,
                    rmse=187.4,
                )

    def _create_soil_history(self, user):
        rows = [
            (
                'demo-soil-pepper',
                '고추',
                '전북특별자치도 완주군 봉동읍',
                '전북특별자치도 완주군 봉동읍 농원길 24',
                {
                    'PNU_Nm': '완주군 봉동읍 장기리 218-3',
                    'ACID': '6.4',
                    'OM': '27',
                    'VLDPHA': '382',
                    'POSIFERT_K': '0.72',
                    'POSIFERT_CA': '6.1',
                    'POSIFERT_MG': '1.8',
                    'VLDSIA': '118',
                    'SELC': '1.2',
                },
            ),
            (
                'demo-soil-tomato',
                '토마토',
                '전북특별자치도 김제시 백구면',
                '전북특별자치도 김제시 백구면 영상리 311-2',
                {
                    'PNU_Nm': '김제시 백구면 영상리 311-2',
                    'ACID': '6.8',
                    'OM': '34',
                    'VLDPHA': '612',
                    'POSIFERT_K': '0.91',
                    'POSIFERT_CA': '7.4',
                    'POSIFERT_MG': '2.2',
                    'VLDSIA': '145',
                    'SELC': '2.1',
                },
            ),
            (
                'demo-soil-potato',
                '감자',
                '강원특별자치도 평창군 진부면',
                '강원특별자치도 평창군 진부면 하진부리 187',
                {
                    'PNU_Nm': '평창군 진부면 하진부리 187',
                    'ACID': '5.7',
                    'OM': '19',
                    'VLDPHA': '245',
                    'POSIFERT_K': '0.48',
                    'POSIFERT_CA': '4.3',
                    'POSIFERT_MG': '1.1',
                    'VLDSIA': '96',
                    'SELC': '0.7',
                },
            ),
        ]
        for offset, (sid, crop, address, detail, soil) in enumerate(rows):
            fertilizer = {
                'pre_Fert_N': '8.6',
                'pre_Fert_P': '7.2',
                'pre_Fert_K': '5.4',
                'post_Fert_N': '4.1',
                'post_Fert_P': '0',
                'post_Fert_K': '3.2',
                'pre_Compost_Cattl': '180',
                'pre_Compost_Pig': '140',
                'pre_Compost_Chick': '95',
                'pre_Compost_Mix': '160',
            }
            row = CropData.objects.create(
                user_id=user.id,
                session_id=sid,
                crop_name=crop,
                address=address,
                detailed_address=detail,
                soil_data=soil,
                fertilizer_data=fertilizer,
            )
            self._stamp(row, 'created_at', 14 - offset * 5)

    def _create_detections(self, user):
        rows = [
            ('PEPPER_ANTHRACNOSE', 91.1, 'pest_detections/demo/pepper-anthracnose.png', 12),
            ('TOMATO_POWDERY_MILDEW', 87.6, 'pest_detections/demo/tomato-powdery-mildew.png', 7),
            ('CUCUMBER_DOWNY_MILDEW', 94.3, 'pest_detections/demo/cucumber-downy-mildew.png', 2),
        ]
        for code, confidence, image, days in rows:
            PestDetection.objects.create(
                user=user,
                pest=Pest.objects.get(code=code),
                confidence=confidence,
                image=image,
                detection_date=timezone.now() - timedelta(days=days),
            )

    def _create_chats(self, user):
        sessions = [
            (
                'demo-chat-pepper',
                '고추 탄저병 예방 방법',
                [
                    (
                        '고추 열매에 검은 반점이 생겼는데 탄저병일 가능성이 있나요?',
                        '과실에 물에 젖은 듯한 움푹한 원형 반점이 생기고 점차 검게 번진다면 탄저병을 의심할 수 있습니다. 병든 과실은 바로 제거하고 주변 포장으로 옮기지 않는 것이 좋습니다.',
                    ),
                    (
                        '장마가 시작되기 전에 어떤 방제를 해두는 게 좋을까요?',
                        '배수로를 정비하고 포기 사이 통풍을 확보하세요. 비가 오기 전 보호살균제를 사용하고, 비가 그친 뒤에는 등록약제의 안전사용기준에 따라 방제하는 것이 좋습니다.',
                    ),
                ],
            ),
            (
                'demo-chat-tomato',
                '토마토 웃거름 주는 시기',
                [
                    (
                        '토마토 첫 화방 착과 후 웃거름은 언제 주는 게 좋나요?',
                        '첫 화방의 열매가 탁구공 크기 정도 되었을 때 생육 상태를 확인한 뒤 첫 웃거름을 주는 방식이 일반적입니다.',
                    ),
                    (
                        '질소를 많이 주면 열매가 더 잘 크나요?',
                        '질소가 지나치면 줄기와 잎만 무성해지고 착과가 불량해질 수 있습니다. 토양검정 결과와 초세를 보고 소량씩 나누어 주는 것이 안전합니다.',
                    ),
                ],
            ),
            (
                'demo-chat-rainy',
                '장마철 시설하우스 관리',
                [
                    (
                        '비가 계속 올 때 하우스 환기는 어떻게 해야 하나요?',
                        '비가 들이치지 않는 범위에서 측창과 천창을 짧게라도 열어 습도를 낮추세요. 순환팬을 함께 사용하면 잎 표면이 젖어 있는 시간을 줄이는 데 도움이 됩니다.',
                    ),
                    (
                        '장마 뒤 가장 먼저 확인할 것은 무엇인가요?',
                        '배수 상태와 뿌리 활력을 먼저 확인하고 병든 잎을 제거하세요. 흐린 날이 이어졌다면 갑자기 강한 햇빛에 노출되지 않도록 차광도 단계적으로 조절하는 것이 좋습니다.',
                    ),
                ],
            ),
        ]
        for session_offset, (sid, name, messages) in enumerate(sessions):
            for message_offset, (question, answer) in enumerate(messages):
                chat = Chatbot.objects.create(
                    user=user,
                    session_id=sid,
                    session_name=name,
                    question_content=question,
                    answer_content=answer,
                )
                self._stamp(chat, 'created_at', 9 - session_offset * 3, -message_offset)
