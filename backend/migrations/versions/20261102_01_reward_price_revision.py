"""Reward mall price revision (업무지시서 리워드몰 가격·문구 개편 §2): 홍삼 3종·코치 7회권 가격 인하.

시드(ensure_products)는 기존 행 가격을 덮어쓰지 않으므로 여기서 1회 바꾼다. 운영자가 이미 바꾼 가격은 건드리지 않도록
이전 시드 가격과 같은 행만 고친다. 교환·이용권·차감 내역은 신청 당시 포인트(points·amount)를 따로 저장하므로 바뀌지 않는다.
3회 체험권 상품은 코치 시드와 함께 ensure_products가 추가한다.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261102_01'
down_revision = '20261101_01'
branch_labels = None
depends_on = None

# (상품 ID, 이전 가격, 새 가격)
PRICES = (('ginseng_daily10', 180, 100), ('bristick15', 290, 140), ('ginseng_premium30', 750, 200),
          ('coach_kim', 700, 200), ('coach_park', 700, 200), ('coach_lee', 700, 200), ('coach_choi', 700, 200))
UPDATE = sa.text('UPDATE reward_products SET price = :new WHERE id = :id AND price = :old')


def upgrade():
    for product_id, old, new in PRICES:
        op.execute(UPDATE.bindparams(id=product_id, old=old, new=new))


def downgrade():
    for product_id, old, new in PRICES:
        op.execute(UPDATE.bindparams(id=product_id, old=new, new=old))
