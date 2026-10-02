# AI 식단 다이어리 실행 안내

최초 설치는 `01_SETUP_AND_RUN.bat`, 이후 실행은 `02_RUN_ONLY.bat`을 더블 클릭하세요.
현재 PC에 설치된 Python과 프로젝트 내 차트 패키지를 사용합니다.
가상환경이 있으면 해당 환경을 우선 사용하며, 준비된 환경이 없으면 설치 스크립트를 실행합니다.

## 모델 및 데이터

- `best.pt`: 프로젝트 폴더에 있는 최신 모델 (150 클래스)
- `data.yaml`: 클래스 번호 0~149와 한글 음식명
- `CaloDetect_nutrition_all_matched.csv`: YAML 순서대로 정렬된 150행
- `data_config.py`: 경로와 컬럼 정의, 데이터 검증
- `validate_data.py`: 실제 모델/YAML/CSV 매칭 확인

앱은 프로젝트 폴더의 `best.pt`를 사용합니다. 모델을 교체한 뒤에는 실행 중인 앱을 종료하고 다시 실행하세요.
앱, YAML, CSV, 샘플 경로는 실행하는 폴더에 영향을 받지 않습니다.

## 영양 CSV 컬럼

| 컬럼 | 의미 / 단위 |
| --- | --- |
| class_id | data.yaml의 클래스 번호 (0~149) |
| food_name | 모델의 한글 음식명과 정확히 일치 |
| category | 음식 분류 |
| unit | 영양값의 기준 섭취량 (원본 값 유지) |
| cal | kcal |
| carbs | 탄수화물 g |
| protein | 단백질 g |
| fat | 지방 g |
| sugar | 당류 g |
| sodium | 나트륨 mg |

영양 수치는 원본 그대로 유지했습니다. 각 수치는 `unit`에 적힌 기준량의 값입니다.
음식명 누락/중복, 잘못된 클래스 번호, 빈 분류/기준량, 음수 또는 잘못된 영양 수치는 실행 시 오류로 알려줍니다.

## 다른 PC에서 최초 설치

Python 3.10 이상이 설치된 상태에서 `01_SETUP_AND_RUN.bat`을 실행하세요.
패키지 설치 후 모델과 컬럼을 검증하고 Streamlit을 실행합니다.
이후에는 `02_RUN_ONLY.bat`을 실행하세요.

직접 실행하는 경우 이 폴더에서:

```powershell
python -m pip install -r requirements.txt
python validate_data.py
python -m streamlit run app.py
```

접속 주소: http://localhost:8501

샘플 사진은 `samples/` 폴더에 넣거나 화면에서 업로드할 수 있습니다.
