from app import app as application

# needs to be named "application" for wsgi to pick it up
if __name__ == "__main__":
  application.run(port=5000)
