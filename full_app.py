"""
Flash Transfer - Complete Version
"""
import os
from flask import Flask, request, jsonify, send_file, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import uuid

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
CORS(app)

app.config['SECRET_KEY'] = 'flash-transfer-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flash_transfer.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
app.config['RETENTION_DAYS'] = 10

# Ensure directories exist
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

db = SQLAlchemy(app)

# Database Models
class Transfer(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_type = db.Column(db.String(20), nullable=False)
    total_size = db.Column(db.BigInteger, nullable=False)
    file_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    download_count = db.Column(db.Integer, default=0)
    sender_email = db.Column(db.String(120))
    recipient_emails = db.Column(db.Text)
    
    files = db.relationship('File', backref='transfer', lazy=True, cascade='all, delete-orphan')

class File(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_id = db.Column(db.String(36), db.ForeignKey('transfer.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Plan Configuration
PLAN_LIMITS = {
    'free': 100 * 1024 * 1024 * 1024,
    'standard': 500 * 1024 * 1024 * 1024,
    'premium': 2 * 1024 * 1024 * 1024 * 1024
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    try:
        plan_type = request.form.get('plan_type', 'free')
        
        if plan_type not in PLAN_LIMITS:
            return jsonify({'error': 'Invalid plan type'}), 400
        
        total_size = 0
        files_data = []
        
        for file in request.files.getlist('files'):
            file_size = len(file.read())
            file.seek(0)
            total_size += file_size
        
        if total_size > PLAN_LIMITS[plan_type]:
            return jsonify({
                'error': f'File size exceeds {plan_type} plan limit'
            }), 400
        
        transfer = Transfer(
            plan_type=plan_type,
            total_size=total_size,
            file_count=len(request.files.getlist('files')),
            expires_at=datetime.utcnow() + timedelta(days=app.config['RETENTION_DAYS'])
        )
        db.session.add(transfer)
        db.session.flush()
        
        for file in request.files.getlist('files'):
            if file.filename:
                file_id = str(uuid.uuid4())
                original_filename = file.filename
                filename = f"{file_id}_{original_filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                file.save(file_path)
                
                file_record = File(
                    transfer_id=transfer.id,
                    filename=filename,
                    original_filename=original_filename,
                    file_size=os.path.getsize(file_path),
                    file_path=file_path
                )
                db.session.add(file_record)
                files_data.append({
                    'id': file_record.id,
                    'name': original_filename,
                    'size': file_record.file_size
                })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'transfer_id': transfer.id,
            'files': files_data,
            'expires_at': transfer.expires_at.isoformat(),
            'download_url': f'/download/{transfer.id}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transfer/<transfer_id>')
def get_transfer_info(transfer_id):
    transfer = Transfer.query.get(transfer_id)
    if not transfer:
        return jsonify({'error': 'Transfer not found'}), 404
    
    if datetime.utcnow() > transfer.expires_at:
        return jsonify({'error': 'Transfer has expired'}), 410
    
    files_data = [{
        'id': file.id,
        'name': file.original_filename,
        'size': file.file_size,
    } for file in transfer.files]
    
    return jsonify({
        'transfer_id': transfer.id,
        'plan_type': transfer.plan_type,
        'total_size': transfer.total_size,
        'file_count': transfer.file_count,
        'created_at': transfer.created_at.isoformat(),
        'expires_at': transfer.expires_at.isoformat(),
        'download_count': transfer.download_count,
        'files': files_data
    })

@app.route('/download/<transfer_id>')
def download_transfer(transfer_id):
    transfer = Transfer.query.get(transfer_id)
    if not transfer:
        return jsonify({'error': 'Transfer not found'}), 404
    
    if datetime.utcnow() > transfer.expires_at:
        return jsonify({'error': 'Transfer has expired'}), 410
    
    transfer.download_count += 1
    db.session.commit()
    
    if transfer.files:
        file_record = transfer.files[0]
        return send_file(
            file_record.file_path,
            as_attachment=True,
            download_name=file_record.original_filename
        )
    
    return jsonify({'error': 'No files found'}), 404

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    print("🚀 Flash Transfer Starting...")
    print(f"📁 Templates: {TEMPLATE_DIR}")
    print(f"📁 Uploads: {UPLOAD_DIR}")
    print("🌐 Server: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)