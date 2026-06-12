"""
Script Khởi Tạo Dữ Liệu Mẫu (Seed Data)
Tạo dữ liệu mẫu cho Hệ Thống Điểm Danh Thông Minh.
Chạy sau khi thực hiện migration database để có dữ liệu ban đầu.

Dữ liệu được tạo:
  - Năm học và học kỳ hiện tại (AcademicYear, Semester)
  - Cơ sở, tòa nhà, phòng học mẫu (Campus, Building, Room)
  - Khoa mẫu (Department)

Cách chạy: python seed_data.py
"""
from app import app
from models import db, Department, AcademicYear, Semester, Campus, Building, Room
from datetime import date


def seed_departments():
    """Create sample departments."""
    print("\nCreating sample departments...")
    
    departments_data = [
        {'code': 'CS', 'name': 'Computer Science', 'description': 'Department of Computer Science'},
        {'code': 'EE', 'name': 'Electrical Engineering', 'description': 'Department of Electrical Engineering'},
        {'code': 'ME', 'name': 'Mechanical Engineering', 'description': 'Department of Mechanical Engineering'},
        {'code': 'BA', 'name': 'Business Administration', 'description': 'Department of Business Administration'},
    ]
    
    for data in departments_data:
        existing = Department.query.filter_by(code=data['code']).first()
        if not existing:
            dept = Department(**data)
            db.session.add(dept)
            print(f"  ✓ Created department: {data['name']}")
        else:
            print(f"  ⚠️  Department {data['name']} already exists")
    
    db.session.commit()


def seed_academic_year_semester():
    """Create current academic year and semester."""
    print("\nCreating academic year and semester...")
    
    # Academic Year 2025-2026
    year_data = {
        'year': '2025-2026',
        'start_date': date(2025, 9, 1),
        'end_date': date(2026, 6, 30),
        'is_current': True
    }
    
    existing_year = AcademicYear.query.filter_by(year=year_data['year']).first()
    if not existing_year:
        academic_year = AcademicYear(**year_data)
        db.session.add(academic_year)
        db.session.commit()
        print(f"  ✓ Created academic year: {year_data['year']}")
    else:
        academic_year = existing_year
        print(f"  ⚠️  Academic year {year_data['year']} already exists")
    
    # Semester 2 (current)
    semester_data = {
        'name': 'Semester 2',
        'code': 'S2_2025_2026',
        'start_date': date(2026, 1, 6),
        'end_date': date(2026, 6, 15),
        'is_current': True,
        'academic_year_id': academic_year.id
    }
    
    existing_sem = Semester.query.filter_by(code=semester_data['code']).first()
    if not existing_sem:
        semester = Semester(**semester_data)
        db.session.add(semester)
        db.session.commit()
        print(f"  ✓ Created semester: {semester_data['name']}")
    else:
        print(f"  ⚠️  Semester {semester_data['name']} already exists")


def seed_campus_buildings_rooms():
    """Create sample campus, buildings, and rooms."""
    print("\nCreating campus, buildings, and rooms...")
    
    # Campus
    campus_data = {
        'code': 'MAIN',
        'name': 'Main Campus',
        'address': '123 University Road, City',
        'latitude': 10.8231,
        'longitude': 106.6297
    }
    
    existing_campus = Campus.query.filter_by(code=campus_data['code']).first()
    if not existing_campus:
        campus = Campus(**campus_data)
        db.session.add(campus)
        db.session.commit()
        print(f"  ✓ Created campus: {campus_data['name']}")
    else:
        campus = existing_campus
        print(f"  ⚠️  Campus {campus_data['name']} already exists")
    
    # Buildings
    buildings_data = [
        {'code': 'A', 'name': 'Building A', 'campus_id': campus.id},
        {'code': 'B', 'name': 'Building B', 'campus_id': campus.id},
        {'code': 'C', 'name': 'Building C', 'campus_id': campus.id},
    ]
    
    for data in buildings_data:
        existing_building = Building.query.filter_by(code=data['code']).first()
        if not existing_building:
            building = Building(**data)
            db.session.add(building)
            db.session.commit()
            print(f"  ✓ Created building: {data['name']}")
            
            # Create some rooms for this building
            for floor in range(1, 4):
                for room_num in range(1, 6):
                    room_code = f"{data['code']}{floor}{room_num:02d}"
                    room = Room(
                        code=room_code,
                        name=f"Room {room_code}",
                        capacity=40,
                        floor=floor,
                        building_id=building.id
                    )
                    db.session.add(room)
            
            db.session.commit()
            print(f"    ✓ Created 15 rooms for {data['name']}")
        else:
            print(f"  ⚠️  Building {data['name']} already exists")


def main():
    """Run all seed functions."""
    print("=" * 60)
    print("SEEDING INITIAL DATA FOR SMART ATTENDANCE SYSTEM")
    print("=" * 60)
    
    with app.app_context():
        try:
            seed_departments()
            seed_academic_year_semester()
            seed_campus_buildings_rooms()
            
            print("\n" + "=" * 60)
            print("✓ SEEDING COMPLETED SUCCESSFULLY")
            print("=" * 60)
            print("\nReference data is ready.")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Error during seeding: {str(e)}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    main()
