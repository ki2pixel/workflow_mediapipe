# On-stop actions[](#on-stop-actions)

Automate tasks at Studio shutdown with on-stop actions. Use this to automatically stop servers, delete temporary files or sync resources to external repositories.

## on\_stop.sh file[](#onstopsh-file)

Edit the ` on_stop.sh ` script located in the ` .lightning_studio ` folder of the Studio's home directory. It supports basic shell syntax and auto-executes with each Studio shutdown. Use it to shutdown servers or clean up the studio environment before the studio is persisted:

`1 2 3 4 5 6 7 8 ` ` #!/bin/bash # This script runs every time your Studio sleeps, from your home directory. # Add your shutdown commands below. # # Example: docker down my-container # Example: sudo service mysql stop`

