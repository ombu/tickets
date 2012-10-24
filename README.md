## Update the staging environment (lame method)

- Manually rsync `/home/ombu/redmine-uploads/` and
  `/home/ombu/redmine-uploads-stage/`

        mysqldump -u root -p tickets > tickets.sql
        mysql -u root -p -D tickets-stage < tickets.sql

## Installing a new plugin

    git submodule add git://github.com/edavis10/redmine-timesheet-plugin.git plugins/timesheet
    git commit -m '' && git push
    fab staging deploy:96c048c088663b04480b35329136c002a7e7c525

## Upgrade to a new version of Redmine

    cd redmine && git fetch && git fetch --tags
    git checkout 1.4.4
    cd .. && git add redmine
