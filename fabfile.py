from fabric.api import task, env, run, abort, sudo, cd, execute, prompt, \
    shell_env
from fabric.contrib import console, files

env.repo_type = 'git'
env.repo = 'git@github.com:ombu/tickets.git'
env.use_ssh_config = True
env.forward_agent = True
env.gem_home = '/home/axolx/.gem'
env.uploads_path = '/mnt/tickets/uploads'
env.db_db = 'tickets'
env.db_user = 'tickets'
env.smtp_host = 'email-smtp.us-east-1.amazonaws.com'
env.smtp_user = 'AKIAI7LZAOFJ5MKLR5BQ'
env.smtp_pw = 'SETME'

# Host settings
@task
def local():
    """
    The local (Vagrant) server definition
    """
    env.hosts = ['tickets.local:22']
    env.host_type = 'development'
    env.url = 'tickets.local'
    env.app_path = '/var/www/tickets.local'
    env.db_host = 'qadb.cpuj5trym3at.us-west-2.rds.amazonaws.com'
    env.db_pw = 'SETME'


@task
def staging():
    """
    The staging server definition
    """
    env.hosts = ['tickets.stage.ombuweb.com']
    env.host_type = 'staging'
    env.url = 'tickets.stage.ombuweb.com'
    env.app_path = '/var/www/tickets.stage'
    env.db_host = 'qadb.cpuj5trym3at.us-west-2.rds.amazonaws.com'
    env.db_pw = 'SETME'


@task
def production():
    """
    The production server definition
    """
    env.hosts = ['54.185.183.93']
    env.host_type = 'production'
    env.url = 'tickets.ombuweb.com'
    env.app_path = '/var/www/tickets.ombuweb.com'
    env.db_pw = 'SETME'


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
            execute(_install_plugins)
            run('bundle install --path %(gem_home)s '
                '--without="development test"' % env)
            run('bundle exec rake db:migrate' % env)
            run('bundle exec rake redmine:plugins:migrate' %
                env)
            run('bundle exec rake tmp:cache:clear' % env)
            run('bundle exec rake tmp:sessions:clear' % env)
            run('bundle exec rake generate_secret_token' % env)

    run('sudo /etc/init.d/apache2 restart')


@task
def uninstall():
    doit = prompt(
        "This operation can lead to data loss. Are you sure "
        "you want delete the tickets app on %s?" % env.host_type)
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


def _install_plugins():
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
