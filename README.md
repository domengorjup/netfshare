# netfshare

A flask-based local network file sharing tool.

**Not for production environements. Use with care.**

## Installation and use

1. Install the `netfshare` python package:

    ```py -m pip install netfshare```

2. Navigate to the directory that you want to share the contents of. Run `netfshare` to start the sharing service:
   
   ```py -m netfshare```

The service cam+n be accessd at `<your-local-ip>:5000`. 

Make sure your machine is discoverable in the local network and that the required firewall rules are active.

## Sharing settings

Visit the service website Admin interface from the machine running the service to manage the sharing settings.

`netfshare` supports downloading the contents (subdirectories) of your shared folder, as well as uploading clients' content to selected directories inside the shared folder.

Only downloads of *whole subdirectories* are supported, as `.zip` archives. To make files available for downalod, they must be placed inside a subdirectory of the sharedfolder, and the appropriate sharing mode must be set for this subdirectory in the Admin web interface. 

Currently, the supported sharing modes are:
 - `read_only`: whole subdirectories of the shared folder can be downloaded as a `.zip` archive.
 - `upload_only`: clients can upload their data into a selected subdirectory of the shared folder. The uploaded content is placed inside a subfolder with the user's selected name. Currently, only a *single upload* by each user is allowed.

 
