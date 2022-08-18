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

# Usage

## Authorization

__\*\*\*Authorization must be done before any of the bot functions can be used.\*\*\*__

- Authorize 3rd party Twitter app with internal server interface first (the "AUTHORIZE NEW CLIENT" button). Only needs to be done once per client.								
- The Twitter authorization link provided can be sent to the client, but the client must give you the resulting PIN number so that you can enter it into the interface.								
								
								
## Automated Messaging: Scripts and Blocklist

- Set the Twitter handle, set all the filters (must be integer values of 0 or greater) and add the block list to the Blocklist tab BEFORE starting the job in Scripts tab								
- Set Job to 'start', all lower case, to start the job.								
- Set Job to 'reset', all lower case, to delete all followers to allow messages to be sent to followers again with new script.								
- Set Job to 'ignore' to ignore the account entirely. Use to stay within Twitter API rate limits.								
- Anything other than the two keywords above under Job column will stop the running jobs for that Twitter handle.								
- Every row in Scripts represents a single Twitter client account. 								
- Every column in Blocklist also represents one account and the header of the column MUST be the client Twitter handle.								
								
## Call to Action Buttons

- CTA or Call to Action buttons will be sent with messages if filled in the "CTA # Label" and "CTA # Url" columns.								
- CTA labels have a max string length of 36 characters. Both a label and a URL must be present for the CTA to be sent with the message.								

# Access Points

Where `host` represents the IP/domain of the server:

- MongoDB: http://host:27017
  - All relevant data should be contained in the `twitter` collection.
- Server test: http://host:5000
  - Should show `"OK"` if server is active.
