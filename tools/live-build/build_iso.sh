#!/bin/sh
mkdir config/includes.binary
echo " * Creating dummy configuration file."
tr '\000' '\007' < /dev/zero | dd of=config/includes.binary/dummy.tar.gz bs=1024 count=10k
echo " * Starting build of ISO file"
lb build
mv binary.hybrid.iso beeswarm_client.iso
echo " * Beeswarm client (hive/feeder) ISO has been generated and saved as beeswarm_client.iso"