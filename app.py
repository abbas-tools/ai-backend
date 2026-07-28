import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort

app = Flask(__name__)
app.secret_key = 'ahb_secure_secret_key_xyz'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory storage for file metadata (Use database for production persistence)
files_db = {}

ADMIN_USER = "admin"
ADMIN_PASS = "ahb123"

@app.route('/')
def index():
    # Main page par public upload nahi hoga, yahan aap chahein toh landing text ya general hub dikha sakte hain
    return render_template('index.html')

@app.route('/file/<file_id>')
def viewer_page(file_id):
    if file_id not in files_db:
        abort(404)
    file_info = files_db[file_id]
    return render_template('viewer.html', file_info=file_info, file_id=file_id)

@app.route('/download-ad/<file_id>')
def download_ad(file_id):
    if file_id not in files_db:
        abort(404)
    file_info = files_db[file_id]
    return render_template('ad_download.html', file_info=file_info, file_id=file_id)

@app.route('/download/<file_id>')
def download_file(file_id):
    if file_id not in files_db:
        abort(404)
    file_info = files_db[file_id]
    return send_from_directory(app.config['UPLOAD_FOLDER'], file_info['stored_name'], as_attachment=True)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged'] = True
            return redirect(url_for('admin_panel'))
    return render_template('admin_login.html')

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
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
                file.save(file_path)
                
                files_db[file_id] = {
                    'filename': filename,
                    'stored_name': f"{file_id}_{filename}"
                }
                return redirect(url_for('admin_panel'))

    return render_template('admin.html', files=files_db)

@app.route('/admin/delete/<file_id>')
def delete_file(file_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    if file_id in files_db:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], files_db[file_id]['stored_name']))
        except:
            pass
        del files_db[file_id]
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.pop('admin_logged', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
    
