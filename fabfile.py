from fabric.api import task, env, run, abort, sudo, cd
from fabric.contrib import console
from fabric.contrib import files
#from butter import deploy

env.repo_type = 'git'
env.repo = 'https://github.com/ombu/redmine'
env.use_ssh_config = True
env.forward_agent = True

# Host settings
@task
def production():
    """
    The production server definition
    """
    #env.hosts = ['ombu@tk:34165']
    env.hosts = ['ombu@184.169.222.15:34165']
    env.host_type = 'production'
    env.user = 'ombu'
    env.url = 'tk.ombuweb.com'
    env.host_webserver_user = 'www-data'
    env.host_site_path = '/home/ombu/redmine'
    env.public_path = '/home/ombu/redmine/current/public'
    env.db_db = 'tickets'
    env.db_user = 'tickets'
    env.db_pw = 'SETME'
    env.db_host = 'localhost'
    env.db_root_pw = 'SETME'

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
    files.upload_template('private/' + env.url + '.key', env.host_site_path +
            '/private/' + env.url + '.key')
    files.upload_template('private/' + env.url + '.ca.crt', env.host_site_path +
            '/private/' + env.url + '.ca.crt')
    files.upload_template('private/' + env.url + '.crt', env.host_site_path +
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
def deploy():
    p = env.host_site_path
    if not files.exists(p + '/repo'):
        run('cd %s && git clone %s repo' % (p, env.repo))   # clone
    else:
        run('cd %s/repo && git fetch' % p)                  # or fetch
    with(cd(p)):
        run('cd repo && git reset --hard origin/master && git submodule update --init --recursive')
        run('rm -rf current && cp -r repo/redmine current')
    with(cd(p + '/current')):
        run('bundle install --without development test')
        run('rake generate_session_store')
    files.upload_template('private/database.yml', p +
    '/current/config/database.yml', env)
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
        #run('rake redmine:plugins:migrate RAILS_ENV="production"')
        run('rake tmp:clear')


@task
def install_plugin():
