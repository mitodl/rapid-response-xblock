⛔️ DEPRECATION WARNING
======================
This repository is deprecated. Please see [open-edx-plugins](https://github.com/mitodl/open-edx-plugins) for all the future updates and development.
-------------------------------------------------------------------------------------------------------------------------------------------------------


# rapid-response-xblock
A django app plugin for edx-platform

## Setup

### 1) Add rapid response as a dependency

In production, the current practice as of 01/2021 is to add this dependency via Salt.

For local development, you can use one of the following options to add this as a dependency in the `edx-platform` repo:

- **Install directly via pip.**

    ```
    # From the devstack directory, run bash in a running LMS container...
    make dev.shell.lms
    
    # In bash, install the package
    source /edx/app/edxapp/edxapp_env && pip install rapid-response-xblock==<version>

    # Do the same for studio
    make dev.shell.studio
    
    # In bash, install the package
    source /edx/app/edxapp/edxapp_env && pip install rapid-response-xblock==<version>
    ``` 
   
   To install a version of rapid-response-xblock which is not on pypi, you can clone this repo into the two containers. Install the package by running `source /edx/app/edxapp/edxapp_env && python setup.py install` for LMS and Studio.


- **Add to one of the requirements files (`requirements/private.txt` et. al.), then re-provision with `make dev.provision.lms`.** This is very heavyweight
  as it will go through many extra provisioning steps, but it may be the most reliable way.
- **Use ODL Devstack Tools.** [odl_devstack_tools](https://github.com/mitodl/odl_devstack_tools) was created to 
  alleviate some of the pain that can be experienced while running devstack with extra dependencies and config changes.
  If you set a few environment variables and create a docker compose file and config patch file, you can run devstack
  with your rapid response repo mounted and installed, and the necessary config changes (discussed below) applied. 
- **Clone inside LMS/CMS:** Both LMS/CMS containers have a shared directory `src` which can be used to clone and install this xBlock locally. You can use this method for local development as well.
    ```
    pip install -e /edx/src/rapid-response-xblock
    ```

### 2) Update EdX config files 

As mentioned above, [odl_devstack_tools](https://github.com/mitodl/odl_devstack_tools) can be used to automatically
apply the necessary config changes when you start the containers. If you're not using that tool, you can manually 
    add/edit the relevant config files while running bash in the LMS container (`make dev.shell.lms`):

#### Juniper release or more recent

If you're using any release from Juniper onward, make sure the following property exists with the given value
in `/edx/etc/lms.yml` and `/edx/etc/studio.yml`:

```yaml
- ALLOW_ALL_ADVANCED_COMPONENTS: true
```

#### Any release before Juniper

If you're using any release before Juniper, make sure the following properties exist with the given values in
`/edx/app/edxapp/lms.env.json` and `/edx/app/edxapp/cms.env.json`:

```json
{
    "ALLOW_ALL_ADVANCED_COMPONENTS": true,
    "ADDL_INSTALLED_APPS": ["rapid_response_xblock"]
}
```

`ADDL_INSTALLED_APPS` may include other items. The list just needs to have `rapid_response_xblock` among its values.

#### Feature flags

There is a feature flag to enable toggling the rapid response functionality for a problem through course outline in CMS. Enable `ENABLE_RAPID_RESPONSE_AUTHOR_VIEW` in your CMS config either through `/edx/app/edxapp/cms.env.json` or `private.py`.

```yaml
- ENABLE_RAPID_RESPONSE_AUTHOR_VIEW: true or false
```


__NOTE:__Once this flag is enabled and you toggle the rapid response from course outline, It will auto publish the problem if it was not in draft.

### 3) Add database record

If one doesn't already exist, create a record for the `XBlockAsidesConfig` model 
(LMS admin URL: `/admin/lms_xblock/xblockasidesconfig/`).

If you have enabled `ENABLE_RAPID_RESPONSE_AUTHOR_VIEW` you will also need to create a record in the `StudioConfig` model 
(CMS admin URL: `/admin/xblock_config/studioconfig/`).

### 4) Rapid Response for Studio and XML
[Studio Documentation](https://odl.zendesk.com/hc/en-us/articles/360007744011-Rapid-Response-for-Studio)
[XML Documentation](https://odl.zendesk.com/hc/en-us/articles/360007744151-Rapid-Response-for-XML)

## Database Migrations

If your `rapid-response-xblock` repo is mounted into the devstack container, you can create migrations for any
model changes as follows:

```
# From the devstack directory, run bash in a running LMS container...
make dev.shell.lms

# In bash, create the migrations via management command...
python manage.py lms makemigrations rapid_response_xblock --settings=devstack_docker
```

## Usage

_NOTE (4/2021)_: Rapid response is **only configured to work with multiple choice problems**.

Follow these steps to enable an individual problem for rapid response:
1. Load the problem in Studio
2. Click "Edit"
3. In the editing dialog UI there should be Editor, Settings, and Plugins in the title bar. Click "Plugins". (If this option doesn't exist, rapid response may not be properly configured)
4. Check the box ("Enable problem for rapid-response")
5. Save and publish

When you navigate to that problem in LMS, you should now see an option for opening the problem for rapid response.

To test rapid response functionality:
1. Login to your local edX instance as "staff"
2. In Studio go to the edX Demo Course. Create a new unit which is a multiple choice problem.
3. Edit the problem and turn on rapid response as described in the previous steps.
4. Publish and click "View Live Version"
5. Verify that the dropdown next to "View this course as" is "Staff". 
6. Scroll down and you should see an empty graph containing a button labeled "Open problem now". Click on the button and it should show a timer that starts counting.
7. Pick one of the answers and submit it. After a few seconds a bar should appear for the column for the answer.
8. Pick another answer, and the bar should disappear and a new one should appear at the new answer.
9. Click "Close problem now"
10. Click the dropdown next to "View this course as" to switch to "Audit". You should see a multiple choice question with two incorrect answers and one correct answer according to the labels. You should **not** see the rapid response functionality beneath the problem.


## Rapid Response Reports

All the results of the Rapid Response problems are also available in form of CSV reports as a separate plugin [ol-openedx-rapid-response-reports](https://github.com/mitodl/open-edx-plugins/tree/main/src/ol_openedx_rapid_response_reports). (_Installation instructions are on the given link_).

**How/Where to check reports?**

After you've installed [ol-openedx-rapid-response-reports](https://github.com/mitodl/open-edx-plugins/tree/main/src/ol_openedx_rapid_response_reports), visit `Rapid Responses` under the `Instructor Dashboard`. If you don't see `Rapid Responses` tab, please check that the plugins is installed properly.
![Screenshot of Rapid Response reports](docs/rapid_response_reports.png)


__NOTE:__ Rapid Response xBlock works independently and doesn't depend on `ol-openedx-rapid-response-reports`, there are no additional steps to be performed inside Rapid Response xBlock if you want to use the reports plugin.

