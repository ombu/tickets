## Update the staging environment

   fab sync:src=production,dst=staging

## Installing a new plugin

    git submodule add git://github.com/edavis10/redmine-timesheet-plugin.git plugins/timesheet
    git commit -m '' && git push
    fab staging deploy:96c048c088663b04480b35329136c002a7e7c525
