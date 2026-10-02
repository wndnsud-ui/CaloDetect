"""실행 전 데이터 및 실제 모델의 클래스 매칭을 확인합니다."""
from data_config import MODEL_PATH, load_class_names, load_nutrition_frame


def main():
    from ultralytics import YOLO

    names = load_class_names()
    df = load_nutrition_frame()
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"모델 파일이 없습니다: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    model_names = [model.names[i] for i in range(len(model.names))]
    if model_names != names:
        raise ValueError("best.pt의 클래스 번호/음식명이 data.yaml과 다릅니다.")
    print(f"검증 완료: 모델 {len(names)} 클래스 / 영양정보 {len(df)}행 / 컬럼 {list(df.columns)}")


if __name__ == "__main__":
    main()
