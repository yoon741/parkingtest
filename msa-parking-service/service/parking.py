from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from models.parking import Parking, Parkseat
from schema.parking import ParkingBase
from service.database import db_url

engine = create_engine(db_url, echo=True)

def create_triggers():
    # 차량번호 입력 하여 parking 테이블에 저장하면 trigger 작동 (parkseat에 값 저장)
    trigger_sql_parking = """
    CREATE TRIGGER IF NOT EXISTS after_insert_parking
    AFTER INSERT ON parking
    FOR EACH ROW
    BEGIN
        INSERT INTO parkseat (carnum, barrier) VALUES (NEW.carnum, NEW.barrier);
    END;
    """

    # 결제완료 시 payment 테이블에 저장 된 paydate에 값이 채워지면
    # parkseat에 동일한 carnum 데이터 삭제
    trigger_sql_payment = """
    CREATE TRIGGER IF NOT EXISTS remove_parkseat
    AFTER UPDATE ON payment
    FOR EACH ROW
    WHEN OLD.paydate IS NULL AND NEW.paydate IS NOT NULL
    BEGIN
        DELETE FROM parkseat WHERE carnum = NEW.carnum;
    END;
    """

    with engine.connect() as connection:
        # 주차 트리거가 존재하는지 확인 후 생성
        existing_trigger_parking = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='after_insert_parking'")
        ).fetchone()

        if not existing_trigger_parking:
            connection.execute(text(trigger_sql_parking))

        # 결제 트리거가 존재하는지 확인 후 생성
        existing_trigger_payment = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='remove_parkseat'")
        ).fetchone()

        if not existing_trigger_payment:
            connection.execute(text(trigger_sql_payment))


# 입차
# 차량번호 입력 시 parking테이블에 저장
def register(db: Session, parking: ParkingBase):
    parking = Parking(**parking.model_dump())
    db.add(parking)
    db.commit()
    db.refresh(parking)

    return {
        "carnum": parking.carnum,
        "barrier": parking.barrier,
        "intime": parking.intime,
        "outtime": parking.outtime,
    }

# 입차 내역 전부 조회
def carlists(db: Session, parknum: str):
    query = (
        db.query(Parkseat.carnum, Parking.intime, Parking.pno)
        .join(Parking, Parking.carnum == Parkseat.carnum)
        .filter(Parkseat.carnum.like(f"%{parknum}"))
    )
    result = query.all()
    return [{"carnum": row[0], "intime": row[1], "pno":row[2]} for row in result]

# 출차
# carlists에서 주차한 차를 선택해서 outregist페이지로 넘어갈 때 outtime 저장
def set_outtime(db: Session, pno: int):
    parking = db.query(Parking).filter(Parking.pno == pno).first()

    if not parking:
        return {"error": "Car not found"}

    parking.outtime = datetime.now()
    db.commit()

# 차량 정보 출력
# total_time = parking.outtime - parking.intime
# total_minutes = total_time.total_seconds() / 60
#
# rate_10min = 1500       # 회차시간 15분 / 10분당 1500원
# total_fee = int((max(0, total_minutes - 15) / 10) * rate_10min)
#
# return {
#     "carnum": parking.carnum,
#     "intime": parking.intime,
#     "outtime": parking.outtime,
#     "total_minutes": total_minutes,
#     "total_fee": total_fee
# }
