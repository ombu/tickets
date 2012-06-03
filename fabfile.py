from fabric.api import task, env, run, abort, sudo
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
  env.hosts = ['ombu@tk:34165']
  env.host_type = 'production'
  env.user = 'ombu'
  env.url = 'tk.ombuweb.com'
  env.host_webserver_user = 'www-data'
  env.host_site_path = '/home/ombu/redmine'
  env.public_path = '/home/ombu/redmine/redmine/public'
  env.db_db = 'tickets'
  env.db_user = 'tickets'
  env.db_pw = 'meh'
  env.db_host = 'localhost'

@task
def setup_env():
    _setup_env_dir()
    _setup_env_webserver_ssl()
    _setup_env_helloworld()
    sudo('service apache2 restart')

def _setup_env_dir():
    if files.exists(env.host_site_path):
        if console.confirm("Found %s. Replace it?" % env.host_site_path, default=False):
            run('rm -rf %s' % env.host_site_path)
        else: abort('Quitting')
    run('mkdir -p %s' % env.host_site_path)
    run('cd %s && mkdir files log private' % env.host_site_path)
    print('Site directory structure created at: %s' % env.host_site_path)

def _setup_env_webserver_ssl():
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

def _setup_env_helloworld():
    run('mkdir -p ' + env.public_path)
    files.append(env.public_path + '/index.html', '<h1>hello world</h1>')

@task
def deploy():
    pass

@task
def upgrade_db():
    local('rake db:migrate RAILS_ENV="development"')
    local('rake redmine:plugins:migrate RAILS_ENV="development"')
    local('rake tmp:clear')
