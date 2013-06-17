#!/usr/bin/env python
# This script is meant to atomically download and install R
#
# Author: Derek Weitzel <djw8605@gmail.com>

from os.path import expanduser
import os
import tempfile
import subprocess
import sys
import time
import urllib2
import platform
import shutil
import tarfile

UNKNOWN="UNKNOWN"
UNSUPPORTED="UNSUPPORTED"
RH5="RH5"
RH6="RH6"
OSX="MAC"
OSX_UNSUPPORTED="UNSUPPORTED"
DEB6="DEB6"

SUPPORTED_OSX = ['10.6', '10.7', '10.8']
SUPPORTED_PLATFORMS = [ RH5, RH6, DEB6 ]

# download URLs for the different platforms
URL_DICT={
  DEB6: "To be determined",
  RH5: "https://www.dropbox.com/s/a1fb39cvg5oybhv/el5-R-modified.tar.gz",
  RH6: "https://www.dropbox.com/s/7qfa9no0ckusuys/el6-R-modified.tar.gz",
}

def findInstallDir(home_dir):
    
    return_dir = home_dir
    
    # First, check for writability in the home directory
    if not os.access(home_dir, os.W_OK):
        return_dir = os.getcwd()
    
    return return_dir
    

def findversion_redhat(detail=False):
  # content of /etc/redhat-release
  # Scientific Linux release 6.2 (Carbon)
  # Red Hat Enterprise Linux Server release 5.8 (Tikanga)
  # Scientific Linux SL release 5.5 (Boron)
  # CentOS release 4.2 (Final)
  #
  # Do we support FC:Fedora Core release 11 ... ?
  #
  # should I check that it is SL/RHEL/CentOS ? 
  # no 
  lines = open('/etc/redhat-release').readlines()
  for line in lines:
    if detail and 'release'in line:
      return line
    if 'release 5.' in line:
      return RH5
    if 'release 6.' in line:
      return RH6
    return UNSUPPORTED
  return UNKNOWN
  
def findversion_debian(detail=False):
  """cat /etc/*release
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=11.10
DISTRIB_CODENAME=oneiric
DISTRIB_DESCRIPTION="Ubuntu 11.10"

user@bellatrix:~$ lsb_release
No LSB modules are available.

user@bellatrix:~$ lsb_release -a  
No LSB modules are available.

Distributor ID:    Ubuntu
Description:    Ubuntu 11.10
Release:    11.10
Codename:    oneiric       
"""
  retv = UNSUPPORTED
  lines = open('/etc/lsb-release').readlines()
  for line in lines:
    if detail:
       if 'DISTRIB_DESCRIPTION' in line:
        return line[len('DISTRIB_DESCRIPTION='):]
    if 'DISTRIB_ID' in line:
      if not 'Debian' in line:
        return UNSUPPORTED
    if 'DISTRIB_RELEASE' in line:
        if line[len('DISTRIB_RELEASE='):].startswith('6.'):
          retv = DEB6
  return retv
  
  

def findversion():
  if not os.name == 'posix':
    return UNSUPPORTED
  if sys.platform == 'darwin':
    myver = platform.mac_ver()
    if myver[0]:
      if '.'.join(myver[0].split('.')[:2]) in SUPPORTED_OSX:
        return OSX
    return findversion_mac()
  elif sys.platform.startswith('linux'):
    # only 64 bit supported
    if not platform.architecture()[0] == '64bit':
      return UNSUPPORTED
    # try first platform.dist, use it only for positive recognition
    mydist = platform.dist()
    if mydist[0]:
      if mydist[0].lower() == 'redhat':
        if mydist[1].startswith('5.'):
          return RH5
        if mydist[1].startswith('6.'):
          return RH6
      if mydist[0].lower() == 'debian':
        if mydist[1].startswith('6.'):
          return DEB6
    if os.path.isfile('/etc/redhat-release'):
      return findversion_redhat()
    elif os.path.isfile('/etc/lsb-release'):
      return findversion_debian()
  return UNKNOWN


def installR(install_dir):
    # First, create the R directory
    if not os.path.isdir(install_dir):
        try:
            os.makedirs(install_dir)
        except OSError:
            # we can't make the directories in the install_dir, bail
            return 1
    
    # Second, place the .started file
    started_file = open(os.path.join(install_dir, ".started"), 'a')
    started_file.close()
    
    # Determine the operating system and download correct binary
    version = findversion()
    
    # Have to fake the user agent so dropbox doesn't give us a html page
    request = urllib2.Request(URL_DICT[version], None, {"User-Agent": "curl/7.29.0"})
    response = urllib2.urlopen(request)
    tmp_dir = tempfile.mkdtemp()
    tar_name = os.path.join(tmp_dir, 'R-modified.tar.gz')
    f = open(tar_name, 'w')
    shutil.copyfileobj(response, f)
    f.close()
    response.close()
    
    # Untar
    tar = tarfile.open(tar_name, 'r')
    tar.extractall(tmp_dir)
    
    # Ok, now move the R installation into the correct directory
    tmp_r_dir = os.path.join(tmp_dir, 'R')
    for rDir in os.listdir(tmp_r_dir):
        shutil.move(os.path.join(tmp_r_dir, rDir), os.path.join(install_dir, rDir))
    #shutil.move(os.path.join(tmp_dir, 'R'), install_dir)
    shutil.rmtree(tmp_dir)
    
    # Create the .completed file
    f = open(os.path.join(install_dir, ".completed"), 'a')
    f.close()
    


def runR(r_dir):
    # Run R
    r_binary = os.path.join(r_dir, "bin", "R")
    # Set the environment up correctly
    os.environ["PATH"] = os.path.join(r_dir, "bin") + ":" + os.environ["PATH"]
    
    # Call R, with stdout and stderr going to our stdout/stderr
    return subprocess.call(r_binary + " " + " ".join(sys.argv[1:]), shell=True)
    

def main():
    # Blahp, in it's infinite wisdom, redfines the $HOME directory
    # We have to get the actual $HOME directory
    del os.environ["HOME"]
    home_dir = expanduser("~")
    install_dir = findInstallDir(home_dir)
    r_dir = os.path.join(install_dir, "bosco", "R")
    
    if os.path.isdir(r_dir):
        if os.path.exists(os.path.join(r_dir, ".completed")):
            return runR(r_dir)
        
        if os.path.exists(os.path.join(r_dir, ".started")):
            # Install has started... somewhere.  
            # Wait 5 minutes for the .completed to show up.
            counter = 60*5
            while counter > 0:
                time.sleep(5)
                counter -= 5
                if os.path.exists(os.path.join(r_dir, ".completed")):
                    return runR(r_dir)     
                else:
                    continue
                
            if counter <= 0:
                # Timer ran out, Install R myself
                installR(r_dir)
                return runR(r_dir)
        
        # If the .completed doesn't exist, and .started doesn't exist, but 
        # r_dir does exist, something odd happened, and we need to install and
        # start over
        installR(r_dir)
        return runR(r_dir)
           
        
    else:
        installR(r_dir)
        return runR(r_dir)



if __name__ == "__main__":
    sys.exit(main())

