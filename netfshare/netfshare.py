import os
import time
import zipfile
import json
import datetime
import socket
from functools import wraps
from pythonping import ping

from flask import (Flask, Blueprint, request, redirect, url_for, 
                   send_file, flash, render_template, )
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

SHARED_DIRECTORY = os.getcwd()
app = Flask(__name__)

# Register this module as view Blueprint
netfshare = Blueprint('netfshare', __name__)
 
# Config app
local_config = os.path.join(SHARED_DIRECTORY, '.netfshare', 'config.json')
print(f'Starting netfshare in {SHARED_DIRECTORY}...')
try:
    print('config from local file: ', local_config)
    app.config.from_file(local_config, load=json.load, text=False)
except Exception as e:
    print(f'Exception: {e}\nUsing default config.')
    app.config.from_object('netfshare.config')

# Config database
db_path = os.path.join(SHARED_DIRECTORY, '.netfshare', 'dir_config.db')
print(os.path.dirname(db_path))
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

db = SQLAlchemy(app)

# DB models
class Directory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.Integer, default=0)
    path = db.Column(db.String(64), nullable=True)
    # # Backref relationships to access directory from download and upload:
    downloads = db.relationship('Download', backref='directory')
    uploads = db.relationship('Upload', backref='directory')

    def __init__(self, path):
        self.path = path
        self.mode = 0

    def __repr__(self):
        return f'Directory: {self.path} (share mode {self.mode})'
    
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(64), nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.datetime.now)
    selected_name = db.Column(db.String(64), nullable=True)
    active = db.Column(db.Boolean, default=False)
    # Backref relationships to access client from download and upload:
    downloads = db.relationship('Download', backref='client')
    uploads = db.relationship('Upload', backref='client')

    def __init__(self, address):
        self.address = address

    def __repr__(self):
        return f'Client: {self.address} (name: {self.selected_name}), active: {self.active}, (last seen {self.last_seen})'
    
class Download(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    directory_id = db.Column(db.Integer, db.ForeignKey('directory.id'))
    download_time = db.Column(db.DateTime, default=datetime.datetime.now)

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    directory_id = db.Column(db.Integer, db.ForeignKey('directory.id'))
    upload_time = db.Column(db.DateTime, default=datetime.datetime.now)
    files_count = db.Column(db.Integer)

class ConfigBool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=True, unique=True)
    value = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(256), nullable=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=True, unique=True)
    message = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(256), nullable=True)
    category = db.Column(db.String(64), nullable=True)


# Scan the shared directory and add subdirectories to the DB
with app.app_context():
    db.create_all()

    for directory in os.listdir(SHARED_DIRECTORY):
        if os.path.isdir(directory):
            if not Directory.query.filter(Directory.path == directory).first():
                db.session.add(Directory(directory))
    

    # Initialize some default settings
    if not ConfigBool.query.filter(ConfigBool.name == 'allow_multiple_uploads').first():
        db.session.add(ConfigBool(
            name = "allow_multiple_uploads",
            value = app.config.get('ALLOW_MULTIPLE_UPLOADS', False),
            description = "Allow multiple user uploads to the same directory. Replaces existing files."
        ))
        print(app.config.get('ALLOW_MULTIPLE_UPLOADS', False))

    if not Message.query.filter(Message.name == 'default_message').first():
        db.session.add(Message(
            name = "default_message",
            message = '',
            description = "Default message, visible to all users.",
            category='info'
        ))

    db.session.commit()


# Command line output
bcolors = {
    "HEADER": '\033[95m',
    "OKBLUE": '\033[94m',
    "OKCYAN": '\033[96m',
    "OKGREEN": '\033[92m',
    "WARNING": '\033[93m',
    "FAIL": '\033[91m',
    "ENDC": '\033[0m',
    "BOLD": '\033[1m',
    "UNDERLINE": '\033[4m',
}
print()
print(f'{bcolors["OKGREEN"]}File sever running at: '+\
      f'{bcolors["OKBLUE"]}{socket.gethostbyname(socket.gethostname())}:5000{bcolors["ENDC"]}{bcolors["ENDC"]}')
print()



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

