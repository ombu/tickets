from fabric.api import task, env, run, abort, sudo, cd, execute, prompt, \
    shell_env, local
from fabric.contrib import console, files
from datetime import date

PROD_DB_PW = 'SETME'
SMTP_PW = 'SETME'
SMTP_PW = 'SETME'

PROD_DB_HOST = 'ombudb.cpuj5trym3at.us-west-2.rds.amazonaws.com'
PROD_DB_HOST2 = 'proddb1.ombudev.com'
VAGRANT_DB_PW = 'meh'

env.use_ssh_config = True
env.forward_agent = True
env.repo = 'git@github.com:ombu/tickets.git'
env.gem_home = '/home/axolx/.gem'
env.uploads_path = '/mnt/tickets/uploads'
env.db_db = 'tickets'
env.db_user = 'tickets'
env.smtp_host = 'email-smtp.us-east-1.amazonaws.com'
env.smtp_user = 'AKIAI7LZAOFJ5MKLR5BQ'
env.smtp_pw = SMTP_PW


# Host settings
@task
def vagrant():
    """
    The local (Vagrant) server definition
    """
    env.hosts = ['tickets.local']
    env.environ = 'development'
    env.url = 'tickets.local'
    env.app_path = '/var/www/tickets.local'
    env.db_host = 'localhost'
    env.db_pw = VAGRANT_DB_PW


@task
def production():
    """
    The production server definition
    """
    env.hosts = ['54.185.183.93']
    env.environ = 'production'
    env.url = 'tickets.ombuweb.com'
    env.app_path = '/var/www/tickets.ombuweb.com'
    env.db_host = PROD_DB_HOST
    env.db_pw = PROD_DB_PW


@task
def production_vpc():
    """
    The production server definition
    """
    env.hosts = ['52.10.14.7']
    env.environ = 'production'
    env.url = 'tickets.ombuweb.com'
    env.app_path = '/var/www/tickets.ombuweb.com'
    env.db_host = PROD_DB_HOST2
    env.db_pw = PROD_DB_PW


@task
def setup_env():
    setup_env_dir()
    setup_env_vhost()


def setup_env_dir():
    if files.exists(env.app_path):
        if console.confirm("Found %s. Replace it?" % env.app_path,
                           default=False):
            run('rm -rf %s' % env.app_path)
        else:
            abort('Quitting')
    run('mkdir -p %s' % env.app_path)
    run('cd %(app_path)s && chgrp www-data %(app_path)s && chmod g+s %('
        'app_path)s' % env)
    run('cd %(app_path)s && mkdir log private' % env)

    with shell_env(GEM_HOME=env.gem_home):
        run('gem install bundler')

    print('Site directory structure created at: %(app_path)s' % env)


def setup_env_vhost():
    files.upload_template(
        'private/apache_vhost', env.app_path + '/private/' + env.url, env)
    sudo(
        'ln -fs %(app_path)s/private/%(url)s '
        '/etc/apache2/sites-available/%(url)s.conf' % env)
    sudo('a2ensite %s.conf' % env.url)


@task
def deploy(refspec):
    """ A Git refspec such as a commit code or branch. Branches names need
    to start with `origin/` (e.g. origin/1.x instead of 1.x). """
    p = env.app_path
    if not files.exists(p + '/repo'):
        run('cd %s && git clone -q %s repo' % (p, env.repo))   # clone
    else:
        run('cd %s/repo && git fetch' % p)                  # or fetch
    with(cd(p)):
        refspec = run('cd %s/repo && git rev-parse %s' % (p, refspec))
        run('cd repo && git reset --hard %s && git submodule -q update '
            % refspec + '--init --recursive')
        run('rm -rf current')
        run('cp -r repo/redmine current')
    files.upload_template('private/database.yml', p +
                          '/current/config/database.yml', env)
    files.upload_template('private/configuration.yml', p +
                          '/current/config/configuration.yml', env)

    with shell_env(GEM_HOME=env.gem_home, RAILS_ENV='production'):
        with(cd(p + '/current')):
            execute(install_plugins)
            env.bundle_bin = "%s/bin/bundle" % env.gem_home
            run('%(bundle_bin)s install --path %(gem_home)s '
                '--without="development test"' % env)
            run('%(bundle_bin)s exec rake db:migrate' % env)
            run('%(bundle_bin)s exec rake redmine:plugins:migrate' %
                env)
            run('%(bundle_bin)s exec rake tmp:cache:clear' % env)
            run('%(bundle_bin)s exec rake tmp:sessions:clear' % env)
            run('%(bundle_bin)s exec rake generate_secret_token' % env)

    run('sudo /etc/init.d/apache2 restart')


@task
def uninstall():
    doit = prompt(
        "This operation can lead to data loss. Are you sure "
        "you want delete the tickets app on %s?" % env.environ)
    if not doit == 'y':
        abort('Sync aborted')
    sudo('if [ -d %(app_path)s ]; then rm -rf %(app_path)s; fi' % env)
    sudo('if [ -d %(gem_home)s ]; then rm -rf %(gem_home)s; fi' % env)
    sudo(
        'if [ -h /etc/apache2/sites-enabled/%(url)s.conf ]; then unlink '
        '/etc/apache2/sites-enabled/%(url)s.conf; fi' % env)
    sudo(
        'if [ -h /etc/apache2/sites-available/%(url)s.conf ]; then unlink '
        '/etc/apache2/sites-available/%(url)s.conf; fi' % env)
    run('sudo /etc/init.d/apache2 restart')


@task
def install_plugins():
    """ Install plugins in plugins/* """
    with(cd(env.app_path)):
        run("""
        for plugin in `ls repo/plugins`
        do
            if [ -d current/plugins/$plugin ]; then
                rm -rf current/plugins/$plugin
            fi
        done""")
        run('cp -r repo/plugins/* current/plugins')


@task
def add_repo(name):
    """ Add a repo to the server """
    path = '/mnt/repos/' + name
    if files.exists(path):
        abort('Repo path exists: ' + path)
    else:
        run('git clone -q --bare git@bitbucket.org:ombu/%s.git %s' % (name,
                                                                      path))
        with(cd(env.app_path + '/current')):
            run('ruby script/runner "Repository.fetch_changesets" -e '
                'production')


@task
def prod_db_dump():
    """ Download a dump of the tickets production database
    """
    today = date.today().strftime('%Y%m%d')
    dump_name = "dbdumps/tickets-%s.sql.gz" % today
    local("mkdir -p dbdumps")
    print("Dumping tickets DB to: " + dump_name)
    local(
        'ssh tickets.ombuweb.com mysqldump -h%s -utickets '
        '-p%s tickets | gzip -c > %s' % (PROD_DB_HOST, PROD_DB_PW,  dump_name))


@task
def load_db_dump_to_vagrant(dump_name):
    """ Load a dump previously created with `prod_db_dump` into a running
    Vagrant VM.
    """
    print("Loading DB dump to Vagrant: " + dump_name)
    local(
        """echo "grant all on tickets.* to tickets@localhost identified \
    by '%s'; create database tickets;" | ssh tickets.local mysql -uroot """ %
        VAGRANT_DB_PW)
    local(
        'gunzip -c dbdumps/%s '
        '| ssh tickets.local mysql -utickets -Dtickets -p%s'
        % (dump_name, VAGRANT_DB_PW))
