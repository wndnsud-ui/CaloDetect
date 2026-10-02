import os  # 운영체제 파일 경로 및 존재 여부 확인용 라이브러리 임포트
import random  # 가상 데이터 생성 시 무작위 값 추출용 라이브러리 임포트
from datetime import datetime, timedelta  # 날짜 및 시간 계산용 라이브러리 임포트
from data_config import APP_DIR, MODEL_PATH, load_class_names, load_nutrition_frame  # 모델 클래스 설정(YAML) 파일을 읽기 위한 라이브러리 임포트
import streamlit as st  # 웹 UI 및 대시보드 구성을 위한 Streamlit 프레임워크 임포트
import pandas as pd  # 식단 데이터 테이블 관리 및 그룹화 연산용 판다스 라이브러리 임포트
from PIL import Image, ImageDraw  # 업로드된 이미지 열기 및 바운딩 박스 드로잉용 라이브러리 임포트
from ultralytics import YOLO  # 객체 탐지 비전 AI 모델 구동을 위한 라이브러리 임포트
from streamlit_echarts import st_echarts  # Apache ECharts 5 차트를 Streamlit에서 렌더링하기 위한 컴포넌트 임포트

# [1] 웹 페이지 기본 설정
st.set_page_config(
    page_title="AI 맞춤형 식단 다이어리 & 대시보드",  # 브라우저 탭에 표시되는 서비스 타이틀 설정
    page_icon="🥗",                            # 브라우저 탭 아이콘 설정
    layout="wide"                              # 화면 전체를 넓게 사용하는 와이드 모드 레이아웃 적용
)


