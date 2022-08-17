# Installation and Setup

- Install Docker Compose and related requirements
   - Debian/Ubuntu: https://docs.docker.com/desktop/install/ubuntu/  
   https://www.digitalocean.com/community/tutorial_collections/how-to-install-docker-compose
  - MacOS: https://docs.docker.com/desktop/install/mac-install/  
  https://docs.docker.com/desktop/install/mac-install/
  - Windows: Not recommended :)
- Ensure docker service is running using `systemctl --user start docker-desktop` (for Ubuntu).
- Run `docker-compose up -d` from within the main directory (should contain the file `docker-compose.yaml`) to run package installation and host server
  - Check container status using `docker ps`. It should should show 2 containers, one for MongoDB and one for the Flask app (that contains the bot code).
- Take down the containers using `docker-compose down` .

# Access Points

Where `host` represents the IP/domain of the server:

- MongoDB: http://host:27017
  - All relevant data should be contained in the `twitter` collection.
- Server test: http://host:5000
  - Should show `"OK"` if server is active.
