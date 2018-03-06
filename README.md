# rapid-response-xblock
A django app plugin for edx-platform

## Database Migrations

If you make any model changes in this project, new migrations can 
be created as follows:

- Run `edx-platform` with this package listed as a requirement. One
   way to do this is to mount this repo directory to devstack and in
   `/requirements/private.txt` add that path:
   ``` 
   -e /path/to/rapid-response-xblock
   ```
- Run the `makemigrations` Django management command within devstack:
   ```
   python manage.py lms makemigrations rapid_response_xblock --settings=devstack_docker
   ```
   If your `rapid-response-xblock` repo is mounted to the devstack container,
   you'll see the migrations directory and files added to your local repo, ready
   to be added and committed in Git.
