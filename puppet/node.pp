node default {
    class { [base, ombussl, rails]: }

    package { [ 'libmagickwand-dev', 'libopenssl-ruby', 'libmysqlclient-dev' ]:
        ensure    => installed,
    }

    # Needed to build webrat gem, which is required by Redmine
    package { [ 'libxml2-dev', 'libxslt-dev' ]:
        ensure    => installed,
    }

    # Redmine gem requirements that Bundler fails at installing
    package { [ 'bundler', 'json', 'mysql', 'rdiscount', 'rmagick' ]:
        ensure   => 'installed',
        provider => 'gem',
    }

    class {'apache::mod::ssl': }

    file { "/var/www":
        ensure => "directory",
        owner  => 'root',
        group  => 'www-data',
        mode   => '770',
    }

}
