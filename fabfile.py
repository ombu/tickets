from fabric.api import task, env, run, abort, sudo, cd
from fabric.contrib import console
from fabric.contrib import files
#from butter import deploy

env.repo_type = 'git'
env.repo = 'git@github.com:ombu/tickets.git'
env.use_ssh_config = True
env.forward_agent = True

# Host settings
@task
def staging():
    """
    The staging server definition
    """
    env.hosts = ['ombu@tickets:34165']
    env.host_type = 'staging'
    env.user = 'ombu'
    env.url = 'tickets.stage.ombuweb.com'
    env.host_webserver_user = 'www-data'
    env.host_site_path = '/home/ombu/redmine-stage'
    env.public_path = '/home/ombu/redmine-stage/current/public'
    env.db_db = 'tickets-stage'
    env.db_user = 'tickets-stage'
    env.db_pw = 'SETME'
    env.db_host = 'SETME'
    env.db_root_pw = 'SETME'
    env.smtp_host = 'SETME'
    env.smtp_user = 'SETME'
    env.smtp_pw = 'SETME'

@task
def production():
    """
    The production server definition
    """
    env.hosts = ['ombu@tickets:34165']
    env.host_type = 'production'
    env.user = 'ombu'
    env.url = 'tickets.ombuweb.com'
    env.host_webserver_user = 'www-data'
    env.host_site_path = '/home/ombu/redmine'
    env.public_path = '/home/ombu/redmine/current/public'
    env.db_db = 'tickets'
    env.db_user = 'tickets'
    env.db_pw = 'SETME'
    env.db_host = 'SETME'
    env.db_root_pw = 'SETME'
    env.smtp_host = 'SETME'
    env.smtp_user = 'SETME'
    env.smtp_pw = 'SETME'

@task
def setup_env():
    setup_env_dir()
    setup_env_webserver_ssl()

def setup_env_dir():
    if files.exists(env.host_site_path):
        if console.confirm("Found %s. Replace it?" % env.host_site_path, default=False):
            run('rm -rf %s' % env.host_site_path)
        else: abort('Quitting')
    run('mkdir -p %s' % env.host_site_path)
    run('cd %s && mkdir files log private' % env.host_site_path)
    print('Site directory structure created at: %s' % env.host_site_path)

def setup_env_webserver_ssl():
    files.upload_template('private/ombuweb.com.key', env.host_site_path +
            '/private/' + env.url + '.key')
    files.upload_template('private/ombuweb.com.ca.crt', env.host_site_path +
            '/private/' + env.url + '.ca.crt')
    files.upload_template('private/ombuweb.com.crt', env.host_site_path +
            '/private/' + env.url + '.crt')
    files.upload_template('private/apache_vhost', env.host_site_path +
            '/private/' + env.url, env)
    sudo('ln -fs %s/private/%s /etc/apache2/sites-available/%s' %
            (env.host_site_path, env.url, env.url))
    sudo('a2ensite %s' % env.url)
    sudo('a2enmod rewrite ssl')

def setup_env_helloworld():
    run('mkdir -p ' + env.public_path)
    files.append(env.public_path + '/index.html', '<h1>hello world</h1>')

@task
def deploy(refspec):
    """ a git refspec such as a commit code or branch. note branches should
    include the origin (e.g. origin/1.x instead of 1.x) """
    p = env.host_site_path
    if not files.exists(p + '/repo'):
        run('cd %s && git clone %s repo' % (p, env.repo))   # clone
    else:
        run('cd %s/repo && git fetch' % p)                  # or fetch
    with(cd(p)):
        run('cd repo && git reset --hard %s && git submodule update ' % refspec
            + '--init --recursive' )
        run('rm -rf current && cp -r repo/redmine current')
    files.upload_template('private/database.yml', p +
    '/current/config/database.yml', env)
    files.upload_template('private/configuration.yml', p +
    '/current/config/configuration.yml', env)
    files.upload_template('private/Gemfile.local', p +
    '/current/Gemfile.local')
    with(cd(p + '/current')):
        run('bundle install --without development test')
        run('rake generate_session_store')
    sudo('service apache2 restart')

@task
def restore():
    """ restore files & db from backup """
    restore_db()
    restore_files()

@task
def restore_files():
    """ restore files from backup """
    run("rsync --human-readable --progress --archive --backup --compress \
        ombu@web301.webfaction.com:/home/ombu/webapps/tickets2/redmine/files/ \
        %(host_site_path)s/files/" % env)

@task
def restore_db():
    run("""echo "drop database if exists %(db_db)s; \
        create database %(db_db)s character set utf8; \
        grant all privileges on %(db_db)s.* to '%(db_user)s'@'%(db_host)s' identified by '%(db_pw)s';" \
        | mysql -u root -p%(db_root_pw)s""" % env)
    run("ssh -C ombu@web301.webfaction.com mysqldump -u ombu_tickets2 ombu_tickets2 \
        | mysql -u%(db_user)s  -p%(db_pw)s -D %(db_db)s" % env)
    with(cd(env.host_site_path + '/current')):
        run('rake db:migrate RAILS_ENV="production"')
        run('rake tmp:clear')

@task
def install_plugins():
    """ Install plugins in plugins/* """
    with(cd(env.host_site_path)):
        run("""
        for plugin in `ls repo/plugins`
        do
            if [ -d current/vendor/plugins/$plugin ]; then
                rm -rf current/vendor/plugins/$plugin
            fi
        done""")
        run('cp -r repo/plugins/* current/vendor/plugins')
        run('cd current && rake db:migrate_plugins RAILS_ENV="production"')

@task
def add_repo(name):
    """ Add a repo to the server """
    path = '/mnt/repos/' + name
    if(files.exists(path)):
        abort('Repo path exists: ' + path)
    else:
        run('git clone --bare git@bitbucket.org:ombu/%s.git %s' % (name, path))
        with(cd(env.host_site_path + '/current')):
            run('ruby script/runner "Repository.fetch_changesets" -e production')
