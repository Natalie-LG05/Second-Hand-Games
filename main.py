from SHG_Code_Stuffs import create_app

app = create_app()

if __name__ == '__main__':
    """debug=True: automatically reruns web server when changes are made"""
    app.run(debug=True)