# [2] 고급 건강검진 / 영양분석 서비스 스타일 (불필요한 접두사 제거 및 가독성 개선)
st.markdown(
    """
    <style>
        /* 헬스케어 엔터프라이즈 테마 전용 CSS 변수 선언 (직관적인 이름 사용) */
        :root {
            --navy: #16324F;       /* 앱 전체의 핵심 브랜드 컬러인 딥 네이비 색상 */
            --blue: #2F5B7C;       /* 보조 포인트 컬러로 사용되는 블루 색상 */
            --teal: #238A8D;       /* 헬스케어 감성을 주는 틸(청록) 포인트 색상 */
            --bg: #F6F8FA;         /* 애플리케이션 전체 배경의 부드러운 연회색 */
            --surface: #FFFFFF;    /* 카드 및 컨테이너 박스의 배경이 되는 순백색 */
            --border: #E2E8ED;     /* 컴포넌트 테두리 경계선의 은은한 회색 */
            --text: #243746;       /* 화면에 표시되는 기본 본문 텍스트 색상 */
            --muted: #71808C;      /* 강조도가 낮은 보조 텍스트 및 레이블의 색상 */
            --soft: #EEF6F6;       /* 태그나 소프트 배경에 쓰이는 연한 틸 계열 색상 */
        }

        /* 전역 레이아웃 및 기본 폰트 설정 */
        html, body, [class*="css"] {
            font-family: 'Noto Sans KR', sans-serif;  /* 앱 전체 기본 폰트 지정 */
        }

        .stApp {
            background: var(--bg);     /* 앱 전역 배경색 적용 */
            color: var(--text);        /* 앱 전역 기본 텍스트 색상 적용 */
        }

        [data-testid="stHeader"] {
            background: rgba(246, 248, 250, 0.96);  /* 상단 헤더 배경색 */
        }

        [data-testid="stSidebar"] {
            background: #FFFFFF;                     /* 사이드바 배경을 흰색으로 고정 */
            border-right: 1px solid var(--border);   /* 사이드바 우측 경계선 */
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.25rem;                    /* 사이드바 상단 여백 조절 */
        }

        .block-container {
            max-width: 1480px;                       /* 메인 대시보드 최대 가로 폭 제한 */
            padding: 1.7rem 2.2rem 3rem;             /* 컨테이너 내부 패딩 설정 */
        }

        /* 타이틀 및 섹션 헤더 타이포그래피 스타일링 */
        h1, h2, h3 {
            color: var(--navy) !important;           /* 주요 제목 색상을 네이비로 강제 고정 */
            font-weight: 800 !important;             /* 제목 폰트 두께를 매우 두껍게 설정 */
            letter-spacing: -0.035em;                /* 자간을 좁혀 모던한 느낌 연출 */
        }

        h1 {
            font-size: 2rem !important;              /* 최상단 메인 타이틀 크기 */
            margin-bottom: 0.25rem !important;       /* 하단 여백 축소 */
        }

        h2 {
            font-size: 1.35rem !important;           /* 중간 타이틀 크기 */
        }

        h3 {
            font-size: 1.05rem !important;           /* 소제목 크기 */
        }

        .page-kicker {
            color: var(--teal);                      /* 상단 소형 레이블 컬러 */
            font-size: 0.72rem;                      /* 폰트 크기 작게 설정 */
            font-weight: 800;                        /* 폰트 두께 강조 */
            letter-spacing: 0.14em;                  /* 자간을 넓혀 세련된 감성 부여 */
            margin-bottom: 0.45rem;                  /* 하단 여백 설정 */
        }

        .page-description {
            color: var(--muted);                     /* 설명 문구 보조 색상 */
            font-size: 0.9rem;                       /* 폰트 크기 설정 */
            line-height: 1.6;                        /* 줄 간격 확보 */
            margin-bottom: 1.25rem;                  /* 하단 여백 설정 */
        }

        .section-title {
            color: var(--navy);                      /* 섹션 타이틀 네이비 색상 */
            font-size: 0.9rem;                       /* 폰트 크기 */
            font-weight: 800;                        /* 폰트 두께 */
            letter-spacing: 0.05em;                  /* 자간 설정 */
            margin: 1.35rem 0 0.7rem;                /* 상하 마진 설정 */
            text-transform: uppercase;               /* 알파벳 대문자 변환 */
        }

        /* 사이드바 브랜드 로고 및 서브타이틀 디자인 */
        .sidebar-brand {
            color: var(--navy);                      /* 브랜드 네이비 색상 */
            font-size: 1.2rem;                       /* 로고 글자 크기 */
            font-weight: 800;                        /* 굵게 설정 */
            letter-spacing: -0.03em;                 /* 자간 좁힘 */
        }

        .sidebar-sub {
            color: #84919A;                          /* 서브 타이틀 연한 회색 */
            font-size: 0.72rem;                      /* 작은 글자 크기 */
            margin: 2px 0 18px;                      /* 상하 마진 */
        }

        /* 카드 형태 컴포넌트 디자인 (박스 그림자 및 곡선 테두리) */
        .health-card, .enterprise-card, .report-box {
            background: var(--surface);              /* 카드 배경 순백색 */
            border: 1px solid var(--border);         /* 테두리선 회색 */
            border-radius: 12px;                     /* 모서리 둥글게 처리 */
            box-shadow: 0 2px 10px rgba(22, 50, 79, 0.035); /* 은은한 입체 그림자 */
        }

        .health-card {
            padding: 18px 20px;                      /* 헬스케어 카드 내부 패딩 */
        }

        .report-box {
            padding: 18px 20px;                      /* 리포트 박스 내부 패딩 */
            margin: 0.5rem 0 1rem;                   /* 상하 마진 설정 */
        }

        .report-title {
            color: var(--navy);                      /* 리포트 제목 네이비 색상 */
            font-size: 0.92rem;                      /* 폰트 크기 */
            font-weight: 800;                        /* 폰트 두께 */
            margin-bottom: 7px;                      /* 하단 여백 */
        }

        .report-text {
            color: #647480;                          /* 리포트 본문 회색조 컬러 */
            font-size: 0.83rem;                      /* 폰트 크기 */
            line-height: 1.7;                        /* 줄 간격 설정 */
        }

        /* KPI 메트릭 카드 라벨 및 수치 디자인 */
        .metric-label {
            color: var(--muted);                     /* 지표 레이블 보조 회색 */
            font-size: 0.72rem;                      /* 폰트 크기 작게 */
            font-weight: 700;                        /* 폰트 두께 */
            letter-spacing: 0.07em;                  /* 자간 넓힘 */
            text-transform: uppercase;               /* 대문자 변환 */
        }

        .metric-value {
            color: var(--navy);                      /* 핵심 숫자 네이비 컬러 */
            font-size: 1.75rem;                      /* 큼직한 폰트 크기 */
            font-weight: 800;                        /* 매우 두껍게 */
            line-height: 1.1;                        /* 줄 높이 타이트하게 */
            margin-top: 7px;                         /* 상단 마진 */
        }

        .metric-unit {
            color: #6D7C87;                          /* 단위(kcal, g) 중간 채도 회색 */
            font-size: 0.8rem;                       /* 단위 폰트 크기 */
            font-weight: 500;                        /* 적당한 두께 */
            margin-left: 3px;                        /* 숫자와 단위 간격 */
        }

        .metric-note, .small-muted {
            color: #87949E;                          /* 보조 설명 연한 회색 */
            font-size: 0.7rem;                       /* 아주 작은 폰트 크기 */
            margin-top: 7px;                         /* 상단 마진 */
        }

        /* 영양 상태 평가 상태별 텍스트 색상 클래스 */
        .status-good {
            color: var(--teal);                      /* 양호 상태 틸 그린 컬러 */
            font-weight: 700;                        /* 굵게 */
        }

        .status-warning {
            color: #A46A00;                          /* 주의 상태 오렌지빛 브라운 */
            font-weight: 700;                        /* 굵게 */
        }

        .tag {
            display: inline-block;                   /* 인라인 블록 배치 */
            background: var(--soft);                 /* 연한 소프트 배경 */
            color: #237779;                          /* 진한 청록색 글자 */
            border: 1px solid #D5EAEA;               /* 연한 테두리선 */
            padding: 4px 8px;                        /* 내부 패딩 */
            border-radius: 999px;                    /* 완전한 알약 형태 */
            font-size: 0.72rem;                      /* 폰트 크기 */
            font-weight: 700;                        /* 굵게 */
            margin: 2px 3px 2px 0;                   /* 주변 마진 */
        }

        /* 버튼 및 입력 폼 UI 컴포넌트 디자인 설정 */
        .stButton > button, .stDownloadButton > button {
            border-radius: 8px;                      /* 버튼 모서리 둥글게 */
            font-weight: 700;                        /* 버튼 글자 굵게 */
            border: 1px solid var(--border);         /* 버튼 테두리선 지정 */
        }

        [data-testid="stFileUploader"] {
            background: #FFFFFF;                     /* 업로더 박스 배경 흰색 */
            border: 1px dashed #C8D4DC;              /* 세련된 점선 테두리 */
            border-radius: 10px;                     /* 모서리 둥글게 */
        }

        [data-testid="stMetric"] {
            background: #FFFFFF;                     /* 메트릭 박스 배경 흰색 */
            border: 1px solid var(--border);         /* 테두리선 지정 */
            border-radius: 10px;                     /* 모서리 둥글게 */
            padding: 12px 14px;                      /* 내부 패딩 */
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--border);         /* 데이터프레임 테두리 */
            border-radius: 10px;                     /* 모서리 둥글게 */
            overflow: hidden;                        /* 테두리 밖 내용 숨김 */
        }

        div[data-baseweb="select"] > div, 
        div[data-baseweb="input"] > div {
            border-radius: 8px;                      /* 입력창 모서리 둥글게 */
        }

        hr {
            border: 0;                               /* 기본 구분선 스타일 초기화 */
            border-top: 1px solid var(--border);     /* 상단 커스텀 테두리선 지정 */
            margin: 1.2rem 0;                        /* 상하 마진 설정 */
        }
    </style>
    """,
    unsafe_allow_html=True
)


# [3] CSV 영양 데이터 로드 및 정제 함수
@st.cache_data  # 동일한 파일 경로와 수정 시각일 경우 결과를 캐싱하여 로딩 속도 최적화
def load_nutrition_db(csv_path, csv_modified_time):
    
    nutrition_df = load_nutrition_frame(csv_path)

    return {
        row["food_name"]: {
            "category": row["category"],
            "unit": row["unit"],
            "cal": row["cal"],
            "carbs": row["carbs"],
            "protein": row["protein"],
            "fat": row["fat"],
            "sugar": row["sugar"],
            "sodium": row["sodium"]
        }
        for _, row in nutrition_df.iterrows()
    }


# 영양 데이터베이스 CSV 파일 경로 조합 및 존재 여부 검증
NUTRITION_CSV_PATH = os.path.join(
    os.path.dirname(__file__), 
    "CaloDetect_nutrition_all_matched.csv"
)

if not os.path.exists(NUTRITION_CSV_PATH):
    raise FileNotFoundError(f"영양 데이터 CSV 파일이 없습니다: {NUTRITION_CSV_PATH}")

