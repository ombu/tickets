## Running

## Obtaining a database dump from production

    fab prod_db_dump

This will save a databse dump in the `dbdumps` directory, such as
`dbdumps/tickets-20150208.sql.gz`.

### Using a local Ruby

Run Redmine locally ideally using the same Ruby version as the production
server. You'll need the Redmine database loaded and accessible with the
development credentials in `private/database.yml`.

Checkout repository submodules:

    git submodule update --init --recursive

Use a Ruby environment already configured with the Redmine dependencies:

    rvm use ruby-1.9.3@tickets

Or, setup an RVM environment:

    rvm install ruby-1.9.3
    rvm use ruby-1.9.3
    rvm gemset create tickets
    gem install bundler
    cd redmine
    bundle install

Run Redmine:

    export RAILS_ENV=development
    rake generate_secret_token tmp:cache:clear tmp:sessions:clear
    rake db:migrate redmine:plugins:migrate
    rails server

### Deploy to a Vagrant box

Obtain a Vagrant with the same Linux distribution as the production server,
such as [Ubuntu's](https://cloud-images.ubuntu.com/vagrant/trusty/current/)
and declare it in Vagrantfile `config.vm.box`.

Bring up the Vagrant VM:

    vagrant up

Configure your local DNS so you can ssh into the Vagrant VM with
`ssh tickets.local`.

Load a Redmine database into the VM accessible with the credentials in the
fabfile's `vagrant` task. There are tasks in the fabfile to help with this:

    fab prod_db_dump

This will create a current dump, for example
`dbdumps/tickets-20150208.sql.gz`. Load it to the Vagrant VM with:

    fab load_db_dump_to_vagrant:tickets-20150208.sql.gz

Prepare the server for Redmine, and deploy a Git refspec:

    fab vagrant setup_env
    fab vagrant deploy:origin/feature/2.6

### Deploy to AWS

Provision an instance with OMBU Puppet manifest `tickets.pp`. Load a database
dump into the remote database server. Configure a host task for the instance
in `fabfile.py`.

    fab instance setup_env
    fab instance deploy:origin/feature/2.6

#### Update the staging environment (lame method)

- Manually rsync `/home/ombu/redmine-uploads/` and
  `/home/ombu/redmine-uploads-stage/`

        mysqldump -u root -p tickets > tickets.sql
        mysql -u root -p -D tickets-stage < tickets.sql

## Installing a new plugin

    git submodule add git://github.com/edavis10/redmine-timesheet-plugin.git plugins/timesheet
    git commit -m '' && git push
    fab staging deploy:96c048c088663b04480b35329136c002a7e7c525

## Upgrading Redmine

For example, to upgrade to a new repository tag 2.6.1:

    cd redmine && git fetch && git fetch --tags
    git checkout 2.6.1
    bundle update
    rake db:migrate redmine:plugins:migrate
    cd .. && git add redmine
