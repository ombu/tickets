node default {
    class { [base, ombussl, rails]: }

    package { [ 'libmagickwand-dev', 'libopenssl-ruby', 'libmysqlclient-dev' ]:
        ensure    => installed,
    }

    class {'apache::mod::ssl': }

    file { "/var/www":
        ensure => "directory",
        owner  => 'root',
        group  => 'www-data',
        mode   => '770',
    }

}
