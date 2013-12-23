from fabric.api import task, env, run, abort, sudo, cd, execute, prompt
from fabric.contrib import console, files

env.repo_type = 'git'
env.repo = 'git@github.com:ombu/tickets.git'
env.repo_branch = 'master'
env.use_ssh_config = True
env.forward_agent = True


# Host settings
@task
def local():
    """
    The local (Vagrant) server definition
    """
    env.repo_branch = 'feature/2.4'
    env.user = 'axolx'
    env.hosts = ['axolx@tickets.dev:22']
    env.host_type = 'development'
    env.url = 'tickets.dev'
    env.app_path = '/var/www/tickets.dev'
    env.public_path = '/var/www/tickets.dev/current/public'
    env.db_host = 'qadb.cpuj5trym3at.us-west-2.rds.amazonaws.com'
    env.db_db = 'tickets_local'
    env.db_user = 'tickets_local'
    env.db_pw = 'SETME'
    env.smtp_host = 'SETME'
    env.smtp_user = 'SETME'
    env.smtp_pw = 'SETME'


@task
def staging():
    """
    The staging server definition
    """
    env.hosts = ['ombu@tickets:34165']
    env.host_type = 'staging'
    env.user = 'ombu'
    env.url = 'tickets.stage.ombuweb.com'
    env.app_path = '/home/ombu/redmine-stage'
    env.public_path = '/home/ombu/redmine-stage/current/public'
    env.db_host = 'qadb.cpuj5trym3at.us-west-2.rds.amazonaws.com'
    env.db_db = 'tickets_stage'
    env.db_user = 'tickets_stage'
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
    env.user = 'axolx'
    env.hosts = ['axolx@54.244.195.139']
    env.host_type = 'production'
    env.url = 'tickets.ombuweb.com'
    env.app_path = '/var/www/tickets.ombuweb.com'
    env.public_path = '/var/www/tickets.ombuweb.com/current/public'
    env.db_db = 'tickets'
    env.db_user = 'tickets'
    env.db_pw = 'VuqRTwcLrjsT75H'
    env.db_host = 'localhost'
    env.smtp_host = 'mail.authsmtp.com'
    env.smtp_user = 'ac40599'
    env.smtp_pw = '7rzomKKHNYik7rgS'
    env.uploads_path = '/mnt/tickets/uploads'


@task
def setup_env():
    setup_env_dir()
    setup_env_vhost()


def setup_env_dir():
    if files.exists(env.app_path):
        if console.confirm("Found %s. Replace it?" % env.app_path, default=False):
            run('rm -rf %s' % env.app_path)
        else: abort('Quitting')
    run('mkdir -p %s' % env.app_path)
    run('cd %(app_path)s && chgrp www-data %(app_path)s && chmod g+s %(app_path)s' % env)
    run('cd %(app_path)s && mkdir log private' % env)
    print('Site directory structure created at: %(app_path)s' % env)


def setup_env_vhost():
    files.upload_template(
        'private/apache_vhost', env.app_path + '/private/' + env.url, env)
    sudo(
        'ln -fs %(app_path)s/private/%(url)s '
        '/etc/apache2/sites-available/%(url)s' % env)
    sudo('a2ensite %s' % env.url)


@task
def deploy(refspec):
    """ a git refspec such as a commit code or branch. note branches should
    include the origin (e.g. origin/1.x instead of 1.x) """
    p = env.app_path
    if not files.exists(p + '/repo'):
        run('cd %s && git clone -q %s repo' % (p, env.repo))   # clone
    else:
        run('cd %s/repo && git fetch' % p)                  # or fetch
    with(cd(p)):
        run('cd repo && git reset --hard %s && git submodule -q update '
            % refspec + '--init --recursive')
        sudo('rm -rf current')
        run('cp -r repo/redmine current')
    files.upload_template('private/database.yml', p +
                          '/current/config/database.yml', env)
    files.upload_template('private/configuration.yml', p +
                          '/current/config/configuration.yml', env)
    # Candidate to remove
    #files.upload_template('private/Gemfile.local', p +
    #                      '/current/Gemfile.local')
    with(cd(p + '/current')):
        # Install these manually because in Ubuntu 12.04 compilation fails with
        # Bundler
        sudo('bundle install --without development test postgresql sqlite')
        execute(install_plugins)
        run('rake tmp:cache:clear')
        run('rake tmp:sessions:clear')
    sudo('service apache2 force-reload')


@task
def uninstall():
    uninstall = prompt(
        "This operation can lead to data loss. Are you sure "
        "you want delete the tickets app on %s?" % env.host_type)
    if not uninstall == 'y':
        abort('Sync aborted')
    sudo('if [ -d %(app_path)s ]; then rm -rf %(app_path)s; fi' % env)
    sudo(
        'if [ -h /etc/apache2/sites-enabled/%(url)s ]; then unlink '
        '/etc/apache2/sites-enabled/%(url)s; fi' % env)
    sudo(
        'if [ -h /etc/apache2/sites-available/%(url)s ]; then unlink '
        '/etc/apache2/sites-available/%(url)s; fi' % env)
    sudo('service apache2 restart')


@task
def sync_stage():
    """ restore files from backup """
    #run("rsync --human-readable --progress --archive --backup --compress \
    #    ombu@web301.webfaction.com:/home/ombu/webapps/tickets2/redmine/files/ \
    #    %(app_path)s/files/" % env)
    #run("""echo "drop database if exists %(db_db)s; \
    #    create database %(db_db)s character set utf8; \
    #    grant all privileges on %(db_db)s.* to '%(db_user)s'@'%(db_host)s' identified by '%(db_pw)s';" \
    #    | mysql -u root -p%(db_root_pw)s""" % env)
    #run("ssh -C ombu@web301.webfaction.com mysqldump -u ombu_tickets2 ombu_tickets2 \
    #    | mysql -u%(db_user)s  -p%(db_pw)s -D %(db_db)s" % env)
    #with(cd(env.app_path + '/current')):
    #    run('rake db:migrate RAILS_ENV="production"')
    #    run('rake tmp:clear')


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
        with(cd(env.app_path + '/current')):
            # sudo('bundle install --without development test postgresql sqlite')
            # "production" hardcoded below because the current env
            # credentials are interpolated in the production config
            sudo('chmod 0770 Gemfile.lock')
            run('rake redmine:plugins:migrate RAILS_ENV=production')


@task
def add_repo(name):
    """ Add a repo to the server """
    path = '/mnt/repos/' + name
    if(files.exists(path)):
        abort('Repo path exists: ' + path)
    else:
        run('git clone -q --bare git@bitbucket.org:ombu/%s.git %s' % (name, path))
        with(cd(env.app_path + '/current')):
            run('ruby script/runner "Repository.fetch_changesets" -e production')
