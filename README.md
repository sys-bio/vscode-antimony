# Antimony for Visual Studio Code

[![MIT License](https://img.shields.io/github/license/sys-bio/vscode-antimony)](https://github.com/sys-bio/vscode-antimony/blob/master/LICENSE)

#### [Repository](https://github.com/sys-bio/vscode-antimony/tree/master/vscode-antimony)&nbsp;&nbsp;|&nbsp;&nbsp;[Issues](https://github.com/sys-bio/vscode-antimony/issues)&nbsp;&nbsp;|&nbsp;&nbsp;[Code Examples](https://github.com/sys-bio/vscode-antimony/tree/master/examples)&nbsp;&nbsp;|&nbsp;&nbsp;[Antimony Reference](https://tellurium.readthedocs.io/en/latest/antimony.html)&nbsp;&nbsp;|&nbsp;&nbsp;[tellurium](https://tellurium.readthedocs.io/en/latest/index.html)&nbsp;&nbsp;|&nbsp;&nbsp;[Marketplace Link](https://marketplace.visualstudio.com/items?itemName=stevem.vscode-antimony)&nbsp;&nbsp;|&nbsp;&nbsp;[Marketplace Link for Extension Pack](https://marketplace.visualstudio.com/items?itemName=stevem.antimony-extension-pack)

The Antimony extension adds language support for Antimony to Visual Studio Code for building models in Systems Biology.

# [Installation (Required)](#installation-required-1)

The currently available version 0.2 is a public beta version developed by [Longxuan Fan](https://www.linkedin.com/in/longxf), [Sai Anish Konanki](https://www.linkedin.com/in/sai-anish-konanki-8b81a575/), [Eva Liu](https://www.linkedin.com/in/evaliu02), [Steve Ma](https://www.linkedin.com/in/steve-ma/), [Gary Geng](https://www.linkedin.com/in/gary-geng-9995a2160/), [Dr. Joseph Hellerstein](https://sites.google.com/uw.edu/joseph-hellerstein/home?authuser=0), and [Dr. Herbert Sauro](https://bioe.uw.edu/portfolio-items/sauro/) at the University of Washington. Dr. Joseph Hellerstein is responsible for future releases, and please feel free to [contact](mailto:joseph.hellerstein@gmail.com) him if you have any questions.

Please note that the current release does not support the complete Antimony grammar. While most grammar has been supported, more will be included in future releases. Flux balance constraints and submodeling are not supported currently.

## **Installation (Required)**
The [Antimony Extension Pack](https://marketplace.visualstudio.com/items?itemName=stevem.antimony-extension-pack) is available on the Visual Studio Code Extensions Tab and the Visual Studio Code Marketplace. (We recommend installing the extension pack directly so you have full access to all of the features.) <br/>

[Windows Instructions](#windows)&nbsp;&nbsp;|&nbsp;&nbsp;[Mac Instructions](#mac)&nbsp;&nbsp;|&nbsp;&nbsp;[Linux Instructions](#linux)

### Windows
* This extension requires [Vscode Antimony Dependencies Installer](https://github.com/sys-bio/vscode-antimony/raw/master/setup/Vscode%20Antimony%20Setup%20Installer.exe) to be installed.
* Your web browser may warn that this isn't a commonly installed software, allow the browser to keep the download.
<p align=center>
<img src="docs/images/warning.png" width=75%>
<br/>
<em>(Press Keep)</em>
</p>

* Once [Vscode Antimony Dependencies Installer](https://github.com/sys-bio/vscode-antimony/raw/master/setup/Vscode%20Antimony%20Setup%20Installer.exe) is installed, open the Downloads folder on your device
* Double click "Vscode Antimony Dependencies Installer" to start the setup process. If there is a warning pop up from Windows, click more info and then click run anyway. **(This will not intefer with any other dependencies and programs of your device)**.

<p align=center>
<img src="docs/images/moreinfo.png" width=75%>
<br/>
<em>(Press more info)</em>
</p>
<p align=center>
<img src="docs/images/runanyway.png" width=75%>
<br/>
<em>(Press run anyway)</em>
</p>

* Once installed, restart Visual Studio Code if you have Visual Studio Code already installed. Otherwise, proceed.
[Next Steps Below](#steps-below-apply-for-all-operating-systems)<br/><br/>

### Mac
* This extension requires [Vscode_Antimony_Setup (Silicon CPU Macbooks)](https://github.com/sys-bio/vscode-antimony/raw/macinstall/setup/Vscode_Antimony_Setup.pkg) or [Python 3.9.13 (Intel Macbooks)](https://www.python.org/ftp/python/3.9.13/python-3.9.13-macos11.pkg) to be installed before use.
* For Intel CPU Macbooks: When installing Python 3.9.13, proceed with the installations as is. No changes are needed to be made.
* For Silicon CPU Macbooks: When installing Vscode_Antimony_Setup.pkg, right click on the pkg file and press open.

<p align=center>
<img src="docs/images/open.png" width=75%>
<br/>
<em>(Right click, then press open)</em>
</p>

* For Silicon CPU Macbooks: Click open when the pop up appears.

<p align=center>
<img src="docs/images/macpopup.png" width=75%>
<br/>
<em>(Click open)</em>
</p>

* Once installed, restart Visual Studio Code if you have Visual Studio Code already installed. Otherwise, proceed. <br/>
[Next Steps Below](#steps-below-apply-for-all-operating-systems)<br/><br/>

### Linux
* Linux users will have to install Python3.10, venv python package, and pip. 
* Once installed, restart Visual Studio Code if you have Visual Studio Code already installed. Otherwise, proceed. <br/>
[Next Steps Below](#steps-below-apply-for-all-operating-systems)<br/><br/>

### Steps below apply for all Operating Systems
* **_If there are any non VSCode Antimony associated virtual environments activated, please deactivate them before setting up VSCode Antimony._**<br/>
* Install [Git](https://git-scm.com/downloads). Make sure to add Git to PATH when installing if the option shows. Restart Visual Studio Code if already installed after installation of Git. <br/>
* Install [VSCode](https://code.visualstudio.com/download) for your specific operating system (Mac, Windows, or Linux)
* Once you open VSCode, download the **Antimony Extension Pack** from the Visual Studio Code Extension Marketplace and install. This should install Antimony and Antimony Syntax. Follow the numbered points in the figure below.
<p align=center>
<img src="docs/images/Step2.png" width=75%>
<br/>
<em>(Download Antimony Extension)</em>
</p>

* When an XML or Antimony model file is opened for the first time, a pop up will show. On the other hand, if a user does not have a SBML or Antimony file, they can open the Command Palette (Ctrl + Shift + P for Windows, Cmd + Shift + P for Mac) and type **Open Antimony Start Page**. This will open a simple Antimony page, which will allow for the installation of the virtual environment.
<p align=center>
<img src="docs/images/popup.png" width=75%>
<br/>
<em>(Pop up for setup)</em>
</p>

<p align=center>
<img src="docs/images/startPage.png" width=75%>
<br/>
<em>(Open Antimony Start Page)</em>
</p>

* Click yes to allow creation of virtual environment and installation of required dependencies. Click no to use your own default python interpreter (You can change the Vscode-Antimony python interpreter in the VSCode Settings in section Extensions/vscode-antimony. Use (Cmd + ,) for Mac and (Ctrl + ,) for Windows).
<br/>
<p align=center>
<img src="docs/images/yesno.png" width=75%>
<br/>
<em>(Permissions for Virtual Environment Setup)</em>
</p>

* If there are errors during/after the installation, clear the error prompts--if there are any--on the bottom right corner, right click on the ant/xml file and press "Delete Virtual Environment". Attempt to restart VSCode or your device before clicking yes to the installation prompt again. If errors still occur, it is advices to press "Delete Virtual Environment" a second time.
<br/>
<p align=center>
<img src="docs/images/deletevirenv.png" width=75%>
<br/>
<em>(Error Fix)</em>
</p>

* A pop up may show if the incorrect python version is installed. Click yes, install the correct python version per instructions above and restart VSCode.
<br/>
<br/>
<p align=center>
<img src="docs/images/pythonvererror.png" width=75%>
<br/>
<em>(Python Version Error)</em>
</p>

* Now, right clicking anywhere in the .ant file will display a list of features that can be accessed by users.
<br/>
<p align=center>
<img src="docs/images/rightclick.png" width=75%>
<br/>
<em>(List of options when right clicking in the file)</em>
</p>

## Features
The extension provides many convenient features for developing biological models with the Antimony language in tellurium. The current release focuses on the areas below.

### 1. SBML to Antimony Conversion and Editing

<p align=center>
<img src="docs/images/roundTrippingDemo.png" width=75%>
<br/>
<em>(SBML to Antimony conversion)</em>
</p>

When an SBML file is opened, the editor will automatically convert the SBML file to the Antimony format. User can edit the Antimony file, and save the changes made to the Antimony model back to the original SBML file.
⚠️ Note: this feature can be disabled in settings

<p align=center>
<img src="docs/images/roundTrippingDiagram.png" width=25%>
<br/>
<em>(Diagram of workflow)</em>
</p>

### 2. Browsing Biomodels
The extension allows a user to browse for different biomodels from the [BioModels database](https://www.ebi.ac.uk/biomodels/search?query=*%3A*). The user can query for models with a string or a model number. The chosen model will be displayed in Antimony, which can be saved as SBML or Antimony.

<p align=center>
<img src="docs/images/biomodelBrowsing.gif" width=75%>
<br/>
<em>(Biomodel Browsing with saving)</em>
</p>

### 3. Syntax recognition and highlights

<p align=center>
<img src="docs/images/syntax_highlights.png" width=75%>
<br/>
<em>(Syntax Highlights)</em>
</p>

⚠️ Note: the default syntax highlighting for Antimony is provided by a separate extension [Antimony Syntax](https://marketplace.visualstudio.com/items?itemName=stevem.vscode-antimony-syntax), and is also available in the [Antimony Extension Pack](https://marketplace.visualstudio.com/items?itemName=stevem.antimony-extension-pack) 

### 4. Automatic annotation creation with database recommendation
The extension can recognize different types of variables, and recommend databases based on the [OMEX metadata specification](https://doi.org/10.1515/jib-2021-0020).

<p align=center>
<img src="docs/images/annotation0.2.gif" width=75%>
<br/>
<em>(Creating an annotation of species BLL through the ChEBI database)</em>
</p>

### 5. Hover messages 

<p align=center>
<img src="docs/images/hover.gif" width=75%>
<br/>
<em>(Hovering over species to look up information)</em>
</p>

### 6. Code navigation

<p align=center>
<img src="docs/images/nav.gif" width=75%>
<br/>
<em>(Navigating to the definition code)</em>
</p>

### 7. Error detection
The extension supports various warning and error detections to help modelers debug their model during development. Our design principle for whether an issue should be a warning or an error entirely depends on the logic of tellurium. Our extension will mark the subject as an error if tellurium throws an error while rendering the model, with a red underline. An example would be calling a function that does not exist (usually due to a typo, which is extremely common during development. Read more in my [thesis](https://drive.google.com/file/d/1FutuOYgq9Jd_AHqp_z4f2joDavVIURuz/view?usp=sharing)).

<p align=center>
<img src="docs/images/function.gif" width=75%>
<br/>
<em>(Typos are extremely common in software development)</em>
</p>

On the other hand, certain issues are not errors in tellurium, but we thought it would be worthwhile to have the user's attention. For example, missing initial values for species and overriding a previously defined value.

<p align=center>
<img src="docs/images/warning.gif" width=75%>
<br/>
<em>(Forgetting to initialize the value for a species, causing tellurium to assume a default value)</em>
</p>

The extension supports a wide range of errors and warnings, and we plan to support more in the upcoming releases. Read more in [issues](https://github.com/sys-bio/issues).

### 8. Converter between Antimony and SBML

<p align=center>
<img src="docs/images/converter_SBML.gif" width=75%>
<br/>
<em>(Exporting Antimony file in SBML format)</em>
</p>

### 9. Antimony/SBML preview

<p align=center>
<img src="docs/images/preview.gif" width=75%>
<br/>
<em>(Previewing Antimony file as SBML)</em>
</p>

### 10. Automatic creation of rate laws

<p align=center>
<img src="docs/images/rate_law.gif" width=75%>
<br/>
<em>(Creating a rate law on a reversible reaction)</em>
</p>

### 11. Annotation recommender for species

<p align=center>
<img src="docs/images/recommender.gif" width=75%>
<br/>
<em>(Creating annotation for species BLL with Annotation Recommender)</em>
</p>

### 12. Highlight indication for annotated species
<p align=center>
<img src="docs/images/highlight.gif" width=75%>
<br/>
<em>(Displaying highlight indication for annotated species, BLL)</em>
</p>

## Known Issues
I have an open issue for [manually curating models](https://github.com/sys-bio/vscode-antimony/issues/26) from BioModels to test the extension. Please feel free to contribute and submit issues.
* subvariables in modular models are currently not supported and false error messages will be triggered.

## Release Notes

### 0.1.0
* First public release of the extension pack.

### 0.1.1
* Added docs and examples.
* Fixed an issue related to code navigation ([#46](https://github.com/sys-bio/vscode-antimony/issues/46)).
* Fixed an issue related to displaying hover message for annotated entities ([#47](https://github.com/sys-bio/vscode-antimony/issues/47)).

### 0.1.2
* Updated docs.

### 0.1.3
* Updated docs.

### 0.1.4
* Updated docs, included a list for updates in 0.2.

### 0.2.0
* Added grammar support and warning/error detection for rate rules, sbo and cvterms, events, flux balance constraints, interaction, and import.
* Converter between Antimony and SBML.
* Antimony/SBML preview.
* More databases supported in create annotation, and database recommendations.
* Automatic creation of rate laws.
* Annotation recommender for species.
* Highlight indication for annotated species.

### 0.2.4
* Automatic virtual environment installation.
* SBML to Antimony Conversion and Editing.
* Browsing Biomodels.

### 0.2.10
* Minor bug fixes
* Updated User Instructions
