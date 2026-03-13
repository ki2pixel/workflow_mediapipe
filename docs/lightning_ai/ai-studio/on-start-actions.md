# On-start actions[](#on-start-actions)

Automate tasks at Studio launch with on-start actions. Use this to automatically start web servers, data preprocessing or a custom workflow.

## on\_start.sh file[](#onstartsh-file)

Edit the ` on_start.sh ` script located in the ` .lightning_studio ` folder of the Studio's home directory. It supports basic shell syntax and auto-executes each time this Studio launches. Use it to copy files, install applications, start services; any actions that should take place every time this studio starts. Environment variables set in this script are not set in subsequent studio terminals. To set environment variables in the studio, see the next section, [Customize the shell](https://lightning.ai/docs/overview/ai-studio/on-start-actions#customize-the-shell) .

`1 2 3 4 5 6 7 8 ` ` #!/bin/bash # This script runs every time your Studio starts, from your home directory. export SOME_IMPORTANT_PATH="/teamspace/studios/this_studio/path/to/some/important/folder" # start a server python server.py `

Example ` on_start.sh ` outlines setting ` SOME_IMPORTANT_PATH ` and initiating a ` uvicorn ` web server, automating a very manual setup process.


## Load files faster[](#load-files-faster)

In certain cases, like model serving, it's necessary to load checkpoints first before any other file. In this case, use the ` !fast_load ` command in the on\_start.sh to load these files to the fastest available storage type.

`1 2 3 4 5 6 7 8 ` ` #!/bin/bash # List files under fast_load that need to load quickly on start (e.g. model checkpoints). # # !fast_load # path/to/some/important/folder/model-checkpoint.ckpt # path/to/some/important/folder/other-model-checkpoint.ckpt # path/to/some/important/other/folder/ ** `

The ` fast_load ` directives cannot be applied to folders. Instead use the ` globbing ` syntax as shown above.
Note that it is important that both the fast\_load directive as well as the file paths below are still commented.

# Customize the shell[](#customize-the-shell)

## Per Studio[](#per-studio)

Customize the shell settings persistently within a Studio by altering ` .zshrc ` and ` .bashrc ` files in the home directory. However, these customizations are Studio-specific and won't carry over to new Studios.

These files contain a section sourcing the ` .lightningrc ` file \(a settings file completely managed by Lightning AI\) at the bottom. Do not remove that section\!
However, for some changes \(like the ` PROMPT ` \) you need to overwrite the default configuration provided by your Studio. For these cases, just change it after the sourcing of that ` .lightningrc ` file but make sure to keep the sourcing in place.

## Across Studios[](#across-studios)

For consistent shell settings across all Studios, use the ` .studiorc ` file in the ` .lightning_studio ` folder. It accepts standard shell syntax and applies to every shell session across Studios.

Be cautious: ` .studiorc ` impacts both ` zsh ` and ` bash ` shells. Use conditionals to prevent syntax errors or unintended executions across shell types.

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` # this part is executed in both shell types if [[ "${SHELL}" == "zsh" ]]; then # do whatever you want in zsh fi # this part is executed in both shell types if [[ "${SHELL}" == "bash" ]]; then # do whatever you want in bash fi # this part is executed in both shell types`

