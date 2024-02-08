import os
import time
import zipfile
import json

from flask import Flask, request, redirect, url_for, send_file, flash, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

SHARED_DIRECTORY = os.getcwd()
app = Flask(__name__)

# Config app
local_config = os.path.join(SHARED_DIRECTORY, '.netfshare', 'config.json')
try:
    print('config from local file: ', local_config)
    app.config.from_file(local_config, load=json.load, text=False)
except Exception as e:
    print(f'Exception: {e}\nUsing default config.')
    app.config.from_object('config')

# Config database
db_path = os.path.join(SHARED_DIRECTORY, '.netfshare', 'dir_config.db')
print(os.path.dirname(db_path))
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

db = SQLAlchemy(app)


# Directory DB model
class Directory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.Integer, default=0)
    path = db.Column(db.String(64), nullable=True)

    def __init__(self, path):
        self.path = path
        self.mode = 0

    def __repr__(self):
        return f'Directory: {self.path} (share mode {self.mode})'

# Scan the shared directory and add subdirectories to the DB
with app.app_context():
    db.create_all()

    for directory in os.listdir(SHARED_DIRECTORY):
        if os.path.isdir(directory):
            if not Directory.query.filter(Directory.path == directory).first():
                db.session.add(Directory(directory))
    db.session.commit()


# Helper functions
def available_dirs(mode):
    """
    Returns a list of all directories that are available for the given mode.
    Excludes directories that are in the exclude_dirnames list.
    """
    all_dirs = [dir for dir in os.listdir(SHARED_DIRECTORY) if os.path.basename(dir) not in app.config["EXCLUDE_DIRNAMES"]]
    matching_mode_paths = [dir.path for dir in Directory.query.filter(Directory.mode==mode).all()]
    return [_ for _ in all_dirs if _ in matching_mode_paths]


def check_admin(request):
    is_admin = False
    if (request.remote_addr) in str(request.host):
        is_admin = True
    return is_admin


# Views
@app.route("/", methods=["GET", "POST"])
def list_dirs():
    """
    View to list directories on the server.
    """
    #not_shared_dirs = available_dirs(0)
    read_only_dirs = available_dirs(1)
    upload_only_dirs = available_dirs(2)

    # Admin check and management forms
    admin = False
    if check_admin(request):
        admin = True
        print('you are admin')
    else:
        print('not admin')
    
    return render_template(
        'list_dirs.html',
        admin=admin,
        read_only_dirs=read_only_dirs, 
        upload_only_dirs=upload_only_dirs
        )


@app.route("/download/<path>")
def download(path):
    """
    Download read_only directory.
    Package the directory as a zip file and serves it.
    """
    if not os.path.isdir(os.path.join(SHARED_DIRECTORY, path)):
        print(path, ' not a directory')
        return redirect(url_for('list_dirs'))
    else:
        zip_file = os.path.join(SHARED_DIRECTORY, '.netfshare', path + '.zip')
        refresh_file = False
        if os.path.isfile(zip_file):
            if os.path.getmtime(zip_file) < os.path.getmtime(os.path.join(SHARED_DIRECTORY, path)):
                refresh_file = True
                print('files changed')
            elif os.path.getmtime(zip_file)-time.time() > app.config['REFRESH_TIME']:
                print('file expired')
                refresh_file = True

        if not os.path.isfile(zip_file) or refresh_file:
            print('generating zip file...')
            with zipfile.ZipFile(zip_file, 'w') as zipf:
                for root, dirs, files in os.walk(os.path.join(SHARED_DIRECTORY, path)):
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, os.path.join(SHARED_DIRECTORY, path))                                
                        zipf.write(file_path, relative_path)
        return send_file(zip_file, as_attachment=True)


@app.route("/upload/<path>", methods=["GET", "POST"])
def upload_dir(path):
    """
    Select a file to upload to the selected (`path`) directory
    on the server.
    """
    if request.method == 'POST':
        target_path = os.path.join(SHARED_DIRECTORY, path)
        upload_name = request.form.get('upload_name')
        if upload_name:
            target_path = os.path.join(target_path, upload_name)
            uploaded_files = request.files.getlist('file')

            if len(uploaded_files) > app.config['MAX_FILES']:
                flash(f'Preveč datotek. Največ {app.config["MAX_FILES"]} neenkrat.', 'error')
                return redirect(url_for('upload_dir', path=path))
            
            if os.path.exists(target_path):
                flash(f'Datotke z istim imenom že obstajajo.', 'error')
                return redirect(url_for('upload_dir', path=path))
            
            for file in uploaded_files:
                if file:
                    dirname = os.path.dirname(file.filename)
                    save_dir = os.path.join(target_path, dirname)
                    filename = secure_filename(file.filename)
                    # Handle nested subdirectories
                    file_path = os.path.join(save_dir, filename)
                    print(file_path)
                    os.makedirs(save_dir, exist_ok=True)
                    file.save(file_path)
            flash(f'{len(uploaded_files)} datotek uspešno naloženih.', 'success')
            return redirect(url_for('upload_dir', path=path))
        else:
            flash('Prosim vpišite vpisno številko.', 'error')
            return redirect(url_for('upload_dir', path=path))
        
    return render_template('upload.html', path=path)


@app.route("/copy_config")
def copy_config():
    if check_admin(request):
        config_copy_keys = [
            'DEBUG', 'SECRET_KEY', 'WTF_CSRF_ENABLED', 'SQLALCHEMY_DATABASE_URI', 
            'REFRESH_TIME', 'SHARE_MODES', 'EXCLUDE_DIRNAMES'
        ]
        config_items = [(k, app.config[k]) for k in config_copy_keys if k in app.config.keys()]
        with open(local_config, 'w') as f:
            json.dump(dict(config_items), f, indent=2)
        return redirect(url_for('admin_view'))
    else:
        return redirect(url_for('list_dirs'))


@app.route("/admin", methods=["GET", "POST"])
def admin_view():
    # Admin check and management forms
    context = {}
    if check_admin(request):
        print('you are admin')
        context['admin'] = True

        # Populate shared dir management forms
        manage_dirs = [dir for dir in Directory.query.all() if dir.path in os.listdir(SHARED_DIRECTORY)]
        context['manage_dirs'] = manage_dirs

        # Validate and update share mode
        if request.method == 'POST':
            for id, value in request.form.items():
                if id in [str(d.id) for d in Directory.query.all()]:
                    if value in [str(k) for k in app.config["SHARE_MODES"].keys()]:
                        dir = Directory.query.filter(Directory.id == int(id)).first()
                        dir.mode = int(value)
                        db.session.commit()
            return redirect(url_for('admin_view'))
            
    else:
        return redirect(url_for('list_dirs'))
    
    return render_template(
        'admin.html',
        share_modes=app.config["SHARE_MODES"],
        exclude_dirnames=app.config["EXCLUDE_DIRNAMES"],
        **context
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, host='0.0.0.0')