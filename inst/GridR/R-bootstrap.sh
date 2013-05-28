#!/bin/sh

# default install directory
# reset the home directory
unset HOME 
R_INSTALL_DIR=~/


run_R () {

    export PATH=${R_INSTALL_DIR}/bosco/R/bin:$PATH
    R "$@"


}

install_R () {

    # First, create the R directory
    mkdir -p ${R_INSTALL_DIR}/bosco/R
    
    # phase 1 of 2 phase commit
    touch ${R_INSTALL_DIR}/bosco/R/.started
    
    # Download R 
    # OSG particular
    if [ "x$OSG_SQUID_LOCATION" != "x" ]; then
        http_proxy=$OSG_SQUID_LOCATION
    fi
    
    wget https://www.dropbox.com/s/a1fb39cvg5oybhv/el5-R-modified.tar.gz -O R-modified.tar.gz --no-check-certificate
    tar xzf R-modified.tar.gz
    mv R/* ${R_INSTALL_DIR}/bosco/R/
    
    # phase 2 of 2 phase commit
    touch ${R_INSTALL_DIR}/bosco/R/.completed
    
    run_R "$@"

}


# First, check for writability in the home directory
home_writable=0
touch ${R_INSTALL_DIR}/writable && rm -f ${R_INSTALL_DIR}/writable && home_writable=1

if [ "$home_writable" -ne "1" ]; then 
    R_INSTALL_DIR=`pwd`
fi


# Next, check for an R installation
if [ -e ${R_INSTALL_DIR}/bosco/R ]; then
    
    # If the R directory exists, check for for the completed install file
    if [ -e ${R_INSTALL_DIR}/bosco/R/.completed ]; then 
        run_R "$@"
        exit 0
    fi
    
    # Check if the installation has started
    if [ -e ${R_INSTALL_DIR}/bosco/R/.started ]; then
        # Install has started... somewhere.  
        # Now wait 5 minutes for the install to complete, then try to install again.
        install_done=0
        wait_counter=0
        
        while [ "$install_done" -eq "0" -a "$wait_counter" -lt "300" ]; do
            sleep 5
            (( wait_counter += 5))
            if [ -e ${R_INSTALL_DIR}/bosco/R/.completed ]; then
                $install_done=1
            fi
            
        done
        
        # If we get to this point, install and move on
        if [ "$install_done" -eq "0" ]; then
            install_R "$@"
            exit 0
        else
            run_R "$@"
            exit 0
        fi
        
        
    fi
    install_R "$@"
    exit 0
    
else
    # If the R directory doesn't exist
    install_R "$@"
    exit 0
fi


