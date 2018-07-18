# rapid-response-xblock
A django app plugin for edx-platform

## Setup

NOTE: We had to make several fixes to XBlock Asides in `edx-platform` in order to get rapid response working. The `edx-platform` branch/tag you're using must include these commits for rapid response to work:
- https://github.com/mitodl/edx-platform/commit/b26db017a55140bb7940c3fbfac5b4f27128bffd
- https://github.com/mitodl/edx-platform/commit/96578f832d786d90162c555f1cfa08f69ba294d2
- https://github.com/mitodl/edx-platform/commit/1bd36be3b31210faa8af09fc28ff4a885807e20e

The following setup steps are also needed to enable rapid response problems in LMS and Studio:
1. Add the following to at the top level of `cms.env.json`: `ALLOW_ALL_ADVANCED_COMPONENTS: true`
1. Make sure `cms.env.json` and `lms.env.json` include this XBlock as an installed app: `ADDL_INSTALLED_APPS: ['rapid_response_xblock']`
1. Create a record for the `XBlockAsidesConfig` model (LMS admin URL: `/admin/lms_xblock/xblockasidesconfig/`)

After these steps, you should be able to see an extra tab in the 'Edit' modal for multiple choice problems in Studio. That extra tab should contain a checkbox that lets you configure the problem as rapid response.

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
