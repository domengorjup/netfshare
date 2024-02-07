import os
import time
import zipfile

from flask import Flask, request, redirect, url_for, send_file, render_template
from flask_sqlalchemy import SQLAlchemy

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


SHARED_DIRECTORY = os.getcwd()
app = Flask(__name__)
app.config.from_object('config')

db_path = os.path.join(SHARED_DIRECTORY, '.netfshare', 'dir_config.db')
print(os.path.dirname(db_path))
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

db = SQLAlchemy(app)

share_modes = {
    0: 'Not shared',
    1: 'Read only',
    2: 'Upload_only'
}

exclude_dirnames = ['.git', '.netfshare', '__pycache__']

# Directory DB model
class Directory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.Integer, default=0)
    path = db.Column(db.String(64), nullable=True)

    def __init__(self, path):
        self.path = path
        self.mode = 0

    def __repr__(self):
        return f'Directory: {self.path} (share mode {self.mode} - {share_modes[self.mode]})'

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
    all_dirs = [dir for dir in os.listdir(SHARED_DIRECTORY) if os.path.basename(dir) not in exclude_dirnames]
    matching_mode_paths = [dir.path for dir in Directory.query.filter(Directory.mode==mode).all()]
    return [_ for _ in all_dirs if _ in matching_mode_paths]


def check_admin(request):
    is_admin = False
    if (request.remote_addr) in str(request.host):
        is_admin = True
    return is_admin


# Forms
class UploadForm(FlaskForm):
    file = FileField('File', validators=[FileRequired()])
    name = StringField('Name', validators=[DataRequired()])
    submit = SubmitField('Upload')

# Views
@app.route("/", methods=["GET", "POST"])
def list_dirs():
    """
    View to list directories on the server.
    """
    #not_shared_dirs = available_dirs(0)
    read_only_dirs = available_dirs(1)
    upload_only_dirs = available_dirs(2)
    print(upload_only_dirs)

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
                    if value in [str(k) for k in share_modes.keys()]:
                        dir = Directory.query.filter(Directory.id == int(id)).first()
                        dir.mode = int(value)
                        db.session.commit()
            return redirect(url_for('list_dirs'))
            
    else:
        print('not admin')
    
    return render_template(
        'list_dirs.html', 
        read_only_dirs=read_only_dirs, 
        upload_only_dirs=upload_only_dirs, 
        share_modes = share_modes,
        **context
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
    TODO: Add a form to select the directory to upload to
    TODO: ecerything else
    """
    form = UploadForm()
    if form.validate_on_submit():
        file = form.file
        name = form.name
        file.save(os.path.join(SHARED_DIRECTORY, path, name, form.name.data))
    return render_template('upload.html', form=form, path=path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, host='0.0.0.0')