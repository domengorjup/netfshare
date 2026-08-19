# netfshare

A flask-based local network file sharing tool.

**Not for production environements. Use with care.**

## Installation and use

1. Install the `netfshare` python package:

    ```py -m pip install netfshare```

2. Navigate to the directory that you want to share the contents of. 

3. (OPTIONAL) To secure your WSGI application, set a custom `SECRET_KEY` environment variable, or create a `.env` file in the shared
   directory defining the `SECRET_KEY`:

        SECRET_KEY=my_secret_key
    
4. Run `netfshare` to start the sharing service:
   
   ```py -m netfshare```

The service can be accessed at `http://<your-local-ip>` by default.

If needed, you can override the port through configuration.

On Linux, binding to port `80` requires additional privileges. One simple option for a local development setup is to grant the virtual environment's Python interpreter permission to bind low ports:

```bash
sudo setcap 'cap_net_bind_service=+ep' "$(realpath .venv/bin/python3)"
```

If you recreate the virtual environment, run the command again.

Make sure your machine is discoverable in the local network and that the required firewall rules are active.

### Admin access

The `netfshare` app automatically recognizes a client that's accessing the app from the host (machine running the app) as admin.

If you're having issues with admin access (e.g. you're not recognized as admin despite accessing the app from your local machine), try accessing the app directl at:

```text
http://127.0.0.1
```

If you configured a custom port, append `:<port>`.

## Sharing settings

Visit the service website Admin interface from the machine running the service to manage the sharing settings.

`netfshare` supports downloading the contents (subdirectories) of your shared folder, as well as uploading clients' content to selected directories inside the shared folder.

Only downloads of *whole subdirectories* are supported, as `.zip` archives. To make files available for downalod, they must be placed inside a subdirectory of the sharedfolder, and the appropriate sharing mode must be set for this subdirectory in the Admin web interface. 

Currently, the supported sharing modes are:
 - `read_only`: whole subdirectories of the shared folder can be downloaded as a `.zip` archive.
 - `upload_only`: clients can upload their data into a selected subdirectory of the shared folder. The uploaded content is placed inside a subfolder with the user's selected name. Currently, only a *single upload* by each user is allowed.

 
## Localization

netfshare supports localization using [flask-babel]([s](https://python-babel.github.io/flask-babel/)).

The client-facing routes of the app are translated into English and Slovenian.

To update the translations after adding / modifying app text, run the following to get new text to bt translated and update the Slovenian translation file,:


    pybabel extract -F babel.cfg -o messages.pot .
    pybabel update -i messages.pot -d netfshare/translations


Now edit / add new translations in `translations/sl/LC_MESSAGES/messages.po` and compile the new translations:

    pybabel compile -d netfshare/translations

