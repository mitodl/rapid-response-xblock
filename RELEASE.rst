Release Notes
=============

Version 0.8.0
-------------

- docs: Update readme with reports plugin info (nutmeg) (#127)
- fix: update broken test settings and fix warnings (#126)

Version 0.7.0 (Released May 02, 2022)
-------------

- Fixes: Page scrolls when closing rapid response problem (#123)

Version 0.6.0 (Released November 10, 2021)
-------------

- Added studio and XML doc references (#113)

Version 0.5.1 (Released November 10, 2021)
-------------

- Update instructions (#117)
- chore: add support for Django3.2 (#111)
- fix: Open/Close button anchor & design regression in Learning MFE (#114)

Version 0.5.0 (Released June 15, 2021)
-------------

- Using codecov in github actions (#106)

Version 0.4.0 (Released June 14, 2021)
-------------

- Added tests for logger.py (#105)

Version 0.3.0 (Released May 03, 2021)
-------------

- Lilac Compatibility: Fixing issues with tests (#101)

Version 0.2.0 (Released April 22, 2021)
-------------

- Upgrade django with a package range (#99)

Version 0.1.0 (Released April 21, 2021)
-------------

- Fixed index out of bound error in case of no submittion data (#93)
- Updated readme to include usage details

Version 0.0.9 (Released January 14, 2021)
-------------

- Update rapid_response_xblock/utils.py
- Added support for updated data structure in rapid response submissions
- Added setup step to README that was accidentally omitted
- Updated installation & testing instructions
- Switch from Travis to Github Actions

Version 0.0.8 (Released December 24, 2020)
-------------

- edX Koa release compatibility

Version 0.0.5 (Released December 11, 2018)
-------------

- Applied MathJax to graph and tooltip, and fixed int test script
- util methods added in xblock to serve instructor dashboard

Version 0.0.2 (Released May 01, 2018)
-------------

- Link y domains together, use the greatest max value (#60)
- Show a tooltip when the mouse hovers over a bar (#57)
- Show number of students while problem is open (#54)
- Fix handling of multiple runs which are open (#56)
- Add timer (#51)
- First round of style tweaks (#53)
- Add comparison view for graphs (#46)
- Add dashed horizontal lines (#49)
- Use custom color palette (#50)
- Limited rapid response block to multiple choice problems
- Updated Django dependency range
- Add database models to store runs (#37)
- Pass histogram from the backend and order by answer order (#35)
- Added studio view so instructors can enable/disable a problem for rapid response
- Rename fields (#28)
- Fix use of _.pluck (#30)
- Add graph of responses (#23)
- Add REST API for responses (#19)
- Removed base class from aside
- Added instructor view to open/close a rapid-response-enabled problem
- Run pylint and pep8 outside pytest (#22)
- Store responses to problems (#6)
- Add a logger to handle events (#5)
- Rename repository and package (#7)
- Add skeleton (#4)

