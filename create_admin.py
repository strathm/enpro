from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

def create_admin():
    with app.app_context():
        username = "admin1"
        email = "sammiedemesso@gmail.com"
        password = "admin123"

        if User.query.filter_by(email=email).first():
            print("Admin already exists.")
            return

        hashed_password = generate_password_hash(password)
        admin = User(username=username, email=email, password=hashed_password, role='admin')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")

if __name__ == "__main__":
    create_admin()
