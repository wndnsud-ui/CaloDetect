"""Import an official MFDS food export, retaining its code, basis, and source.

Default is validation only; --apply writes via the designated migration owner.
No generated nutrition and no changes to model class IDs or existing source files.
"""
import argparse
import csv
import math
import re
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.db import get_engine
from backend.app.models import NutritionFood

SOURCE = 'https://various.foodsafetykorea.go.kr/nutrient/general/down/historyList.do'
NUTRIENTS = {'cal': '에너지(kcal)', 'carbs': '탄수화물(g)', 'protein': '단백질(g)',
             'fat': '지방(g)', 'sugar': '당류(g)', 'sodium': '나트륨(mg)'}


def numeric(value):
    text = str(value if value is not None else '').strip().replace(',', '')
    if text in ('', '-', 'N/A', 'NA'):
        return None
    result = float(text)
    if not math.isfinite(result) or result < 0:
        raise ValueError('Invalid numeric nutrition value')
    return result


def normalize(row):
    row = {str(k).strip().replace(' ', ''): v for k, v in row.items()}
    code = str(row.get('식품코드', '')).strip()
    name = str(row.get('식품명', '')).strip()
    basis = str(row.get('영양성분함량기준량', row.get('영양성분제공단위량', ''))).strip()
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(g|ml)', basis, re.IGNORECASE)
    if not code or len(code) > 75 or not name or len(name) > 120 or not match or float(match[1]) <= 0:
        raise ValueError('Food code/name and an explicit gram nutrition basis are required')
    grams = float(match[1])
    # Keep g and ml distinct. Use only an explicit source-provided portion of the same unit.
    unit = match[2].lower()
    serving = row.get('1인(회)분량참고량') or row.get('1회섭취참고량') or row.get('식품중량')
    serving_match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(g|ml)', str(serving).strip(), re.IGNORECASE) if serving else None
    serving_grams = float(serving_match[1]) if serving_match and serving_match[2].lower() == unit else grams
    nutrition = {key: numeric(row.get(column)) for key, column in NUTRIENTS.items()}
    nutrition = {key: round(value * serving_grams / grams, 4) if value is not None else None
                 for key, value in nutrition.items()}
    return {'id': f'mfds:{code}', 'name': name, 'serving_amount': serving_grams, 'serving_unit': unit,
            'nutrition': nutrition, 'source': SOURCE}


def read_rows(path):
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as stream:
            yield from csv.DictReader(stream)
    elif path.suffix.lower() == '.xlsx':
        from openpyxl import load_workbook
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            rows = iter(workbook.active.values)
            headers = next(rows)
            for row in rows:
                yield dict(zip(headers, row))
        finally:
            workbook.close()
    else:
        raise ValueError('Use an official UTF-8 CSV or XLSX export')


def apply_rows(db, rows):
    """Atomic batched upsert avoids one SELECT/INSERT round trip per source row."""
    if db.bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif db.bind.dialect.name == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise ValueError('Unsupported catalog database')
    rows = list(rows)
    for start in range(0, len(rows), 500):
        statement = insert(NutritionFood).values(rows[start:start + 500])
        db.execute(statement.on_conflict_do_update(index_elements=['id'], set_={
            key: getattr(statement.excluded, key) for key in
            ('name', 'serving_amount', 'serving_unit', 'nutrition', 'source')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    valid, rejected = {}, 0
    for row in read_rows(args.file):
        try:
            item = normalize(row)
            if item['id'] in valid:
                raise ValueError('Duplicate source code')
            valid[item['id']] = item
        except (ValueError, TypeError):
            rejected += 1
    target = sum('순대국' in item['name'] or '순댓국' in item['name'] for item in valid.values())
    print(f'Validated: {len(valid)}; rejected: {rejected}; sundae-guk matches: {target}')
    if not valid or rejected:
        raise SystemExit('Resolve unsupported/missing/duplicate rows before applying. No DB writes made.')
    if not args.apply:
        print('Validation only. No DB connection or writes. Designated owner may use --apply after review.')
        return
    with Session(get_engine()) as db:
        apply_rows(db, valid.values())
        db.commit()
    print('Imported official catalog. Original model foods unchanged.')


if __name__ == '__main__':
    main()
