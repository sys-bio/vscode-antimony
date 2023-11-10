When setting up vscode-antimony repo on a new device, don't forget to install the venv, npm install and npm run webpack.

Adding new python dependencies:
    When using new python dependencies for vscode-antimony development, don't forget to edit:
      all-requirements.txt
       virtualEnvWin.bat
      virtualEnvLinux.sh 
      virtualEnvSilicon.sh 


Packaging and publishing to VSCode Marketplace: 
    https://code.visualstudio.com/api/working-with-extensions/publishing-extension 
      Step 1: npm install -g @vscode/vsce
      Step 2: Change the version (and maybe publisher as well) in package.json
      Step 3: run "cd <extension_file>",
      Step 4: Comment out logger code for production in main.py (MUST DO BEFORE PUBLISHING)
      Step 5: run "vsce package"
      Step 6: run "vsce publish <version_of_extension> --target win32-x64"

Set up a symlink (On Windows cmd): 
      run "git config core.symlinks true" to allow for symlinks
      run "mklink [Name of Symlink File] [Name of Source File]

Remove a symlink (On Linux terminal): 
      run "cp --remove-destination 'readlink [Name of Symlink File]' [Name of Symlink File]"
      run "readlink [Name of Symlink File]" to check if there is a path returned. If a path is shown, the symlink is still active