"""
Flash Transfer - Fixed Version
"""
import os
from flask import Flask, render_template

app = Flask(__name__)

# Get the absolute path to the current directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

print(f"Base directory: {BASE_DIR}")
print(f"Template directory: {TEMPLATE_DIR}")
print(f"Template exists: {os.path.exists(TEMPLATE_DIR)}")

if os.path.exists(TEMPLATE_DIR):
    print("Files in templates directory:")
    for file in os.listdir(TEMPLATE_DIR):
        print(f"  - {file}")

@app.route('/')
def index():
    """Serve the main application"""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error loading template: {str(e)}", 500

@app.route('/test')
def test():
    """Test route to check if Flask is working"""
    return "Flask is working! If you can see this, the backend is running."

if __name__ == '__main__':
    print("Starting Flash Transfer...")
    print("Access the application at: http://localhost:5000")
    print("Test route at: http://localhost:5000/test")
    app.run(debug=True, host='0.0.0.0', port=5000)