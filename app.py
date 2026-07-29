import html
import os
import uuid
import json
from datetime import datetime
import cloudinary
import cloudinary.api
import cloudinary.uploader
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_from_directory,
)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ==============================================
# CONFIGURATION: Environment Variables se le rahe hain
# ==============================================
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ahb_secure_secret_key_xyz_2026_ultra_secure')

# Cloudinary Configuration (Environment Variables se)
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'a0ec1nvp'),
    api_key=os.getenv('CLOUDINARY_API_KEY', '884661819567361'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET', 'R0IrtPJFveu0Tcbt3xSxsOtQSy4'),
)

# ==============================================
# LOCAL STORAGE: Render Persistent Disk ke liye
# ==============================================
# Render par persistent disk mount path
# Local development ke liye 'uploads' folder
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
METADATA_FILE = os.path.join(UPLOAD_FOLDER, 'file_metadata.json')

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Admin Credentials (Environment Variables se)
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'KING56')

# ==============================================
# HELPER FUNCTIONS: File Metadata Management
# ==============================================
def load_metadata():
    """Load file metadata from JSON file"""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f'Error loading metadata: {e}')
            return {}
    return {}

def save_metadata(metadata):
    """Save file metadata to JSON file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f'Metadata saved successfully to {METADATA_FILE}')
    except Exception as e:
        print(f'Error saving metadata: {e}')

def get_all_files():
    """Get all files from local storage with metadata"""
    metadata = load_metadata()
    files_dict = {}
    
    try:
        # Get files from local storage
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path) and filename != 'file_metadata.json':
                # Extract file_id from filename (remove extension)
                file_id = filename.split('.')[0]
                file_info = metadata.get(file_id, {})
                
                # Get file size
                bytes_size = os.path.getsize(file_path)
                if bytes_size < 1024 * 1024:
                    size_str = f'{bytes_size / 1024:.1f} KB'
                else:
                    size_str = f'{bytes_size / (1024 * 1024):.1f} MB'
                
                files_dict[file_id] = {
                    'filename': file_info.get('original_filename', filename),
                    'local_path': file_path,
                    'cloud_url': file_info.get('cloud_url', ''),
                    'public_id': file_info.get('public_id', ''),
                    'size': size_str,
                    'upload_date': file_info.get('upload_date', ''),
                    'file_size_bytes': bytes_size,
                }
    except Exception as e:
        print(f'Error reading files: {e}')
    
    return files_dict

def generate_unique_link(file_id):
    """Generate unique link for file"""
    return url_for('viewer_page', file_id=file_id, _external=True)

def get_file_extension(filename):
    if '.' in filename:
        return f".{filename.rsplit('.', 1)[1].lower()}"
    return '.unknown'

def get_file_size_format(bytes_size):
    """Convert bytes to human readable format"""
    if bytes_size < 1024 * 1024:
        return f'{bytes_size / 1024:.1f} KB'
    elif bytes_size < 1024 * 1024 * 1024:
        return f'{bytes_size / (1024 * 1024):.1f} MB'
    else:
        return f'{bytes_size / (1024 * 1024 * 1024):.1f} GB'

# ==============================================
# ROUTE: Index (Landing Page)
# ==============================================
@app.route('/')
def index():
    return render_template('index.html')

# ==============================================
# ROUTE: Viewer Page with Unique Link
# ==============================================
@app.route('/file/<file_id>')
def viewer_page(file_id):
    files_db = get_all_files()
    
    if file_id not in files_db:
        abort(404)
    
    file_info = files_db[file_id]
    file_info['extension'] = get_file_extension(file_info['filename'])
    
    # Generate unique link for sharing
    unique_link = generate_unique_link(file_id)
    
    return render_template('viewer.html', 
                         file_info=file_info, 
                         file_id=file_id,
                         unique_link=unique_link)

# ==============================================
# ROUTE: Download Ad Page
# ==============================================
@app.route('/download-ad/<file_id>')
def download_ad(file_id):
    files_db = get_all_files()
    
    if file_id not in files_db:
        abort(404)
    file_info = files_db[file_id]
    return render_template('ad_download.html', file_info=file_info, file_id=file_id)

# ==============================================
# ROUTE: Direct Download
# ==============================================
@app.route('/download/<file_id>')
def download_file(file_id):
    files_db = get_all_files()
    
    if file_id not in files_db:
        abort(404)
    
    file_info = files_db[file_id]
    
    # Check if file exists locally
    local_path = file_info.get('local_path')
    if local_path and os.path.exists(local_path):
        # Serve from local storage
        directory = os.path.dirname(local_path)
        filename = os.path.basename(local_path)
        return send_from_directory(directory, filename, as_attachment=True)
    elif file_info.get('cloud_url'):
        # Fallback to Cloudinary
        return redirect(file_info['cloud_url'])
    else:
        abort(404)

# ==============================================
# ROUTE: Admin Login
# ==============================================
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = 'Invalid Username or Password!'
    return render_template('admin_login.html', error=error)

# ==============================================
# ROUTE: Admin Panel
# ==============================================
@app.route('/admin-panel', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                try:
                    # Generate unique ID for file
                    file_id = str(uuid.uuid4())[:8]
                    
                    # Get file extension
                    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                    local_filename = f"{file_id}.{ext}" if ext else file_id
                    local_path = os.path.join(UPLOAD_FOLDER, local_filename)
                    
                    # Save file locally first
                    file.save(local_path)
                    print(f'File saved locally: {local_path}')
                    
                    # Upload to Cloudinary
                    cloud_result = cloudinary.uploader.upload(
                        local_path,  # Upload from local path
                        public_id=f"ahb_file_hub/{file_id}",
                        resource_type='auto'
                    )
                    print(f'File uploaded to Cloudinary: {cloud_result.get("secure_url")}')
                    
                    # Save metadata
                    metadata = load_metadata()
                    metadata[file_id] = {
                        'original_filename': file.filename,
                        'cloud_url': cloud_result.get('secure_url', ''),
                        'public_id': cloud_result.get('public_id', ''),
                        'upload_date': datetime.now().isoformat(),
                        'file_size': os.path.getsize(local_path),
                    }
                    save_metadata(metadata)
                    
                except Exception as e:
                    print(f'Upload Error: {e}')
                    import traceback
                    traceback.print_exc()
                
                return redirect(url_for('admin_panel'))
    
    files_db = get_all_files()
    return render_template('admin.html', files=files_db)

# ==============================================
# ROUTE: Delete File
# ==============================================
@app.route('/admin/delete/<file_id>')
def delete_file(file_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    
    files_db = get_all_files()
    if file_id in files_db:
        try:
            # Delete from local storage
            local_path = files_db[file_id].get('local_path')
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
                print(f'Deleted local file: {local_path}')
            
            # Delete from Cloudinary
            public_id = files_db[file_id].get('public_id')
            if public_id:
                cloudinary.uploader.destroy(public_id)
                print(f'Deleted from Cloudinary: {public_id}')
            
            # Remove from metadata
            metadata = load_metadata()
            if file_id in metadata:
                del metadata[file_id]
                save_metadata(metadata)
                
        except Exception as e:
            print(f'Error deleting file: {e}')
    
    return redirect(url_for('admin_panel'))

# ==============================================
# ROUTE: Health Check (Render ke liye)
# ==============================================
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

# ==============================================
# ROUTE: Logout
# ==============================================
@app.route('/logout')
def logout():
    session.pop('admin_logged', None)
    return redirect(url_for('index'))

# ==============================================
# ERROR HANDLERS
# ==============================================
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
