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
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ahb_secure_secret_key_xyz_2026_ultra_secure')

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'a0ec1nvp'),
    api_key=os.getenv('CLOUDINARY_API_KEY', '884661819567361'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET', 'R0IrtPJFveu0Tcbt3xSxsOtQSy4'),
)

# Metadata JSON - Cloudinary par depend karein
METADATA_FILE = 'file_metadata.json'  # Yeh bhi ephemeral hai but sirf metadata hai

# Admin Credentials
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'KING56')


# ==============================================
# HELPER FUNCTIONS
# ==============================================
def load_metadata():
    """Load file metadata from JSON file"""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_metadata(metadata):
    """Save file metadata to JSON file"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def get_all_files():
    """Get all files from Cloudinary only"""
    metadata = load_metadata()
    files_dict = {}
    
    try:
        # Cloudinary se files fetch karein
        result = cloudinary.api.resources(
            type='upload', 
            prefix='ahb_file_hub/',
            max_results=100
        )
        
        for resource in result.get('resources', []):
            public_id = resource.get('public_id')
            file_id = public_id.split('/')[-1] if '/' in public_id else public_id
            
            # Metadata se info lein
            file_info = metadata.get(file_id, {})
            
            bytes_size = resource.get('bytes', 0)
            if bytes_size < 1024 * 1024:
                size_str = f'{bytes_size / 1024:.1f} KB'
            else:
                size_str = f'{bytes_size / (1024 * 1024):.1f} MB'
            
            files_dict[file_id] = {
                'filename': file_info.get('original_filename', f"{file_id}.{resource.get('format', 'file')}"),
                'cloud_url': resource.get('secure_url'),
                'public_id': public_id,
                'size': size_str,
                'upload_date': file_info.get('upload_date', ''),
                'format': resource.get('format', 'unknown'),
            }
    except Exception as e:
        print(f'Error fetching from Cloudinary: {e}')
    
    return files_dict

def generate_unique_link(file_id):
    """Generate unique link for file"""
    return url_for('viewer_page', file_id=file_id, _external=True)

def get_file_extension(filename):
    if '.' in filename:
        return f".{filename.rsplit('.', 1)[1].lower()}"
    return '.unknown'


# ==============================================
# ROUTES
# ==============================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/file/<file_id>')
def viewer_page(file_id):
    files_db = get_all_files()
    
    if file_id not in files_db:
        abort(404)
    
    file_info = files_db[file_id]
    file_info['extension'] = get_file_extension(file_info['filename'])
    unique_link = generate_unique_link(file_id)
    
    return render_template('viewer.html', 
                         file_info=file_info, 
                         file_id=file_id,
                         unique_link=unique_link)

@app.route('/download-ad/<file_id>')
def download_ad(file_id):
    files_db = get_all_files()
    if file_id not in files_db:
        abort(404)
    file_info = files_db[file_id]
    return render_template('ad_download.html', file_info=file_info, file_id=file_id)

@app.route('/download/<file_id>')
def download_file(file_id):
    files_db = get_all_files()
    if file_id not in files_db:
        abort(404)
    file_info = files_db[file_id]
    return redirect(file_info['cloud_url'])

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

@app.route('/admin-panel', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                try:
                    file_id = str(uuid.uuid4())[:8]
                    
                    # Direct Cloudinary upload
                    cloud_result = cloudinary.uploader.upload(
                        file,
                        public_id=f"ahb_file_hub/{file_id}",
                        resource_type='auto'
                    )
                    
                    # Save metadata
                    metadata = load_metadata()
                    metadata[file_id] = {
                        'original_filename': file.filename,
                        'cloud_url': cloud_result.get('secure_url', ''),
                        'public_id': cloud_result.get('public_id', ''),
                        'upload_date': datetime.now().isoformat(),
                    }
                    save_metadata(metadata)
                    
                except Exception as e:
                    print(f'Upload Error: {e}')
                
                return redirect(url_for('admin_panel'))
    
    files_db = get_all_files()
    return render_template('admin.html', files=files_db)

@app.route('/admin/delete/<file_id>')
def delete_file(file_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    
    files_db = get_all_files()
    if file_id in files_db:
        try:
            # Cloudinary se delete
            public_id = files_db[file_id].get('public_id')
            if public_id:
                cloudinary.uploader.destroy(public_id)
            
            # Metadata se delete
            metadata = load_metadata()
            if file_id in metadata:
                del metadata[file_id]
                save_metadata(metadata)
                
        except Exception as e:
            print(f'Error deleting file: {e}')
    
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.pop('admin_logged', None)
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
