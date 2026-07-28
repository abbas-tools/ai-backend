import os
import uuid
from flask import Flask, request, jsonify, render_template, abort, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "abbas_super_secret_key_king5656"

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory storage for site customizations (Admin control)
site_config = {
    "site_title": "AHB FILE HUB",
    "theme_glow": "#4facfe"
}

# --- HOME / UPLOAD PAGE ---
@app.route('/')
def index():
    return render_template('index.html', config=site_config)

# --- XML UPLOAD ENDPOINT ---
@app.route('/upload-xml', methods=['POST'])
def upload_xml():
    if 'xml_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['xml_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.xml'):
        file_id = uuid.uuid4().hex
        filename = f"{file_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        share_url = request.host_url + f"view/{file_id}"
        return jsonify({'success': True, 'share_url': share_url})
    
    return jsonify({'error': 'Only .xml files are allowed'}), 400

# --- SECURE ISOLATED VIEWER PAGE (With Smart Link & Banner Ads) ---
@app.route('/view/<file_id>')
def view_xml(file_id):
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.startswith(file_id):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            original_name = filename.split('_', 1)[1]
            return render_template('viewer.html', content=content, filename=original_name, config=site_config)
            
    return abort(404, description="XML file not found or link expired.")

# --- ADMIN PANEL LOGIN ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'KING5656':
            session['admin_logged'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Wrong Password! Access Denied.'
    return render_template('admin_login.html', error=error)

# --- ADMIN DASHBOARD & CUSTOMIZATION ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        site_config['site_title'] = request.form.get('site_title', 'AHB FILE HUB')
        site_config['theme_glow'] = request.form.get('theme_glow', '#4facfe')
        return redirect(url_for('admin_dashboard'))
    
    # List all uploaded files for admin overview
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('admin.html', config=site_config, files=files)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
