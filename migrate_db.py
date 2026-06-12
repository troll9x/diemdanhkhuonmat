"""
Script Migration Database (Database Migration)
Script chạy một lần để cập nhật cấu trúc database sau khi thay đổi models.
An toàn khi chạy nhiều lần (kiểm tra cột đã tồn tại trước khi thêm).

Cách chạy: python migrate_db.py

Danh sách migrations:
  - attendance_sessions: thêm cột latitude, longitude, late_after_minutes, session_type
  - app_enrollments: thêm cột joined_at
  - app_attendance_records: thêm cột is_late, distance_meters, reject_reason
  - app_face_embeddings: thêm cột pose
"""
import logging
logging.disable(logging.CRITICAL)

from app import create_app
from models import db

app = create_app()

MIGRATIONS = [
    # attendance_sessions: new columns
    ("attendance_sessions", "session_type",         "VARCHAR(10) NOT NULL DEFAULT 'start'"),
    ("attendance_sessions", "scheduled_start_time", "TIME"),
    ("attendance_sessions", "late_after_minutes",   "INTEGER NOT NULL DEFAULT 15"),
    # attendance_sessions: remove old unique, add new — handled by recreating index below

    # app_attendance_records: new column
    ("app_attendance_records", "is_late", "BOOLEAN NOT NULL DEFAULT 0"),
]

NEW_TABLES = [
    "app_class_schedules",
]

with app.app_context():
    conn = db.engine.raw_connection()
    cur = conn.cursor()

    # 1. Add missing columns
    for table, column, col_def in MIGRATIONS:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cur.fetchall()]
        if column not in cols:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                print(f"  + {table}.{column}")
            except Exception as e:
                print(f"  ! {table}.{column}: {e}")
        else:
            print(f"  = {table}.{column} already exists")

    conn.commit()

    # 2. Create new tables (db.create_all handles existing ones safely)
    db.create_all()
    print("  + New tables created (if not existing)")

    # 3. Fix unique constraint on attendance_sessions
    #    SQLite can't DROP CONSTRAINT; we need to recreate the index.
    #    First drop old unique index if it exists, then create the new one.
    try:
        cur.execute("DROP INDEX IF EXISTS uq_session_classroom_date")
        print("  - Dropped old index uq_session_classroom_date")
    except Exception as e:
        print(f"  ! Drop old index: {e}")

    try:
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_session_classroom_date_type
            ON attendance_sessions (classroom_id, session_date, session_type)
        """)
        print("  + Created index uq_session_classroom_date_type")
    except Exception as e:
        print(f"  ! Create new index: {e}")

    conn.commit()
    conn.close()
    print("\nMigration complete.")
