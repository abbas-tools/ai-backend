import html
import os
import uuid
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

app = Flask(__name__)
app.secret_key = 'ahb_secure_secret_key_xyz_2026_ultra_secure'

# Cloudinary Configuration
cloudinary.config(
    cloud_name='a0ec1nvp',
    api_key='884661819567361',
    api_secret='R0IrtPJFveu0Tcbt3xSxsOtQSy4',
)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Admin Credentials
ADMIN_USER = 'admin'
ADMIN_PASS = 'KING56'


# ==============================================
# HELPER FUNCTIONS: Cloudinary se live data lana
# ==============================================
def get_cloudinary_files():
  """Cloudinary se baghair kisi folder restriction ke live files fetch karta hai."""
  files_dict = {}
  try:
    result = cloudinary.api.resources(type='upload', max_results=100)

    for resource in result.get('resources', []):
      public_id = resource.get('public_id')
      file_id = public_id.split('/')[-1] if '/' in public_id else public_id

      secure_url = resource.get('secure_url')
      format_ext = resource.get('format', 'file')
      original_filename = f"{file_id}.{format_ext}"

      bytes_size = resource.get('bytes', 0)
      if bytes_size < 1024 * 1024:
        size_str = f'{bytes_size / 1024:.1f} KB'
      else:
        size_str = f'{bytes_size / (1024 * 1024):.1f} MB'

      files_dict[file_id] = {
          'filename': original_filename,
          'cloud_url': secure_url,
          'public_id': public_id,
          'size': size_str,
      }
  except Exception as e:
    print(f'Error fetching from Cloudinary: {e}')

  return files_dict


def get_file_extension(filename):
  if '.' in filename:
    return f".{filename.rsplit('.', 1)[1].lower()}"
  return '.unknown'


# ==============================================
# ROUTE: Index (Landing Page)
# ==============================================
@app.route('/')
def index():
  return render_template('index.html')


# ==============================================
# ROUTE: Viewer Page
# ==============================================
@app.route('/file/<file_id>')
def viewer_page(file_id):
  files_db = get_cloudinary_files()

  if file_id not in files_db:
    abort(404)

  file_info = files_db[file_id]
  file_info['extension'] = get_file_extension(file_info['filename'])
  file_info['xml_content'] = (
      '<!-- Preview available via Cloud Storage link -->'
  )

  return render_template('viewer.html', file_info=file_info, file_id=file_id)


# ==============================================
# ROUTE: Download Ad Page
# ==============================================
@app.route('/download-ad/<file_id>')
def download_ad(file_id):
  files_db = get_cloudinary_files()

  if file_id not in files_db:
    abort(404)
  file_info = files_db[file_id]
  return render_template('ad_download.html', file_info=file_info, file_id=file_id)


# ==============================================
# ROUTE: Direct Download
# ==============================================
@app.route('/download/<file_id>')
def download_file(file_id):
  files_db = get_cloudinary_files()

  if file_id not in files_db:
    abort(404)
  file_info = files_db[file_id]
  return redirect(file_info['cloud_url'])


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
          cloudinary.uploader.upload(
              file, folder='ahb_file_hub', resource_type='auto'
          )
        except Exception as e:
          print(f'Cloudinary Upload Error: {e}')

        return redirect(url_for('admin_panel'))

  files_db = get_cloudinary_files()
  return render_template('admin.html', files=files_db)


# ==============================================
# ROUTE: Delete File
# ==============================================
@app.route('/admin/delete/<file_id>')
def delete_file(file_id):
  if not session.get('admin_logged'):
    return redirect(url_for('admin_login'))

  files_db = get_cloudinary_files()
  if file_id in files_db:
    try:
      public_id = files_db[file_id].get('public_id')
      if public_id:
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
      print(f'Error deleting file from cloud: {e}')

  return redirect(url_for('admin_panel'))


# ==============================================
# ROUTE: Logout
# ==============================================
@app.route('/logout')
def logout():
  session.pop('admin_logged', None)
  return redirect(url_for('index'))


if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=5000)
            