# User identification decorator
def id_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client = Client.query.filter(Client.address==request.remote_addr).first()
        print('client: ', client)
        if client is None:
            flash('No user ID set.', 'warning')
            return redirect(url_for('identify'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin = check_admin(request)
        if not admin:
            message = 'Admin access required. Redirecting to index...'
            flash(message, 'danger')
            print(message)
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

# Context processor to inject client id, admin status and messages into templates
@app.context_processor
def inject_client():
    context = {}
    context['admin'] = check_admin(request)
    
    client = Client.query.filter(Client.address==request.remote_addr).first()
    context['client'] = client
    if client is not None:
        client.active = True
        client.last_seen = datetime.datetime.now()
        db.session.commit()

    messages = Message.query.all()
    context['permanent_messages'] = messages
    return context

# Views
@app.route("/id", methods=["GET", "POST"])
def identify():
    """
    View to identify the user on first access.
    """
    # Client database query
    client = Client.query.filter(Client.address==request.remote_addr).first()
    if client is not None:
        return redirect('/')
    
    if request.method == 'POST':
        id = request.form.get('id')
        if id:
            client = Client(request.remote_addr)
            client.selected_name = id
            db.session.add(client)
            db.session.commit()
            return redirect('/')
        else:
            flash('Prosim vpišite vpisno številko.', 'error')
            return redirect('/')
    return render_template('identify.html')

@app.route("/", methods=["GET", "POST"])
def list_dirs():
    """
    View to list directories on the server.
    """
    #not_shared_dirs = available_dirs(0)
    read_only_dirs = available_dirs(1)
    upload_only_dirs = available_dirs(2)
    
    return render_template(
        'list_dirs.html',
        read_only_dirs=read_only_dirs, 
        upload_only_dirs=upload_only_dirs
        )


@app.route("/download/<path>")
@id_required
def download(path):
    """
    Download read_only directory.
    Package the directory as a zip file and serves it.
    """
    if not os.path.isdir(os.path.join(SHARED_DIRECTORY, path)):
        print(path, ' not a directory')
        flash(f'{path} is not a shared directory.', 'warning')
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
            print(f'generating zip file {zip_file}...')
            with zipfile.ZipFile(zip_file, 'w') as zipf:
                for root, dirs, files in os.walk(os.path.join(SHARED_DIRECTORY, path)):
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, os.path.join(SHARED_DIRECTORY, path))                                
                        zipf.write(file_path, relative_path)

        # Record download
        client = Client.query.filter(Client.address==request.remote_addr).first()
        download = Download(client_id=client.id, directory_id=Directory.query.filter(Directory.path==path).first().id)
        download.download_time = datetime.datetime.now()
        db.session.add(download)
        db.session.commit()

        return send_file(zip_file, as_attachment=True)



@app.route("/upload/<path>", methods=["GET", "POST"])
@id_required
def upload_dir(path):
    """
    Select a file to upload to the selected (`path`) directory
    on the server.
    """
    if request.method == 'POST':
        target_path = os.path.join(SHARED_DIRECTORY, path)
        client = Client.query.filter(Client.address==request.remote_addr).first()
        upload_name = client.selected_name
        allow_multiple = ConfigBool.query.filter(ConfigBool.name=='allow_multiple_uploads').first().value

        target_path = os.path.join(target_path, upload_name.strip())
        uploaded_files = request.files.getlist('file') 

        if len(uploaded_files) > app.config['MAX_FILES']:
            flash(f'Preveč datotek. Največ {app.config["MAX_FILES"]} neenkrat.', 'warning')
            return redirect(url_for('upload_dir', path=path))
        
        if os.path.exists(target_path):
            if not allow_multiple:
                flash(f'Datotke z istim imenom že obstajajo.', 'warning')
                return redirect(url_for('upload_dir', path=path))
            else:
                flash(f'Datotke z istim imenom že obstajajo. Obstoječe bodo prepisane.', 'warning')
        
        for file in uploaded_files:
            if file:
                dirname = os.path.dirname(file.filename)
                save_dir = os.path.join(target_path, dirname)
                filename = os.path.basename(file.filename)
                # Handle nested subdirectories
                file_path = os.path.join(save_dir, filename)
                os.makedirs(save_dir, exist_ok=True)
                file.save(file_path)

        # Record upload
        client = Client.query.filter(Client.address==request.remote_addr).first()
        upload = Upload(client_id=client.id, directory_id=Directory.query.filter(Directory.path==path).first().id)
        upload.upload_time = datetime.datetime.now()
        upload.files_count = len(uploaded_files)
        db.session.add(upload)
        db.session.commit()

        flash(f'{len(uploaded_files)} datotek uspešno naloženih.', 'success')
        return redirect(url_for('upload_dir', path=path))

        
    return render_template('upload.html', path=path)


@app.route("/copy_config")
@admin_required
def copy_config():
    if check_admin(request):
        config_copy_keys = [
            'DEBUG', 'SECRET_KEY', 'WTF_CSRF_ENABLED', 'SQLALCHEMY_DATABASE_URI', 
            'REFRESH_TIME', 'SHARE_MODES', 'EXCLUDE_DIRNAMES', 'MAX_FILES'
        ]
        config_items = [(k, app.config[k]) for k in config_copy_keys if k in app.config.keys()]
        with open(local_config, 'w') as f:
            json.dump(dict(config_items), f, indent=2)
        return redirect(url_for('admin_view'))
    else:
        return redirect(url_for('list_dirs'))


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_view():
    # Admin check and management forms
    context = {}
    # Populate shared dir management forms
    manage_dirs = [dir for dir in Directory.query.all() if dir.path in os.listdir(SHARED_DIRECTORY)]
    context['manage_dirs'] = manage_dirs

    # Populate `messages`
    message = Message.query.filter(Message.name=='default_message').first()
    context['default_message'] = message

    # Populate `configs`
    configs = ConfigBool.query.all()
    context['configs'] = configs

    # Validate and update share mode
    if request.method == 'POST':
        messages = {}
        for name, value in request.form.items():
            
            # handle dir modes
            if name in [str(d.id) for d in Directory.query.all()]:
                if value in [str(k) for k in app.config["SHARE_MODES"].keys()]:
                    dir = Directory.query.filter(Directory.id == int(name)).first()
                    dir.mode = int(value)
                    db.session.commit()

            # handle messages and configs
            elif name == 'default_message':
                message.message = value
                db.session.commit()
                print(f'Setting {message.name} to "{value}".')

            elif 'config' in name:
                config_id = int(name.split('_')[-1])
                config_value = bool(int(value))
                config = ConfigBool.query.filter(ConfigBool.id==config_id).first()
                config.value = config_value
                db.session.commit()
                print(f'setting {config.name} to {config_value}')

        return redirect(url_for('admin_view'))
    
    return render_template(
        'admin.html',
        share_modes=app.config["SHARE_MODES"],
        exclude_dirnames=app.config["EXCLUDE_DIRNAMES"],
        **context
        )


@app.route("/manage_session")
@admin_required
def manage_session():
    """
    View to manage the current session.
    """
    if check_admin(request):
        clients = Client.query.all()
        downloads = Download.query.all()
        uploads = Upload.query.all()

        # ping client to update last_seen
        for client in clients:
            response = ping(client.address, count=1, timeout=0.1)
            if response.success():
                client.last_seen = datetime.datetime.now()
                client.active = True
            elif (datetime.datetime.now() - client.last_seen).total_seconds() > 15:
                client.active = False
            db.session.commit()

        return render_template('manage_session.html',
                               clients=clients, downloads=downloads, uploads=uploads)
    else:
        return redirect(url_for('list_dirs'))


@app.route("/reset_session")
@admin_required
def reset_session():
    """
    Resets the current session by deleting the list of clients,
    uploads and downlooads.
    """
    print('reset_session, admin: ', check_admin(request))
    if check_admin(request):
        nd_client = Client.query.delete()
        nd_download = Download.query.delete()
        nd_upload = Upload.query.delete()
        db.session.commit()
        flash(f'Session reset. Deleted {nd_client} client, {nd_download} download and {nd_upload} upload records.', 'success')
        return redirect(url_for('manage_session'))
    else:
        return redirect(url_for('manage_session'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, host='0.0.0.0')