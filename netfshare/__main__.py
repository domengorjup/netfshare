from .netfshare import app, netfshare, socketio

# Register netfshare views blueprint
app.register_blueprint(netfshare)
port = int(app.config.get("PORT", 5000))

socketio.run(app, port=port, host="0.0.0.0")

print()