# 영양 데이터 로드 함수 호출 (파일 수정 시각을 인자로 전달해 캐시 무효화 제어)
NUTRITION_DB = load_nutrition_db(
    NUTRITION_CSV_PATH,
    os.path.getmtime(NUTRITION_CSV_PATH)
)

# [4] 비전 AI 모델 로드 및 추론 함수
@st.cache_resource
def load_ensemble_models():
    class_names = load_class_names()
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"모델 파일이 없습니다: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    model_names = [model.names[index] for index in range(len(model.names))]
    if model_names != class_names:
        raise ValueError("best.pt의 클래스 번호/음식명이 data.yaml과 다릅니다.")
    return [{"model": model, "label": "best.pt", "weight": 1.0}], class_names, []


def calculate_iou(box1, box2):
    intersection_x1 = max(box1[0], box2[0])
    intersection_y1 = max(box1[1], box2[1])
    intersection_x2 = min(box1[2], box2[2])
    intersection_y2 = min(box1[3], box2[3])

    intersection = (
        max(0.0, intersection_x2 - intersection_x1)
        * max(0.0, intersection_y2 - intersection_y1)
    )
    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def fuse_cluster(cluster):
    weighted_scores = [
        detection["conf"] * detection["model_weight"]
        for detection in cluster
    ]
    total_score = sum(weighted_scores)
    fused_box = [
        sum(
            detection["box"][coordinate] * score
            for detection, score in zip(cluster, weighted_scores)
        ) / total_score
        for coordinate in range(4)
    ]
    total_model_weight = sum(detection["model_weight"] for detection in cluster)
    fused_confidence = total_score / total_model_weight

    return fused_box, fused_confidence


def weighted_box_fusion(detections, iou_threshold=0.55):
    sorted_detections = sorted(
        detections,
        key=lambda detection: detection["conf"] * detection["model_weight"],
        reverse=True,
    )
    clusters = []

    for detection in sorted_detections:
        best_cluster = None
        best_iou = 0.0

        for cluster in clusters:
            if cluster[0]["cls_id"] != detection["cls_id"]:
                continue

            fused_box, _ = fuse_cluster(cluster)
            current_iou = calculate_iou(detection["box"], fused_box)
            if current_iou >= iou_threshold and current_iou > best_iou:
                best_cluster = cluster
                best_iou = current_iou

        if best_cluster is None:
            clusters.append([detection])
        else:
            best_cluster.append(detection)

    fused_detections = []
    for cluster in clusters:
        fused_box, fused_confidence = fuse_cluster(cluster)
        fused_detections.append({
            "cls_id": cluster[0]["cls_id"],
            "box": fused_box,
            "conf": fused_confidence,
            "models": sorted({detection["model_label"] for detection in cluster}),
        })

    return sorted(
        fused_detections,
        key=lambda detection: detection["conf"],
        reverse=True,
    )


def run_5th_model(image, conf_val=0.08, iou_val=0.45, imgsz_val=960):
    models, class_names, _ = load_ensemble_models()

    raw_detections = []

    # 최신 모델을 실행하고 탐지 결과를 공통 형식으로 변환한다.
    for model_info in models:
        result = model_info["model"](
            image,
            conf=conf_val,
            iou=iou_val,
            imgsz=imgsz_val,
            verbose=False,
        )[0]

        for box in result.boxes:
            raw_detections.append({
                "cls_id": int(box.cls[0]),
                "conf": float(box.conf[0]),
                "box": box.xyxy[0].tolist(),
                "model_label": model_info["label"],
                "model_weight": model_info["weight"],
            })

    fused_results = weighted_box_fusion(raw_detections, iou_threshold=0.55)
    detected_items = []
    annotated_img = image.copy()
    draw = ImageDraw.Draw(annotated_img)
    image_width, image_height = image.size

    for detection in fused_results:
        cls_id = detection["cls_id"]
        name = class_names[cls_id]
        confidence = detection["conf"]
        xyxy = detection["box"]
        x1, y1, x2, y2 = map(int, xyxy)
        crop_box = (
            max(0, x1),
            max(0, y1),
            min(image_width, x2),
            min(image_height, y2),
        )
        crop_img = (
            image.crop(crop_box)
            if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]
            else None
        )
        model_source = " + ".join(detection["models"])

        detected_items.append({
            "name": name,
            "conf": confidence * 100,
            "box": xyxy,
            "source": model_source,
            "crop": crop_img,
        })
        draw.rectangle([x1, y1, x2, y2], outline="#28a745", width=3)
        draw.text(
            (x1 + 4, max(0, y1 - 16)),
            f"{name} ({confidence * 100:.0f}%)",
            fill="#28a745",
        )

    return detected_items, annotated_img


# [5] 가상 데이터 생성 및 세션 상태 초기화 함수
def generate_mock_meals(count=20):
    # 영양 데이터베이스(NUTRITION_DB)에 등록된 모든 음식명(키)들을 리스트로 추출
    sample_keys = list(NUTRITION_DB.keys())
    
    # 생성된 가상 식단 데이터들을 담을 빈 리스트 초기화
    mock_data = []
    
    # 가상 날짜 생성을 위한 기준 시점(현재 시간) 객체 생성
    base_date = datetime.now()
    
    # 요청받은 개수(count)만큼 반복하여 가상 식단 데이터 생성
    for _ in range(count):
        # 최근 6일 이내의 무작위 날짜 지정을 위한 일수(0~6일) 랜덤 선택 후 기준일에서 차감
        target_date = base_date - timedelta(days=random.randint(0, 6))
        
        # 아침, 점심, 저녁, 간식/야식 중 하나의 식사 구분을 무작위로 선택
        meal_type = random.choice(["아침", "점심", "저녁", "간식/야식"])
        
        # 식사 시간 지정을 위한 시(7시~21시)와 분(10분~55분)을 무작위로 추출
        hour = random.randint(7, 21)
        minute = random.randint(10, 55)
        
        # 날짜와 시간을 보기 편한 문자열 포맷("YYYY-MM-DD HH:MM")으로 조합
        time_str = f"{target_date.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}"
        
        # 등록된 음식들 중 무작위로 하나를 선택하여 음식명으로 지정
        food_name = random.choice(sample_keys)
        
        # 선택된 음식의 영양 성분 정보 딕셔너리 가져오기
        item = NUTRITION_DB[food_name]
        
        # 섭취 배율(0.5인분, 1인분, 1.5인분 등)을 무작위로 설정
        portion = random.choice([0.5, 1.0, 1.0, 1.5])
        
        # 가상 데이터 딕셔너리 구성 (섭취 배율을 곱해 영양 성분 비례 계산)
        mock_data.append({
            "데이터구분": "가상생성",
            "기록일시": time_str,
            "날짜": target_date.strftime('%Y-%m-%d'),
            "식사구분": meal_type,
            "음식명": food_name,
            "섭취수량": f"{portion} {item['unit']}",
            "칼로리(kcal)": round(item["cal"] * portion, 1),
            "탄수화물(g)": round(item["carbs"] * portion, 1),
            "단백질(g)": round(item["protein"] * portion, 1),
            "지방(g)": round(item["fat"] * portion, 1),
            "당류(g)": round(item["sugar"] * portion, 1),
            "나트륨(mg)": int(item["sodium"] * portion)
        })
        
    # 생성된 가상 식단 데이터를 기록일시 기준 최신순(내림차순)으로 정렬
    mock_data.sort(key=lambda x: x["기록일시"], reverse=True)
    
    return mock_data


