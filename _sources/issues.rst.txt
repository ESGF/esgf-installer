ESGF Installer Issue Tracking Guidelines
******************************************
We are going to begin to use Github Issues as a well to provide easier and better tracking of issues that occur during development of ESGF.
Here are some general guidelines for reporting issues.

Labeling
===================

Github Issues has a label feature that can be used to categorize issues.
The general guidelines for labeling an issue is to add a label that lists the version in which the issue was first discovered and a label listing the component in which the issue occurs/affects.
It is possible than an issue affects more than one component, so please add labels for all associated components.

Closing Issues
===================
Once an issue has been resolved in the codebase, the issue should be closed to avoid duplicated work.
It is a best practice to add the issue number to the commit message when committing the solution code to the repository.
For example, when committing code to solve issue #3 the commit message can look similar to this:

``Added new awesome feature; fixes #3``

That will cause the commit to be linked to the issue.

Alternatively, the short hash of the commit that fixed the issue can be added as a comment in order to link the solution with the problem statement.
