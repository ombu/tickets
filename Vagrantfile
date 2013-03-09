Vagrant::Config.run do |config|

  config.vm.box = "precise-amd64-mr"
  config.ssh.forward_agent = true
  config.vm.network :bridged #, :bridge => "en1: Wi-Fi (AirPort)"
  config.ssh.private_key_path = "/Users/axolx/.ssh/axolx-base"

  config.vm.provision :puppet, :options => "--verbose" do |puppet|
    puppet.manifests_path = "puppet"
    puppet.manifest_file  = "node.pp"
    puppet.module_path = "/Users/axolx/sandbox/envs/puppetboot/repo/modules"
  end

  # share puppet manifest
  config.vm.share_folder "puppet-manifest", "/etc/puppet", "/Users/axolx/sandbox/envs/puppetboot/repo"

end
