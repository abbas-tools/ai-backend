import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort

app = Flask(__name__)
app.secret_key = 'ahb_secure_secret_key_xyz_2026_ultra_secure'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory storage for file metadata
files_db = {}

# Admin Credentials
ADMIN_USER = "admin"
ADMIN_PASS = "KING56"

# ==============================================
# HELPER FUNCTION: Get file extension
# ==============================================
def get_file_extension(filename):
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return 'unknown'

# ==============================================
# HELPER FUNCTION: Get file size
# ==============================================
def get_file_size(file_path):
    try:
        size = os.path.getsize(file_path)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    except:
        return "Unknown"

# ==============================================
# HELPER FUNCTION: Read XML content (first few lines)
# ==============================================
def get_xml_preview(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(500)  # Read first 500 characters
            # Clean and format for display
            return content
    except:
        return "<!-- XML content preview unavailable -->"

# ==============================================
# ROUTE: Viewer Page
# ==============================================
@app.route('/file/<file_id>')
def viewer_page(file_id):
    if file_id not in files_db:
        abort(404)
    
    file_info = files_db[file_id]
    stored_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info['stored_name'])
    
    # Add additional metadata
    file_info['extension'] = f".{get_file_extension(file_info['filename'])}"
    file_info['size'] = get_file_size(stored_path)
    file_info['date'] = "Today"  # You can add actual date logic
    file_info['xml_content'] = get_xml_preview(stored_path)
    
    return render_template('viewer.html', file_info=file_info, file_id=file_id)

# ==============================================
# ROUTE: Download Ad Page
# ==============================================
@app.route('/download-ad/<file_id>')
def download_ad(file_id):
    if file_id not in files_db:
        abort(404)
    file_info = files_db[file_id]
    return render_template('ad_download.html', file_info=file_info, file_id=file_id)

# ==============================================
# ROUTE: Direct Download
# ==============================================
@app.route('/download/<file_id>')
def download_file(file_id):
    if file_id not in files_db:
        abort(404)
    file_info = files_db[file_id]
    return send_from_directory(
        app.config['UPLOAD_FOLDER'], 
        file_info['stored_name'], 
        as_attachment=True,
        download_name=file_info['filename']
    )

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
            error = "Invalid Username or Password!"
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
                file_id = str(uuid.uuid4())[:8]
                filename = file.filename
                stored_name = f"{file_id}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
                file.save(file_path)
                
                files_db[file_id] = {
                    'filename': filename,
                    'stored_name': stored_name
                }
                return redirect(url_for('admin_panel'))

    return render_template('admin.html', files=files_db)

# ==============================================
# ROUTE: Delete File
# ==============================================
@app.route('/admin/delete/<file_id>')
def delete_file(file_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    if file_id in files_db:
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], files_db[file_id]['stored_name'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
        del files_db[file_id]
    return redirect(url_for('admin_panel'))

# ==============================================
# ROUTE: Logout
# ==============================================
@app.route('/logout')
def logout():
    session.pop('admin_logged', None)
    return redirect(url_for('index'))

# ==============================================
# ROUTE: Index
# ==============================================
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)