# 앱 최초 실행 여부를 확인하여 세션 상태에 가상 식단 20건 자동 주입
if "initialized" not in st.session_state:
    st.session_state.meal_history = generate_mock_meals(20)  # 가상 식단 20건 생성 후 세션에 저장
    st.session_state.initialized = True                      # 초기화 완료 상태 플래그 설정
elif "meal_history" not in st.session_state:
    st.session_state.meal_history = []                       # 히스토리가 비어있을 경우 빈 리스트로 보정

# UI 알림 메시지 관리를 위한 세션 상태 변수 초기화
if "last_added_message" not in st.session_state:
    st.session_state.last_added_message = None

# [6] 사이드바 네비게이션 및 파라미터 조절 위젯 구성

# 사이드바 상단에 서비스 브랜드명 및 서브타이틀 HTML 마크다운 렌더링
st.sidebar.markdown(
    '<div class="sidebar-brand">🥗 NutriVision</div><div class="sidebar-sub">AI 맞춤형 식단 분석 서비스</div>', 
    unsafe_allow_html=True
)

# 사이드바 화면 전환 모드 선택 섹션 제목 출력
st.sidebar.markdown("### 화면")

# 사진 분석 화면과 종합 통계 대시보드 화면을 전환할 수 있는 라디오 버튼 위젯 생성
view_mode = st.sidebar.radio(
    "화면 모드", 
    ["📷 음식 사진 분석 및 추가", "📊 종합 통계 대시보드"]
)

# UI 시각적 구분을 위한 수평선(구분선) 추가
st.sidebar.write("---")

# [수정] 사이드바에 있던 AI 탐지 설정 슬라이더 위젯들을 모두 제거했습니다.
# 대신 아래 메인 화면 영역에서 고정된 파라미터 변수로 직접 선언합니다.

# 사이드바 내 테스트용 가상 데이터 관리 섹션 소제목 출력
st.sidebar.subheader("🎲 가상 데이터 관리")

# 일괄 생성할 가상 식단 데이터 개수 조절 슬라이더 (기본값: 10건)
mock_count = st.sidebar.slider(
    "추가할 가상 데이터 수", 
    5, 30, 10, 5
)

# 가상 식단 데이터 추가 생성 버튼 클릭 시 동작 로직
if st.sidebar.button("✨ 가상 식단 데이터 추가 생성"):
    st.session_state.meal_history.extend(generate_mock_meals(mock_count))
    st.session_state.meal_history.sort(key=lambda x: x["기록일시"], reverse=True)
    st.sidebar.success(f"{mock_count}건의 식단이 추가되었습니다!")
    st.rerun()

# 전체 식단 데이터 초기화(비우기) 버튼 클릭 시 동작 로직
if st.sidebar.button("🗑️ 전체 데이터 비우기"):
    st.session_state.meal_history = []
    st.session_state.last_added_message = None
    st.sidebar.warning("데이터가 모두 삭제되었습니다.")
    st.rerun()

# 대시보드 통계 기준이 되는 사용자 1일 목표 칼로리 입력 숫자 필드 위젯 (기본값: 2000 kcal)
daily_goal = st.sidebar.number_input(
    "🎯 1일 목표 칼로리 (kcal)", 
    1200, 3500, 2000, 100
)

