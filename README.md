# Quiz Master Application

A Flask-based web application for managing and taking quizzes. This application allows administrators to create subjects, chapters, and quizzes, while students can take quizzes and view their results.

## Features

- User Authentication (Admin and Student roles)
- Subject Management
- Chapter Management
- Quiz Creation and Management
- Question Management
- Quiz Taking and Scoring
- Result Viewing and Reports

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd quiz-master
```

2. Create a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

The application uses SQLite as its database. The database file will be automatically created in the `instance` folder when you run the application for the first time.

## Running the Application

1. Activate the virtual environment if not already activated:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

2. Run the Flask application:
```bash
python app.py
```

3. Access the application in your web browser at: `http://localhost:5000`

## Default Admin Account

The application creates a default admin account on first run:
- Email: admin@example.com
- Password: admin123

## Project Structure

```
quiz-master/
├── app.py              # Main application file
├── models.py           # Database models
├── requirements.txt    # Project dependencies
├── instance/          # Database directory
│   └── quiz_app.db    # SQLite database file
└── templates/         # HTML templates
    ├── dashboard.html
    ├── login.html
    ├── register.html
    ├── manage_subjects.html
    ├── manage_chapters.html
    ├── manage_quizzes.html
    ├── manage_questions.html
    ├── quiz_view.html
    ├── results.html
    └── view_reports.html
```

## Usage

1. Log in as admin using the default credentials
2. Create subjects, chapters, and quizzes
3. Add questions to quizzes
4. Create student accounts or let students register
5. Students can take quizzes and view their results
6. Admin can view comprehensive reports

## Security Notes

1. Change the default admin password after first login
2. Update the `SECRET_KEY` in `app.py` for production use
3. Use HTTPS in production
4. Implement proper backup procedures for the database

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
