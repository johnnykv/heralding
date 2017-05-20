#!/bin/bash

# Simple installation script for Heralding Honeypot on an Ubuntu server.
# Must be run as root (sudo).


#################
##Create folder##
#################

mkdir Github/

######################
##Navigate to folder##
######################

cd Github/

####################################################################
##Install essentials for heralding honeypot to succesfully install##
####################################################################

apt-get install git build-essential libssl-dev libffi-dev python-dev python-pip build-dep python-imaging

#############################
##Clone heralding to folder##
#############################

git clone https://github.com/johnnykv/heralding

######################
##Navigate to folder##
######################

cd heralding/

###############
##Upgrade pip##
###############

pip install --upgrade pip

########################
##Install cryptography##
########################

pip install cryptography

####################################
##Install requrements for heraldig##
####################################

pip install -r requirements.txt

#####################
##Install heralding##
#####################

pip install heralding

#########################
##Clear terminal window##
#########################

clear

#############
##Echo text##
#############

echo “If you can see this, then it means that the script ran successfully“
