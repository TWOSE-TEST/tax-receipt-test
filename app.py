from webapp import app, configure
# from waitress import serve

if __name__ == '__main__':
    configure()
    #serve(app, host='0.0.0.0', port=8080, threads=1)
    app.run()
else:
    configure()

# Setup Docker
# https://www.digitalocean.com/community/tutorials/how-to-develop-a-docker-application-on-windows-using-wsl-visual-studio-code-and-docker-desktop
# https://www.youtube.com/watch?v=H5hs4LreRS0

# Launch Docker
# docker run -d -p 5000:5000 python-docker