VAGRANTFILE_API_VERSION = '2'

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.ssh.forward_agent = true
  config.vm.box = 'trusty-i386'
  config.vm.network :private_network, :ip => '10.20.1.3'
  config.cache.auto_detect = true

  config.vm.provision :puppet, :options => '--verbose' do |puppet|
    puppet.manifests_path ='/Users/axolx/sandbox/envs/puppetboot/repo/manifests'
    puppet.module_path = '/Users/axolx/sandbox/envs/puppetboot/repo/modules'
    puppet.manifest_file  = 'tickets.pp'
  end

  # share puppet manifest
  config.vm.synced_folder '/Users/axolx/sandbox/envs/puppetboot/repo/',
                          '/etc/puppet'

end
