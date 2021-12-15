from akut import User_Region, Region, User, login_db, bcrypt

login_db.drop_all()
login_db.create_all()

hashed_pw = bcrypt.generate_password_hash('adminpass').decode('utf-8')
user_admin = User(username='admin', email='admin@admin.de', password=hashed_pw)
hashed_pw = bcrypt.generate_password_hash('asdf').decode('utf-8')
user_andi = User(username='Andi', email='a@b.de', password=hashed_pw)
region_fischbach = Region(name='Fischbach')

login_db.session.add(user_admin)
login_db.session.add(user_andi)
login_db.session.add(region_fischbach)
region_fischbach.users.append(User_Region(user=user_admin))
login_db.session.commit()
"""
delete = User.query.filter_by(username='admin').delete()
login_db.session.commit()

delete = User.query.filter_by(username='admin').first()
login_db.session.delete(delete)
"""

login_db.session.commit()