Adding new python dependencies: <br/>
    When using new python dependencies for vscode-antimony development, don't forget to edit:
    <li>all-requirements.txt
    <li> virtualEnvWin.bat
    <li>virtualEnvLinux.sh 
    <li>virtualEnvSilicon.sh 
<br/>
<br/>
Packaging and publishing to VSCode Marketplace: <br/>
    https://code.visualstudio.com/api/working-with-extensions/publishing-extension <br/>
    <li>Step 1: npm install -g @vscode/vsce
    <li>Step 2: Change the version (and maybe publisher as well) in package.json
    <li>Step 3: run "cd <extension_file>",
    <li>Step 4: Comment out logger code for production in main.py (MUST DO BEFORE PUBLISHING)
    <li>Step 5: run "vsce package"
    <li>Step 6: run "vsce publish <version_of_extension>"

Set up a symlink (On Windows cmd): <br/>
    <li>run "git config core.symlinks true" to allow for symlinks
    <li>run "mklink [Name of Symlink File] [Name of Source File]

Remove a symlink (On Linux terminal): <br/>
    <li>run "cp --remove-destination 'readlink [Name of Symlink File]' [Name of Symlink File]"
    <li>run "readlink [Name of Symlink File]" to check if there is a path returned. If a path is shown, the symlink is still active