# [7] 화면 1: 다중 사진 분석 및 음식 감지 인터페이스
if view_mode == "📷 음식 사진 분석 및 추가":
    
    # 화면 최상단 메인 타이틀 출력
    st.title("📷 AI 150종 음식 감지 & 식단 등록")
    
    # [추가] 사이드바가 사라진 대신, 확정된 AI 탐지 파라미터 기준을 사용자에게 안내하는 캡션 출력
    st.caption("🟢 150종 한식 탐지 | ⚙️ **탐지 기준 고정**: 신뢰도(Conf) 0.11 · 중복제거(IoU) 0.45 · 해상도(imgsz) 960")

    # [수정] 요청하신 AI 탐지 파라미터 고정값 정의
    conf_threshold = 0.11
    iou_threshold = 0.45
    imgsz_choice = 960

    # 최근 일괄 등록 성공 내역이 세션에 존재할 경우 상단에 성공 알림 메시지 노출
    if st.session_state.last_added_message:
        st.success(st.session_state.last_added_message)
        
        # 알림 닫기 버튼 클릭 시 메시지 상태를 초기화하고 화면 새로고침
        if st.button("알림 닫기"):
            st.session_state.last_added_message = None
            st.rerun()

    # 이미지 입력 방식을 선택하는 라디오 버튼 위젯 생성
    input_source = st.radio(
        "이미지 입력 방식:", 
        ["📂 시연용 샘플 이미지 선택", "💻 내 컴퓨터에서 업로드"], 
        horizontal=True
    )
    
    images_to_process = []
    sample_dir = str(APP_DIR / "samples")
    
    # [방식 1] 시연용 샘플 이미지 폴더에서 파일을 선택하여 처리하는 경우
    if input_source == "📂 시연용 샘플 이미지 선택":
        if not os.path.exists(sample_dir):
            os.makedirs(sample_dir)
            
        sample_files = [f for f in os.listdir(sample_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if sample_files:
            selected_samples = st.multiselect("샘플 사진을 선택하세요:", options=sample_files, default=[sample_files[0]])
            for file_name in selected_samples:
                img_path = os.path.join(sample_dir, file_name)
                images_to_process.append((file_name, Image.open(img_path).convert("RGB")))
        else:
            st.info("💡 `samples/` 폴더에 사진들을 넣어두면 간편하게 선택할 수 있습니다.")
            
    # [방식 2] 사용자의 로컬 컴퓨터에서 이미지 파일을 직접 업로드하는 경우
    else:
        uploaded_files = st.file_uploader(
            "음식 사진을 선택하세요 (여러 장 가능)", 
            type=["jpg", "png", "jpeg"], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            for up_file in uploaded_files:
                images_to_process.append((up_file.name, Image.open(up_file).convert("RGB")))

    # 처리할 이미지가 하나 이상 존재할 경우 분석 및 UI 렌더링 진행
    if images_to_process:
        st.write("---")
        
        global_meal_slot = st.selectbox(
            "🕒 식사 구분 (일괄 적용)", 
            ["아침", "점심", "저녁", "간식/야식"], 
            index=1
        )
        
        staged_records = []  # 최종 등록 대기 중인 식단 영양 기록들을 담을 임시 리스트
        
        for img_idx, (img_title, img_obj) in enumerate(images_to_process):
            st.markdown(f"### 🖼️ [사진 {img_idx+1}] {img_title}")
            
            # 고정된 파라미터 값들이 반영된 고유 세션 키 생성
            session_key_orig = f"orig_items_{img_idx}_{img_title}_{conf_threshold}_{iou_threshold}_{imgsz_choice}"
            session_key_active = f"active_items_{img_idx}_{img_title}_{conf_threshold}_{iou_threshold}_{imgsz_choice}"
            annotated_key = f"annotated_img_{img_idx}_{img_title}_{conf_threshold}_{iou_threshold}_{imgsz_choice}"
            
            # 세션에 캐시된 데이터가 없을 경우에만 확정된 고정값으로 YOLO 모델 추론 수행
            if session_key_orig not in st.session_state:
                detected_items, annotated_img = run_5th_model(
                    img_obj,
                    conf_val=conf_threshold,
                    iou_val=iou_threshold,
                    imgsz_val=imgsz_choice
                )
                st.session_state[session_key_orig] = [dict(item) for item in detected_items]
                st.session_state[session_key_active] = [dict(item) for item in detected_items]
                st.session_state[annotated_key] = annotated_img
            
            orig_items = st.session_state[session_key_orig]
            active_items = st.session_state[session_key_active]
            annotated_img = st.session_state[annotated_key]

            # 컬럼 비율을 [1, 1]로 균형 있게 잡고 gap 설정
            col_img, col_summary = st.columns([1, 1], gap="small")
            
            with col_img:
                # AI 탐색 결과 이미지 출력 크기 고정 (width=350)
                st.image(annotated_img, caption="🎯 AI 음식 객체 탐색 결과", width=350)
                
            with col_summary:
                # 1차 탐색 요약 영역
                st.markdown("#### 🔍 1차 탐색 요약")
                
                if not orig_items:
                    st.warning("⚠️ 사진에서 인식된 음식이 없습니다. (사진에 관계없이 직접추가도 가능합니다)")
                else:
                    st.success(f"총 **{len(orig_items)}개**의 음식을 발견했습니다! 탐지 된 음식 중 맞지 않는 음식은 삭제버튼으로 삭제 가능합니다.")
                    
                    tags = [f"**{it['name']}** ({it['conf']:.0f}%)" for it in orig_items]
                    st.markdown("발견된 음식: " + " · ".join(tags))
                    
                    thumb_cols = st.columns(min(len(orig_items), 4))
                    for t_idx, it in enumerate(orig_items[:4]):
                        with thumb_cols[t_idx]:
                            if it["crop"]:
                                st.image(it["crop"], caption=it["name"], width=150)

            # 각 음식별 상세 메뉴 및 섭취량 조절 패널 (활성 리스트 기준 상호작용)
            with st.expander("✏️ 각 음식별 상세 메뉴 및 섭취량 조절", expanded=True):
                all_foods = list(NUTRITION_DB.keys())
                
                if not active_items:
                    food_key = st.selectbox(
                        "메뉴 수동 선택",
                        options=all_foods,
                        format_func=lambda k: f"{k} ({NUTRITION_DB[k]['category']})",
                        key=f"manual_{img_idx}_{img_title}"
                    )
                    item = NUTRITION_DB[food_key]
                    portion = st.number_input(
                        f"섭취 수량 ({item['unit']})", 
                        min_value=0.5, max_value=5.0, value=1.0, step=0.5, 
                        key=f"p_man_{img_idx}_{img_title}"
                    )
                    
                    staged_records.append({
                        "데이터구분": "직접입력", "식사구분": global_meal_slot, "음식명": food_key,
                        "섭취수량": f"{portion} {item['unit']}",
                        "칼로리(kcal)": round(item["cal"] * portion, 1),
                        "탄수화물(g)": round(item["carbs"] * portion, 1),
                        "단백질(g)": round(item["protein"] * portion, 1),
                        "지방(g)": round(item["fat"] * portion, 1),
                        "당류(g)": round(item["sugar"] * portion, 1),
                        "나트륨(mg)": int(item["sodium"] * portion)
                    })
                else:
                    for it_idx, it in enumerate(list(active_items)):
                        c_detail, c_del = st.columns([4, 1])
                        
                        with c_detail:
                            c_crop, c_select = st.columns([1, 2.5])
                            
                            with c_crop:
                                if it["crop"]:
                                    st.image(it["crop"], caption=f"#{it_idx+1} {it['name']}", width=150)
                                    
                            with c_select:
                                def_idx = all_foods.index(it["name"]) if it["name"] in all_foods else 0
                                
                                sel_food = st.selectbox(
                                    f"#{it_idx+1} 메뉴 확인/수정",
                                    options=all_foods,
                                    index=def_idx,
                                    format_func=lambda k: f"{k} ({NUTRITION_DB[k]['category']})",
                                    key=f"menu_{img_idx}_{img_title}_{it_idx}"
                                )
                                
                                item = NUTRITION_DB[sel_food]
                                
                                portion = st.number_input(
                                    f"수량 ({item['unit']})",
                                    min_value=0.5, max_value=5.0, value=1.0, step=0.5,
                                    key=f"portion_{img_idx}_{img_title}_{it_idx}"
                                )
                                
                                c_cal = round(item["cal"] * portion, 1)
                                
                                st.markdown(
                                    f"<div style='font-size: 15px; font-weight: 600; color: #16324F; margin-top: 5px;'>"
                                    f"🔥 {c_cal:,.1f} kcal | 탄 {round(item['carbs']*portion, 1)}g | "
                                    f"단 {round(item['protein']*portion, 1)}g | 지 {round(item['fat']*portion, 1)}g | "
                                    f"나트륨 {int(item['sodium']*portion)}mg"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                                
                                staged_records.append({
                                    "데이터구분": "직접입력", "식사구분": global_meal_slot, "음식명": sel_food,
                                    "섭취수량": f"{portion} {item['unit']}",
                                    "칼로리(kcal)": c_cal,
                                    "탄수화물(g)": round(item["carbs"] * portion, 1),
                                    "단백질(g)": round(item["protein"] * portion, 1),
                                    "지방(g)": round(item["fat"] * portion, 1),
                                    "당류(g)": round(item["sugar"] * portion, 1),
                                    "나트륨(mg)": int(item["sodium"] * portion)
                                })
                                
                        with c_del:
                            st.write("") 
                            st.write("")
                            st.write("")
                            
                            if st.button("🗑️ 삭제", key=f"del_{img_idx}_{img_title}_{it_idx}"):
                                active_items.pop(it_idx)
                                st.rerun()
                                
                        st.write("---")

        if staged_records:
            total_cal = sum(r["칼로리(kcal)"] for r in staged_records)
            btn_label = f"🚀 감지된 총 {len(staged_records)}개 음식 일괄 등록하기 (총 {total_cal:,.1f} kcal)"
            
            if st.button(btn_label, type="primary", use_container_width=True):
                now = datetime.now()
                now_str = now.strftime("%Y-%m-%d %H:%M")
                date_str = now.strftime("%Y-%m-%d")
                
                names = []
                for r in staged_records:
                    r["기록일시"] = now_str
                    r["날짜"] = date_str
                    st.session_state.meal_history.insert(0, r)
                    names.append(r["음식명"])
                    
                st.session_state.last_added_message = (
                    f"✅ **[일괄 등록 성공]** 총 {len(staged_records)}개 품목({', '.join(names)})이 "
                    f"오늘의 **[{global_meal_slot}]** 식단으로 정상 저장되었습니다!"
                )
                st.rerun()

# [8] ECharts 공통 테마 및 렌더링 헬퍼 함수 설정
ECHARTS_TEXT = "#40515F"
ECHARTS_MUTED = "#82909A"
ECHARTS_NAVY = "#16324F"
ECHARTS_TEAL = "#238A8D"
ECHARTS_BORDER = "#E3E9ED"

def render_echart(options, height="330px", key=None):
    return st_echarts(
        options=options,
        height=height,
        key=key
    )

# [9] 화면 2: 고급 건강검진형 종합 통계 대시보드
if view_mode == "📊 종합 통계 대시보드":

    st.markdown(
        '<div class="page-kicker">NUTRIVISION · HEALTH ANALYTICS</div>',
        unsafe_allow_html=True
    )

    st.title("AI 맞춤형 식단 다이어리 & 대시보드")

    st.markdown(
        '<div class="page-description">'
        '식단 기록을 기반으로 일일 에너지 섭취량과 '
        '탄수화물·단백질·지방 균형을 한눈에 확인합니다.'
        '</div>',
        unsafe_allow_html=True
    )

    if not st.session_state.meal_history:
        st.info(
            "데이터가 비어 있습니다. 사진을 등록하거나 "
            "사이드바에서 가상 데이터를 생성하세요."
        )
    else:
        df = pd.DataFrame(st.session_state.meal_history)

        # [계산 공식 1] 전체 누적 영양 성분 합산 산출
        tot_cal = round(df["칼로리(kcal)"].sum(), 1)
        tot_carbs = round(df["탄수화물(g)"].sum(), 1)
        tot_protein = round(df["단백질(g)"].sum(), 1)
        tot_fat = round(df["지방(g)"].sum(), 1)
        tot_sugar = round(df["당류(g)"].sum(), 1)
        tot_sodium = round(df["나트륨(mg)"].sum(), 1)

        # [계산 공식 2] 오늘 날짜 기준으로 데이터 필터링 및 금일 섭취량 계산
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_df = df[df["날짜"].astype(str) == today_str].copy()

        today_cal = round(today_df["칼로리(kcal)"].sum(), 1) if not today_df.empty else 0
        today_carbs = round(today_df["탄수화물(g)"].sum(), 1) if not today_df.empty else 0
        today_protein = round(today_df["단백질(g)"].sum(), 1) if not today_df.empty else 0
        today_fat = round(today_df["지방(g)"].sum(), 1) if not today_df.empty else 0

        # [계산 공식 3] 금일 목표 칼로리 대비 달성률(%) 연산
        goal_percent = today_cal / daily_goal * 100 if daily_goal > 0 else 0

        # ----------------------------------------------------------------------
        # 오늘의 영양 상태 KPI 카드 렌더링
        # ----------------------------------------------------------------------
        st.markdown(
            '<div class="section-title">오늘의 영양 상태</div>',
            unsafe_allow_html=True
        )

        k1, k2, k3, k4 = st.columns(4)

        cards = [
            ("오늘 섭취 칼로리", f"{today_cal:,.0f}", "kcal", f"목표 {daily_goal:,.0f} kcal · {goal_percent:.0f}%"),
            ("탄수화물", f"{today_carbs:,.1f}", "g", "오늘 기록 기준"),
            ("단백질", f"{today_protein:,.1f}", "g", "오늘 기록 기준"),
            ("지방", f"{today_fat:,.1f}", "g", "오늘 기록 기준"),
        ]

        for col, (label, value, unit, note) in zip([k1, k2, k3, k4], cards):
            with col:
                st.markdown(
                    f"""
                    <div class="health-card">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value">{value}
                            <span class="metric-unit">{unit}</span>
                        </div>
                        <div class="metric-note">{note}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # AI 식단 분석 요약 문구 동적 결정
        if today_cal == 0:
            report_text = "오늘 등록된 식단이 없습니다. 음식 사진을 분석하여 오늘의 식단을 먼저 기록해 주세요."
            report_class = "status-warning"
        elif today_cal <= daily_goal:
            report_text = f"오늘 섭취량은 목표 칼로리의 {goal_percent:.0f}% 수준입니다. 현재 기록 기준으로 목표 범위 안에 있습니다."
            report_class = "status-good"
        else:
            report_text = f"오늘 섭취량이 목표보다 {today_cal - daily_goal:,.0f} kcal 높습니다. 다음 식사에서는 섭취량을 조절해 보세요."
            report_class = "status-warning"

        st.markdown(
            f"""
            <div class="report-box">
                <div class="report-title">AI 식단 분석 요약</div>
                <div class="report-text">
                    <span class="{report_class}">{report_text}</span>
                    <br>
                    아래 차트에서 최근 일자별 섭취 추이와 영양소 구성을 자세히 확인할 수 있습니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ----------------------------------------------------------------------
        # [차트 1] 최근 일자별 칼로리 섭취 추이 라인 차트 설정
        # ----------------------------------------------------------------------
        daily_df = (
            df.groupby("날짜")["칼로리(kcal)"]
            .sum()
            .reset_index()
            .sort_values("날짜")
        )

        st.markdown(
            '<div class="section-title">최근 일자별 칼로리 섭취 추이</div>',
            unsafe_allow_html=True
        )

        line_options = {
            "animation": True,
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": "#FFFFFF",
                "borderColor": ECHARTS_BORDER,
                "textStyle": {"color": ECHARTS_TEXT}
            },
            "grid": {"left": "4%", "right": "4%", "top": "14%", "bottom": "12%", "containLabel": True},
            "xAxis": {
                "type": "category",
                "data": daily_df["날짜"].tolist(),
                "boundaryGap": False,
                "axisLine": {"lineStyle": {"color": ECHARTS_BORDER}},
                "axisLabel": {"color": ECHARTS_MUTED, "fontSize": 11}
            },
            "yAxis": {
                "type": "value",
                "name": "kcal",
                "nameTextStyle": {"color": ECHARTS_MUTED},
                "splitLine": {"lineStyle": {"color": "#EEF2F4"}},
                "axisLabel": {"color": ECHARTS_MUTED}
            },
            "series": [{
                "name": "섭취 칼로리",
                "type": "line",
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 7,
                "data": [round(v, 1) for v in daily_df["칼로리(kcal)"].tolist()],
                "lineStyle": {"width": 3, "color": ECHARTS_TEAL},
                "itemStyle": {"color": ECHARTS_TEAL},
                "areaStyle": {"opacity": 0.08},
                # 사이드바에서 입력한 목표 칼로리를 점선 기준선(MarkLine)으로 시각화
                "markLine": {
                    "silent": True,
                    "symbol": "none",
                    "data": [{
                        "yAxis": daily_goal,
                        "label": {"formatter": f"목표 {daily_goal:,} kcal", "color": ECHARTS_NAVY},
                        "lineStyle": {"type": "dashed", "color": "#9AA8B2"}
                    }]
                }
            }]
        }

        render_echart(line_options, height="360px", key="daily_calorie_line")

        # ----------------------------------------------------------------------
        # [차트 2 & 3] 식사 세션별 바 차트 및 탄단지 도넛 차트 설정
        # ----------------------------------------------------------------------
        col_c1, col_c2 = st.columns(2, gap="large")

        with col_c1:
            st.markdown(
                '<div class="section-title">식사 구분별 섭취 칼로리</div>',
                unsafe_allow_html=True
            )

            meal_order = ["아침", "점심", "저녁", "간식/야식"]
            meal_grp = (
                df.groupby("식사구분")["칼로리(kcal)"]
                .sum()
                .reindex(meal_order)
                .fillna(0)
                .reset_index()
            )

            bar_options = {
                "animation": True,
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                "grid": {"left": "5%", "right": "5%", "top": "10%", "bottom": "12%", "containLabel": True},
                "xAxis": {
                    "type": "category",
                    "data": meal_grp["식사구분"].tolist(),
                    "axisLine": {"lineStyle": {"color": ECHARTS_BORDER}},
                    "axisLabel": {"color": ECHARTS_MUTED}
                },
                "yAxis": {
                    "type": "value",
                    "name": "kcal",
                    "splitLine": {"lineStyle": {"color": "#EEF2F4"}},
                    "axisLabel": {"color": ECHARTS_MUTED}
                },
                "series": [{
                    "name": "칼로리",
                    "type": "bar",
                    "barWidth": "42%",
                    "data": [round(v, 1) for v in meal_grp["칼로리(kcal)"].tolist()],
                    "itemStyle": {"color": ECHARTS_NAVY, "borderRadius": [5, 5, 0, 0]}
                }]
            }

            render_echart(bar_options, height="320px", key="meal_calorie_bar")

        with col_c2:
            st.markdown(
                '<div class="section-title">탄수화물 · 단백질 · 지방 구성</div>',
                unsafe_allow_html=True
            )

            # [계산 공식 4] Atwater 환산 계수 적용: 탄수화물(4kcal/g), 단백질(4kcal/g), 지방(9kcal/g)
            macro_cal = [
                {"name": "탄수화물", "value": round(tot_carbs * 4, 1)},
                {"name": "단백질", "value": round(tot_protein * 4, 1)},
                {"name": "지방", "value": round(tot_fat * 9, 1)}
            ]

            macro_total = sum(x["value"] for x in macro_cal)

            donut_options = {
                "animation": True,
                "tooltip": {"trigger": "item", "formatter": "{b}<br/>{c} kcal ({d}%)"},
                "legend": {
                    "bottom": 0,
                    "icon": "circle",
                    "textStyle": {"color": ECHARTS_TEXT}
                },
                "series": [{
                    "name": "탄단지",
                    "type": "pie",
                    "radius": ["52%", "74%"],
                    "center": ["50%", "45%"],
                    "avoidLabelOverlap": True,
                    "itemStyle": {
                        "borderRadius": 5,
                        "borderColor": "#FFFFFF",
                        "borderWidth": 3
                    },
                    "label": {"show": False},
                    "data": macro_cal
                }],
                # 도넛 차트 가운데에 총 칼로리 수치 텍스트 그래픽 삽입
                "graphic": [{
                    "type": "text",
                    "left": "center",
                    "top": "38%",
                    "style": {
                        "text": f"{macro_total:,.0f}\nkcal",
                        "textAlign": "center",
                        "fill": ECHARTS_NAVY,
                        "fontSize": 20,
                        "fontWeight": 700
                    }
                }]
            }

            render_echart(donut_options, height="320px", key="macro_donut")

        # ----------------------------------------------------------------------
        # [지표 카드] 매크로 밸런스 레이더, 목표 게이지, 당류·나트륨 바 차트
        # ----------------------------------------------------------------------
        st.markdown(
            '<div class="section-title">주요 영양 지표</div>',
            unsafe_allow_html=True
        )

        n1, n2, n3 = st.columns(3, gap="large")

        with n1:
            # [계산 공식 5] 전체 칼로리 대비 각 영양소의 열량 비중(%) 산출
            carb_ratio = tot_carbs * 4 / tot_cal * 100 if tot_cal > 0 else 0
            protein_ratio = tot_protein * 4 / tot_cal * 100 if tot_cal > 0 else 0
            fat_ratio = tot_fat * 9 / tot_cal * 100 if tot_cal > 0 else 0

            radar_options = {
                "tooltip": {},
                "radar": {
                    "radius": "62%",
                    "indicator": [
                        {"name": "탄수화물", "max": 60},
                        {"name": "단백질", "max": 40},
                        {"name": "지방", "max": 40}
                    ],
                    "axisName": {"color": ECHARTS_TEXT},
                    "splitLine": {
                        "lineStyle": {
                            "color": ["#E9EEF1", "#E3E9ED", "#DCE4E8", "#D5DEE3"]
                        }
                    }
                },
                "series": [{
                    "type": "radar",
                    "data": [{
                        "value": [
                            round(carb_ratio, 1),
                            round(protein_ratio, 1),
                            round(fat_ratio, 1)
                        ],
                        "name": "현재 구성",
                        "areaStyle": {"opacity": 0.18},
                        "lineStyle": {"width": 2}
                    }]
                }]
            }

            st.markdown('<div class="health-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">MACRO BALANCE</div>', unsafe_allow_html=True)
            render_echart(radar_options, height="280px", key="macro_radar")
            st.markdown('</div>', unsafe_allow_html=True)

        with n2:
            gauge_options = {
                "series": [{
                    "type": "gauge",
                    "startAngle": 210,
                    "endAngle": -30,
                    "min": 0,
                    "max": max(daily_goal, 1),
                    "progress": {"show": True, "width": 13},
                    "axisLine": {
                        "lineStyle": {
                            "width": 13,
                            "color": [[1, "#E7EEF1"]]
                        }
                    },
                    "pointer": {"show": True, "length": "58%", "width": 5},
                    "axisTick": {"show": False},
                    "splitLine": {"show": False},
                    "axisLabel": {"show": False},
                    "anchor": {"show": True, "size": 8},
                    "title": {
                        "show": True,
                        "offsetCenter": [0, "62%"],
                        "color": ECHARTS_MUTED,
                        "fontSize": 12
                    },
                    "detail": {
                        "valueAnimation": True,
                        "offsetCenter": [0, "18%"],
                        "fontSize": 25,
                        "fontWeight": 800,
                        "color": ECHARTS_NAVY,
                        "formatter": "{value} kcal"
                    },
                    "data": [{
                        "value": round(min(today_cal, daily_goal), 1),
                        "name": "오늘 목표 대비"
                    }]
                }]
            }

            st.markdown('<div class="health-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">DAILY CALORIE GOAL</div>', unsafe_allow_html=True)
            render_echart(gauge_options, height="280px", key="daily_goal_gauge")
            st.markdown(
                f'<div class="small-muted">목표 {daily_goal:,} kcal · 현재 {today_cal:,.0f} kcal</div>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with n3:
            # [안전 장치] BidiComponent 에러 방지를 위해 당류 및 나트륨 값이 없을 경우 0.0으로 기본값 보정
            safe_sugar = float(tot_sugar) if 'tot_sugar' in locals() and tot_sugar is not None else 0.0
            safe_sodium = float(tot_sodium) if 'tot_sodium' in locals() and tot_sodium is not None else 0.0

            nutrient_options = {
                "tooltip": {
                    "trigger": "axis",
                    "axisPointer": {"type": "shadow"}
                },
                "grid": {
                    "left": "4%",
                    "right": "4%",
                    "top": "8%",
                    "bottom": "8%",
                    "containLabel": True
                },
                "xAxis": {
                    "type": "category",
                    "data": ["당류", "나트륨"],
                    "axisLine": {"lineStyle": {"color": ECHARTS_BORDER}},
                    "axisLabel": {"color": ECHARTS_MUTED}
                },
                "yAxis": {
                    "type": "value",
                    "splitLine": {"lineStyle": {"color": "#EEF2F4"}},
                    "axisLabel": {"color": ECHARTS_MUTED}
                },
                "series": [{
                    "type": "bar",
                    "barWidth": "35%",
                    "data": [
                        {"value": safe_sugar, "itemStyle": {"color": "#6C7A89"}},
                        {"value": safe_sodium, "itemStyle": {"color": ECHARTS_NAVY}}
                    ],
                    "itemStyle": {"borderRadius": [5, 5, 0, 0]}
                }]
            }

            st.markdown('<div class="health-card">', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">SUGAR · SODIUM</div>', unsafe_allow_html=True)
            render_echart(nutrient_options, height="280px", key="sugar_sodium_bar")
            st.markdown(
                f'<div class="small-muted">당류 {safe_sugar:,.1f} g · 나트륨 {safe_sodium:,.0f} mg</div>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # [히스토리 테이블 및 CSV 다운로드 기능]
        # ----------------------------------------------------------------------
        st.markdown(
            '<div class="section-title">전체 식사 히스토리</div>',
            unsafe_allow_html=True
        )

        st.caption(
            "🟢 직접 등록한 실제 데이터와 가상 생성 데이터를 구분하여 관리할 수 있습니다."
        )

        # 사용자가 사진을 통해 직접 입력한 행에만 배경색을 입혀 시각적으로 강조하는 스타일 함수
        def highlight_real_data(row):
            if row["데이터구분"] == "직접입력":
                return [
                    "background-color: #EEF7F6; color: #1E6F70; font-weight: 600;"
                ] * len(row)
            return [""] * len(row)

        styled_df = df.style.apply(highlight_real_data, axis=1)

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )

        # 전체 식단 데이터를 CSV 파일로 인코딩하여 다운로드 버튼 제공
        csv_file = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="📥 전체 식단 CSV 다운로드",
            data=csv_file,
            file_name=f"diet_history_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
