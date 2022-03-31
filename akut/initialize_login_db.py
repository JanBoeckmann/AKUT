from akut import User_Region, Region, User, login_db, bcrypt

login_db.drop_all()
login_db.create_all()

user_admin = User(username='admin', email='admin@admin.de',
                  password=bcrypt.generate_password_hash('adminpass').decode('utf-8'))
login_db.session.add_all([user_admin])
region_fischbach = Region(name='Fischbach', admin_id='1')
region_fischbach.users.append(User_Region(user=user_admin))

login_db.session.commit()
