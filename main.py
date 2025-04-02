from SHG_Code_Stuffs import web_creation

app = web_creation()

if __name__ == '__main__':
    """debug=True: automatically reruns web server when changes are made"""
    app.run(debug=True)