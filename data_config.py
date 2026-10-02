"""모델 클래스와 영양 CSV의 공통 검증 및 컬럼 정리."""
from pathlib import Path

import pandas as pd
import yaml

APP_DIR = Path(__file__).resolve().parent
MODEL_PATH = APP_DIR / "best.pt"
DATA_PATH = APP_DIR / "data.yaml"
NUTRITION_PATH = APP_DIR / "CaloDetect_nutrition_all_matched.csv"
NUMERIC_COLUMNS = ["cal", "carbs", "protein", "fat", "sugar", "sodium"]
COLUMNS = ["class_id", "food_name", "category", "unit", *NUMERIC_COLUMNS]


def load_class_names():
    config = yaml.safe_load(DATA_PATH.read_text(encoding="utf-8-sig"))
    names = config["names"]
    if isinstance(names, dict):
        if set(names) != set(range(config["nc"])):
            raise ValueError("data.yaml 클래스 번호는 0부터 nc-1까지 연속이어야 합니다.")
        names = [names[i] for i in range(config["nc"])]
    names = [str(name).strip() for name in names]
    if len(names) != config["nc"] or len(set(names)) != len(names) or not all(names):
        raise ValueError("data.yaml의 nc, 음식명 개수 또는 중복을 확인하세요.")
    return names


def load_nutrition_frame(csv_path=NUTRITION_PATH):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    missing = set(COLUMNS[1:]) - set(df.columns)
    if missing:
        raise ValueError(f"영양 CSV 필수 컬럼 누락: {sorted(missing)}")
    for column in ["food_name", "category", "unit"]:
        df[column] = df[column].astype("string").str.strip()
        if df[column].isna().any() or df[column].eq("").any():
            raise ValueError(f"영양 CSV의 {column}에 빈 값이 있습니다.")
    if df["food_name"].duplicated().any():
        raise ValueError("영양 CSV에 중복된 음식명이 있습니다.")
    names = load_class_names()
    missing_foods = set(names) - set(df["food_name"])
    extra_foods = set(df["food_name"]) - set(names)
    if missing_foods or extra_foods:
        raise ValueError(f"클래스/영양정보 불일치: 누락={sorted(missing_foods)}, 추가={sorted(extra_foods)}")
    expected_ids = df["food_name"].map({name: i for i, name in enumerate(names)})
    if "class_id" in df and not pd.to_numeric(df["class_id"], errors="coerce").eq(expected_ids).all():
        raise ValueError("영양 CSV의 class_id가 data.yaml의 음식명과 다릅니다.")
    df["class_id"] = expected_ids
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        if df[column].isna().any() or (~df[column].between(0, float("inf"), inclusive="left")).any():
            raise ValueError(f"영양 CSV의 {column}은 유한한 0 이상의 숫자여야 합니다.")
    return df[COLUMNS].sort_values("class_id").reset_index(drop=True)
