# -*- coding: utf-8 -*-
"""
Created May 2020

@author: Lucian Smith
"""


##@Module antimonyPython
#This module allows access to the antimony.dll from python
import os
from ctypes import c_long, c_int, c_char_p, c_ulong, c_bool, c_double, POINTER, cdll
import inspect
import platform

# Ctypes will only load the dll properly if the working directory is the same as 
# the directory where the dll is (at least on Windows).
__thisfile = inspect.getframeinfo(inspect.currentframe()).filename
__libdir = os.path.dirname(os.path.abspath(__thisfile))
#print(__thisfile)
#print(__libdir)

__oldir = os.getcwd()
os.chdir(__libdir)

__osname = platform.system()
if __osname == "Windows":
   __sharedLib = os.path.join(__libdir, 'libantimony.dll')
elif __osname == "Linux":
   __sharedLib = os.path.join(__libdir, "libantimony.so")
elif __osname == "Darwin":
   __sharedLib = os.path.join(__libdir, "libantimony.dylib")

if not os.path.isfile(__sharedLib):
    print('Unable to find shared library file', __sharedLib, "Exiting.")
    exit()
else:
    pass
    #print(__sharedLib, 'found.')
__antLib = cdll.LoadLibrary(__sharedLib)

os.chdir(__oldir)

#Definitions
__version__ = "2.12.0"

#Library functions
__antLib.loadFile.restype = c_long
__antLib.loadFile.argtypes = (c_char_p, )

def loadFile(filename):
   """
   Load a file of any format libAntimony knows about (potentially Antimony, SBML, or CellML).  If all attempts fail, the errors from the attempt to read the file in the Antimony format are saved, so if the file is actually SBML or CellML, the error is likely to be "but contains errors, the reported errors will be from the attempt to read it as Antimony, and a '-1' is returned.

   NOTE:  This function will not attempt to parse the file as SBML if libAntimony is compiled with the '-NSBML' flag, and will not attempt to parse the file as CellML if compiled with the '-NCELLML' flag.

   @return a long integer indicating the index of the file read and stored.  On an error, returns -1 and no information is stored.

   @param filename The filename as a character string.  May be either absolute or relative to the directory the executable is being run from.

   @see getLastError()
   """
   if type(filename) == str:
      filename = filename.encode('utf-8')
   return __antLib.loadFile(filename)

__antLib.loadString.restype = c_long
__antLib.loadString.argtypes = (c_char_p, )

def loadString(model):
   """
   Load a string of any format libAntimony knows about (potentially Antimony, SBML, or CellML).  The first attempts to read the string as SBML, and if this results in an error, then reads it as Antimony.  If this, too, results in an error, the second error is saved, and a '-1' is returned.

   NOTE:  This function will not attempt to parse the string as SBML if libAntimony is compiled with the '-NSBML' flag, and will not attempt to parse the string as CellML if compiled with the '-NCELLML' flag.

   @return a long integer indicating the index of the string read and stored.  On an error, returns -1 and no information is stored.

   @param model The model, in (potentially) Antimony, SBML, or CellML format.

   @see getLastError()
   """
   if type(model) == str:
      model = model.encode('utf-8')
   return __antLib.loadString(model)

__antLib.loadAntimonyFile.restype = c_long
__antLib.loadAntimonyFile.argtypes = (c_char_p, )

def loadAntimonyFile(filename):
   """
   Loads a file and parses it as an Antimony file.  On an error, the error is saved, -1 is returned, and no information is stored.

   @return a long integer indicating the index of the file read and stored.  On an error, returns -1 and no information is stored.

   @param filename The filename as a character string.  May be either absolute or relative to the directory the executable is being run from.

   @see getLastError()
   """
   if type(filename) == str:
      filename = filename.encode('utf-8')
   return __antLib.loadAntimonyFile(filename)

__antLib.loadAntimonyString.restype = c_long
__antLib.loadAntimonyString.argtypes = (c_char_p, )

def loadAntimonyString(model):
   """
   Loads a string and parses it as an Antimony set of modules.  On an error, the error is saved, -1 is returned, and no information is stored.

   @return a long integer indicating the index of the string read and stored.  On an error, returns -1 and no information is stored.

   @param model The model in Antimony format.

   @see getLastError()
   """
   if type(model) == str:
      model = model.encode('utf-8')
   return __antLib.loadAntimonyString(model)

__antLib.loadSBMLFile.restype = c_long
__antLib.loadSBMLFile.argtypes = (c_char_p, )

def loadSBMLFile(filename):
   """
   @brief Load a file known to be SBML.

   Loads a file and parses it (using libSBML) as an SBML file.  On an error, the error is saved, -1 is returned, and no information is stored.
   @return a long integer indicating the index of the file read and stored.  On an error, returns -1 and no information is stored.
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag.

   @param filename The filename as a character string.  May be either absolute or relative to the directory the executable is being run from.

   @see getLastError()
   """
   if type(filename) == str:
      filename = filename.encode('utf-8')
   return __antLib.loadSBMLFile(filename)

__antLib.loadSBMLString.restype = c_long
__antLib.loadSBMLString.argtypes = (c_char_p, )

def loadSBMLString(model):
   """
   @brief Load a string known to be SBML.

   Loads a string and parses it (using libSBML) as an SBML file.  On an error, the error is saved, -1 is returned, and no information is stored.
   @return a long integer indicating the index of the string read and stored.  On an error, returns -1 and no information is stored.
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag.

   @param model The model, in SBML format.

   @see getLastError()
   """
   if type(model) == str:
      model = model.encode('utf-8')
   return __antLib.loadSBMLString(model)

__antLib.loadSBMLStringWithLocation.restype = c_long
__antLib.loadSBMLStringWithLocation.argtypes = (c_char_p, c_char_p, )

def loadSBMLStringWithLocation(model, location):
   """
   @brief Load a string known to be SBML with its file location.

   Loads a string and parses it (using libSBML) as an SBML file.  On an error, the error is saved, -1 is returned, and no information is stored.  This function additionally allows you to set the location of the string, in case there are relative file references in the file (as there can be in some hierarchical models).
   @return a long integer indicating the index of the string read and stored.  On an error, returns -1 and no information is stored.
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag.

   @param model The model, in SBML format.
   @param location The location of the file (i.e. "file1.xml" or "/home/user/sbml/models/file.xml")

   @see getLastError()
   """
   if type(model) == str:
      model = model.encode('utf-8')
   if type(location) == str:
      location = location.encode('utf-8')
   return __antLib.loadSBMLStringWithLocation(model, location)

__antLib.getNumFiles.restype = c_ulong
__antLib.getNumFiles.argtypes = ()

def getNumFiles():
   """
   @brief Returns the number of files loaded into memory so far.

   Every time 'load<file/string>' is called successfully, the module(s) in those files are saved.  This function will tell you how many sets of modules from successful reads are resident in memory.
   @return The number of files currently stored in memory.
   """
   return __antLib.getNumFiles()

__antLib.revertTo.restype = c_bool
__antLib.revertTo.argtypes = (c_long, )

def revertTo(index):
   """
   Change the 'active' set of modules to the ones from the given index (as received from 'load<file/string>').  Attempting to revert to a negative or nonexistent index returns 'false' and the previous active set of modules is retained.  A successful change return 'true'.
   """
   return __antLib.revertTo(index)

__antLib.clearPreviousLoads.restype = None
__antLib.clearPreviousLoads.argtypes = ()

def clearPreviousLoads():
   """
   Clears memory of all files loaded.  The next successful call to 'load<file/string>' will return 0 as the first valid index.
   """
   __antLib.clearPreviousLoads()

__antLib.addDirectory.restype = None
__antLib.addDirectory.argtypes = (c_char_p, )

def addDirectory(directory):
   """
   Add a directory in which imported files may be found, and in which to look for a '.antimony' file (which contains rules about where to look locally for imported antimony and sbml files).
   """
   if type(directory) == str:
      directory = directory.encode('utf-8')
   __antLib.addDirectory(directory)

__antLib.clearDirectories.restype = None
__antLib.clearDirectories.argtypes = ()

def clearDirectories():
   """
   Clears the list of directories added with the 'addDirectory' function.
   """
   __antLib.clearDirectories()

__antLib.writeAntimonyFile.restype = c_int
__antLib.writeAntimonyFile.argtypes = (c_char_p, c_char_p, )

def writeAntimonyFile(filename, moduleName = None):
   """
   Writes out an antimony-formatted file containing the given module.  If no module name is given, all modules in the current set are returned.  If the module depends on any sub-modules, those modules are written out as well, also in the antimony format.  Returns 0 on failure (and sets an error), 1 on success.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(filename) == str:
      filename = filename.encode('utf-8')
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.writeAntimonyFile(filename, moduleName)

__antLib.getAntimonyString.restype = c_char_p
__antLib.getAntimonyString.argtypes = (c_char_p, )

def getAntimonyString(moduleName = None):
   """
   Returns the same output as writeAntimonyFile, but to a char* array instead of to a file.  Returns NULL on failure, and sets an error.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getAntimonyString(moduleName)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.writeSBMLFile.restype = c_int
__antLib.writeSBMLFile.argtypes = (c_char_p, c_char_p, )

def writeSBMLFile(filename, moduleName = None):
   """
   Writes out a SBML-formatted XML file to the file indicated.  The output is 'flattened', that is, all components of sub-modules are re-named and placed in a single model.  Returns the output of libSBML's 'writeSBML', which "Returns non-zero on success and zero if the filename could not be opened for writing."  An error indicating this is set on returning zero.
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag.

@see getSBMLString
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(filename) == str:
      filename = filename.encode('utf-8')
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.writeSBMLFile(filename, moduleName)

__antLib.getSBMLString.restype = c_char_p
__antLib.getSBMLString.argtypes = (c_char_p, )

def getSBMLString(moduleName = None):
   """
   Returns the same output as writeSBMLFile, but to a char* array instead of to a file.  The output is 'flattened', that is, all components of sub-modules are re-named and placed in a single model.  Returns the output of libSBML's 'writeSBMLToString", which "Returns the string on success and NULL if one of the underlying parser components fail (rare)."
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag.

@see writeSBMLFile
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getSBMLString(moduleName)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.setWriteSBMLTimestamp.restype = None
__antLib.setWriteSBMLTimestamp.argtypes = (c_bool, )

def setWriteSBMLTimestamp(writeTimestamp):
   """
   Sets whether, when writing an SBML file, the timestamp is included.

@see writeSBMLFile
@see getSBMLString
   """
   __antLib.setWriteSBMLTimestamp(writeTimestamp)

__antLib.writeCompSBMLFile.restype = c_int
__antLib.writeCompSBMLFile.argtypes = (c_char_p, c_char_p, )

def writeCompSBMLFile(filename, moduleName = None):
   """
   Writes out a SBML-formatted XML file to the file indicated, using the 'Hierarchichal Model Composition' package.  This retains Antimony's modularity in the SBML format.  Returns the output of libSBML's 'writeSBML', which "Returns non-zero on success and zero if the filename could not be opened for writing."  An error indicating this is set on returning zero.
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag, or if compiled without the USE_COMP flag.

@see getSBMLString
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(filename) == str:
      filename = filename.encode('utf-8')
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.writeCompSBMLFile(filename, moduleName)

__antLib.getCompSBMLString.restype = c_char_p
__antLib.getCompSBMLString.argtypes = (c_char_p, )

def getCompSBMLString(moduleName = None):
   """
   Returns the same output as writeSBMLFile, but to a char* array instead of to a file, using the 'Hierarchichal Model Composition' package.  This retains Antimony's modularity in the SBML format.  Returns the output of libSBML's 'writeSBMLToString", which "Returns the string on success and NULL if one of the underlying parser components fail (rare)."
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag, or if compiled without the USE_COMP flag.

@see writeSBMLFile
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getCompSBMLString(moduleName)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.printAllDataFor.restype = c_char_p
__antLib.printAllDataFor.argtypes = (c_char_p, )

def printAllDataFor(moduleName = None):
   """
   An example function that will print to stdout all the information in the given module.  This function probably isn't as useful to call as it is to examine and copy for your own purposes:  it only calls functions defined here in antimony_api.h.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.printAllDataFor(moduleName)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.checkModule.restype = c_bool
__antLib.checkModule.argtypes = (c_char_p, )

def checkModule(moduleName = None):
   """
   Returns 'true' if the submitted module name exists in the current active set, 'false' if not.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.checkModule(moduleName)

__antLib.getLastError.restype = c_char_p
__antLib.getLastError.argtypes = ()

def getLastError():
   """
   When any function returns an error condition, a longer description of the problem is stored in memory, and is obtainable with this function.  In most cases, this means that a call that returns a pointer returned 'NULL' (or 0).
   """
   ret = __antLib.getLastError()
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getWarnings.restype = c_char_p
__antLib.getWarnings.argtypes = ()

def getWarnings():
   """
   When translating some other format to Antimony, elements that are unable to be translated are saved as warnings, retrievable with this function (returns NULL if no warnings present).  Warnings may also be generated by problems discovered in '.antimony' files.
   """
   ret = __antLib.getWarnings()
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getSBMLInfoMessages.restype = c_char_p
__antLib.getSBMLInfoMessages.argtypes = (c_char_p, )

def getSBMLInfoMessages(moduleName = None):
   """
   Returns the 'info' messages from libSBML. libAntimony always translates its modules into SBML to check for errors.  If SBML finds errors, libAntimony gives up, passes on the error message, and does not save the model.  However, libSBML may discover other things about your model it wants to tell you about, in 'info' and 'warning' messages.  Info messages are just things it found it thinks you might want to know; warning messages are things it found which it feels violates 'best practices' in biological modelling, but not to the extent that it feels you did something actually wrong.  Since Antimony is unitless, for example, you will always find warnings about how you didn't set any units.  This function returns the 'info' messages from libSBML.  If there are no info messages, returns an empty string.
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag.
   @see getSBMLWarnings
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getSBMLInfoMessages(moduleName)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getSBMLWarnings.restype = c_char_p
__antLib.getSBMLWarnings.argtypes = (c_char_p, )

def getSBMLWarnings(moduleName = None):
   """
   Returns the 'warning' messages from libSBML.  If there are no warning messages (an unlikely occurrence), returns an empty string.
   NOTE:  This function is unavailable when libAntimony is compiled with the '-NSBML' flag.
   @see getSBMLInfoMessages
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getSBMLWarnings(moduleName)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNumModules.restype = c_ulong
__antLib.getNumModules.argtypes = ()

def getNumModules():
   """
   Returns the number of modules in the current active set (the last file successfully loaded, or whichever file was returned to with 'revertTo').
   """
   return __antLib.getNumModules()

__antLib.getModuleNames.restype = POINTER(c_char_p)
__antLib.getModuleNames.argtypes = ()

def getModuleNames():
   """
   Returns an array of all the current module names.
   """
   ret = []
   for n in range(getNumModules()):
      ret.append(getNthModuleName(n))
   return ret

__antLib.getNthModuleName.restype = c_char_p
__antLib.getNthModuleName.argtypes = (c_ulong, )

def getNthModuleName(n):
   """
   Returns the nth module name.  Returns NULL and sets an error if there is no such module n.
   """
   ret = __antLib.getNthModuleName(n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getMainModuleName.restype = c_char_p
__antLib.getMainModuleName.argtypes = ()

def getMainModuleName():
   """
   Returns the 'main' module name.  In Antimony, this is either the module marked by an asterisk ('model *mainModel()')  or the last module defined in the file.  In translated SBML models, this is the model child of the &lt;sbml&gt; object.  In translated CellML models, this is the 'containing' model that the translator creates to hold all the CellML components.  Returns NULL only if there are no modules at all.
   """
   ret = __antLib.getMainModuleName()
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNumSymbolsInInterfaceOf.restype = c_ulong
__antLib.getNumSymbolsInInterfaceOf.argtypes = (c_char_p, )

def getNumSymbolsInInterfaceOf(moduleName = None):
   """
   Returns the number of symbols defined to be in the interface of the given module.  In other words, if a module is defined 'module M(x, y, z)', this returns '3'.  (Modules with no interface symbols return '0'.)
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumSymbolsInInterfaceOf(moduleName)

__antLib.getSymbolNamesInInterfaceOf.restype = POINTER(c_char_p)
__antLib.getSymbolNamesInInterfaceOf.argtypes = (c_char_p, )

def getSymbolNamesInInterfaceOf(moduleName = None):
   """
   Returns the names of the symbols defined to be in the interface of the given module.  In other words, if a module is defined 'module M(x, y, z)', this returns the list 'x, y, z'.  A module with no symbols defined in its interface would return a pointer to an empty string.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumSymbolsInInterfaceOf(moduleName)):
      ret.append(getNthSymbolNameInInterfaceOf(moduleName, n))
   return ret

__antLib.getNthSymbolNameInInterfaceOf.restype = c_char_p
__antLib.getNthSymbolNameInInterfaceOf.argtypes = (c_char_p, c_ulong, )

def getNthSymbolNameInInterfaceOf(moduleName, n):
   """
   Returns the Nth symbol name defined to be in the interface of the given module.  If a module is defined 'module M(x, y, z)', calling this with n=0 returns "x".  If no such symbol is found, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthSymbolNameInInterfaceOf(moduleName, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNumReplacedSymbolNames.restype = c_ulong
__antLib.getNumReplacedSymbolNames.argtypes = (c_char_p, )

def getNumReplacedSymbolNames(moduleName = None):
   """
   Returns the Nth replacement symbol name of a symbol that has replaced a different symbol in the given module, through the use of an 'is' construct, or through the use of a module's interface.
   @see getNthFormerSymbolName
   @see getNthReplacementSymbolName
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumReplacedSymbolNames(moduleName)

__antLib.getAllReplacementSymbolPairs.restype = POINTER(POINTER(c_char_p))
__antLib.getAllReplacementSymbolPairs.argtypes = (c_char_p, )

def getAllReplacementSymbolPairs(moduleName = None):
   """
   Returns a list of pairs of symbol names that have been synchronized with each other--the first the symbol that was replaced, and the second the symbol used as the replacement.  These replacements are created when 'is' is used, and when a module's 'interface' (the symbols listed in parentheses) is used.
   @see getNthFormerSymbolName
   @see getNthReplacementSymbolName
   @see getNthReplacementSymbolPair
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumReplacedSymbolNames(moduleName)):
      ret.append(getNthReplacementSymbolPair(moduleName, n))
   return ret

__antLib.getNthReplacementSymbolPair.restype = POINTER(c_char_p)
__antLib.getNthReplacementSymbolPair.argtypes = (c_char_p, c_ulong, )

def getNthReplacementSymbolPair(moduleName, n):
   """
   Returns the Nth pair of symbol names that have been synchronized with each other--the first the symbol that was replaced, and the second the symbol used as the replacement.  These replacements are created when 'is' is used, and when a module's 'interface' (the symbols listed in parentheses) is used.
   @see getNthFormerSymbolName
   @see getNthReplacementSymbolName
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(1):
      ret.append((getNthFormerSymbolName(moduleName, n), getNthReplacementSymbolName(moduleName, n)))
   return ret

__antLib.getNthFormerSymbolName.restype = c_char_p
__antLib.getNthFormerSymbolName.argtypes = (c_char_p, c_ulong, )

def getNthFormerSymbolName(moduleName, n):
   """
   Returns the Nth symbol name that has been replaced by a new symbol name in the given module, through the use of an 'is' construct, or through the use of a module's interface.
   @see getNthReplacementSymbolName
   @see GetNumReplacedSymbolNames
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthFormerSymbolName(moduleName, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthReplacementSymbolName.restype = c_char_p
__antLib.getNthReplacementSymbolName.argtypes = (c_char_p, c_ulong, )

def getNthReplacementSymbolName(moduleName, n):
   """
   Returns the Nth replacement symbol name of a symbol that has replaced a different symbol in the given module, through the use of an 'is' construct, or through the use of a module's interface.
   @see getNthFormerSymbolName
   @see GetNumReplacedSymbolNames
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthReplacementSymbolName(moduleName, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNumReplacedSymbolNamesBetween.restype = c_ulong
__antLib.getNumReplacedSymbolNamesBetween.argtypes = (c_char_p, c_char_p, c_char_p, )

def getNumReplacedSymbolNamesBetween(moduleName, formerSubmodName, replacementSubmodName):
   """
   Returns the Nth replacement symbol name of a symbol that has replaced a different symbol in the given module, through the use of an 'is' construct, or through the use of a module's interface, between the given submodules, with the variable in the first submodule being the former variable name, and the variable in the second being the replacement variable name.  If an empty string is used as one of the submodule names, those synchronized variables that are not part of any submodule are searched for.
   @see getNthFormerSymbolName
   @see getNthReplacementSymbolName
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   if type(formerSubmodName) == str:
      formerSubmodName = formerSubmodName.encode('utf-8')
   if type(replacementSubmodName) == str:
      replacementSubmodName = replacementSubmodName.encode('utf-8')
   return __antLib.getNumReplacedSymbolNamesBetween(moduleName, formerSubmodName, replacementSubmodName)

__antLib.getAllReplacementSymbolPairsBetween.restype = POINTER(POINTER(c_char_p))
__antLib.getAllReplacementSymbolPairsBetween.argtypes = (c_char_p, c_char_p, c_char_p, )

def getAllReplacementSymbolPairsBetween(moduleName, formerSubmodName, replacementSubmodName):
   """
   Returns a list of pairs of symbol names that have been synchronized with each other--the first the symbol that was replaced, and the second the symbol used as the replacement, between the given submodules, with the variable in the first submodule being the former variable name, and the variable in the second being the replacement variable name.  These replacements are created when 'is' is used, and when a module's 'interface' (the symbols listed in parentheses) is used.
   @see getNthFormerSymbolName
   @see getNthReplacementSymbolName
   @see getNthReplacementSymbolPair
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   if type(formerSubmodName) == str:
      formerSubmodName = formerSubmodName.encode('utf-8')
   if type(replacementSubmodName) == str:
      replacementSubmodName = replacementSubmodName.encode('utf-8')
   ret = []
   for n in range(getNumReplacedSymbolNamesBetween(moduleName, formerSubmodName, replacementSubmodName)):
      ret.append(getNthReplacementSymbolPairBetween(moduleName, formerSubmodName, replacementSubmodName, n))
   return ret

__antLib.getNthReplacementSymbolPairBetween.restype = POINTER(c_char_p)
__antLib.getNthReplacementSymbolPairBetween.argtypes = (c_char_p, c_char_p, c_char_p, c_ulong, )

def getNthReplacementSymbolPairBetween(moduleName, formerSubmodName, replacementSubmodName, n):
   """
   Returns the Nth pair of symbol names that have been synchronized with each other--the first the symbol that was replaced, and the second the symbol used as the replacement, between the given submodules, with the variable in the first submodule being the former variable name, and the variable in the second being the replacement variable name.  These replacements are created when 'is' is used, and when a module's 'interface' (the symbols listed in parentheses) is used.
   @see getNthFormerSymbolName
   @see getNthReplacementSymbolName
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   if type(formerSubmodName) == str:
      formerSubmodName = formerSubmodName.encode('utf-8')
   if type(replacementSubmodName) == str:
      replacementSubmodName = replacementSubmodName.encode('utf-8')
   ret = []
   for n in range(getNumReplacedSymbolNamesBetween(moduleName, formerSubmodName, replacementSubmodName)):
      ret.append((getNthFormerSymbolNameBetween(moduleName, formerSubmodName, replacementSubmodName), getNthReplacementSymbolNameBetween(moduleName, formerSubmodName, replacementSubmodName)))
   return ret

__antLib.getNthFormerSymbolNameBetween.restype = c_char_p
__antLib.getNthFormerSymbolNameBetween.argtypes = (c_char_p, c_char_p, c_char_p, c_ulong, )

def getNthFormerSymbolNameBetween(moduleName, formerSubmodName, replacementSubmodName, n):
   """
   Returns the Nth symbol name that has been replaced by a new symbol name in the given module, through the use of an 'is' construct, or through the use of a module's interface, between the given submodules, with the variable in the first submodule being the former variable name, and the variable in the second being the replacement variable name.
   @see getNthReplacementSymbolName
   @see GetNumReplacedSymbolNames
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   if type(formerSubmodName) == str:
      formerSubmodName = formerSubmodName.encode('utf-8')
   if type(replacementSubmodName) == str:
      replacementSubmodName = replacementSubmodName.encode('utf-8')
   ret = __antLib.getNthFormerSymbolNameBetween(moduleName, formerSubmodName, replacementSubmodName, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthReplacementSymbolNameBetween.restype = c_char_p
__antLib.getNthReplacementSymbolNameBetween.argtypes = (c_char_p, c_char_p, c_char_p, c_ulong, )

def getNthReplacementSymbolNameBetween(moduleName, formerSubmodName, replacementSubmodName, n):
   """
   Returns the Nth replacement symbol name of a symbol that has replaced a different symbol in the given module, through the use of an 'is' construct, or through the use of a module's interface, between the given submodules, with the variable in the first submodule being the former variable name, and the variable in the second being the replacement variable name.
   @see getNthFormerSymbolName
   @see GetNumReplacedSymbolNames
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   if type(formerSubmodName) == str:
      formerSubmodName = formerSubmodName.encode('utf-8')
   if type(replacementSubmodName) == str:
      replacementSubmodName = replacementSubmodName.encode('utf-8')
   ret = __antLib.getNthReplacementSymbolNameBetween(moduleName, formerSubmodName, replacementSubmodName, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNumSymbolsOfType.restype = c_ulong
__antLib.getNumSymbolsOfType.argtypes = (c_char_p, c_int, )

def getNumSymbolsOfType(moduleName, rtype):
   """
   Returns the number of symbols of the given return type.  Useful when looping over the arrays in the subsequent functions.
   @see get()
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumSymbolsOfType(moduleName, rtype)

__antLib.getSymbolNamesOfType.restype = POINTER(c_char_p)
__antLib.getSymbolNamesOfType.argtypes = (c_char_p, c_int, )

def getSymbolNamesOfType(moduleName, rtype):
   """
   Returns the names of the symbols of the given return type.  (In SBML, these are the 'id's.)
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumSymbolsOfType(moduleName, rtype)):
      ret.append(getNthSymbolNameOfType(moduleName, rtype, n))
   return ret

__antLib.getSymbolDisplayNamesOfType.restype = POINTER(c_char_p)
__antLib.getSymbolDisplayNamesOfType.argtypes = (c_char_p, c_int, )

def getSymbolDisplayNamesOfType(moduleName, rtype):
   """
   Returns the 'display names' of the symbols of the given return type.  (In SBML, these are the 'name's.)
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumSymbolsOfType(moduleName, rtype)):
      ret.append(getNthSymbolDisplayNameOfType(moduleName, rtype, n))
   return ret

__antLib.getSymbolEquationsOfType.restype = POINTER(c_char_p)
__antLib.getSymbolEquationsOfType.argtypes = (c_char_p, c_int, )

def getSymbolEquationsOfType(moduleName, rtype):
   """
   Returns the equations associated with the symbols of the given return type.
   - Species:                 The initial assignment or assignment rule for the species in question
   - Formulas and operators:  The initial assignment or assignment rule for the formula in question
   - Compartments:            The initial assignment or assignment rule for the compartment in question
   - DNA elements:            The assignment rule or reaction rate of the element in question (no DNA element is defined by an initial assignment or by a rate rule with an initial assignment)
   - DNA Strands:             The assignment rule or reaction rate for the last element of the strand
   - Reactions and genes:     The reaction rate
   - Events:                  The trigger condition
   - Interactions:            Nothing
   - Modules:                 Nothing

   For elements that could have either initial assignments or assignment rules, use getTypeOfEquationForSymbol, or just use getSymbolInitialAssignmentsOfType and getSymbolAssignmentRulesOfType explicitly.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumSymbolsOfType(moduleName, rtype)):
      ret.append(getNthSymbolEquationOfType(moduleName, rtype, n))
   return ret

__antLib.getSymbolInitialAssignmentsOfType.restype = POINTER(c_char_p)
__antLib.getSymbolInitialAssignmentsOfType.argtypes = (c_char_p, c_int, )

def getSymbolInitialAssignmentsOfType(moduleName, rtype):
   """
   Returns the equations associated with the initial assignment for symbols of the given return type.
   - Species:                 The initial assignment for the species in question
   - Formulas and operators:  The initial assignment of the formula in question
   - Compartments:            The initial assignment for the compartment

   - DNA Strands:             Nothing
   - Reactions and genes:     Nothing
   - Events:                  Nothing
   - Interactions:            Nothing
   - Modules:                 Nothing
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumSymbolsOfType(moduleName, rtype)):
      ret.append(getNthSymbolInitialAssignmentOfType(moduleName, rtype, n))
   return ret

__antLib.getSymbolAssignmentRulesOfType.restype = POINTER(c_char_p)
__antLib.getSymbolAssignmentRulesOfType.argtypes = (c_char_p, c_int, )

def getSymbolAssignmentRulesOfType(moduleName, rtype):
   """
   Returns the equations associated with the assignment rule for symbols of the given return type.
   - Species:                 The assignment rule for the species in question
   - Formulas and operators:  The assignment rule of the formula in question
   - Compartments:            The assignment rule for the compartment
   - DNA Strands:             The assignment rule or reaction rate at the end of the strand.
   - Reactions and genes:     The reaction rate (for consistency with DNA strands)

   - Events:                  Nothing
   - Interactions:            Nothing
   - Modules:                 Nothing
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumSymbolsOfType(moduleName, rtype)):
      ret.append(getNthSymbolAssignmentRuleOfType(moduleName, rtype, n))
   return ret

__antLib.getSymbolRateRulesOfType.restype = POINTER(c_char_p)
__antLib.getSymbolRateRulesOfType.argtypes = (c_char_p, c_int, )

def getSymbolRateRulesOfType(moduleName, rtype):
   """
   Returns the equations associated with the rate rule for symbols of the given return type.
   - Species:                 The rate rule for the species in question
   - Formulas and operators:  The rate rule of the formula in question
   - Compartments:            The rate rule for the compartment
   - DNA Strands:             The rate rule or reaction rate at the end of the strand.
   - Reactions and genes:     Nothing
   - Events:                  Nothing
   - Interactions:            Nothing
   - Modules:                 Nothing
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumSymbolsOfType(moduleName, rtype)):
      ret.append(getNthSymbolRateRuleOfType(moduleName, rtype, n))
   return ret

__antLib.getSymbolCompartmentsOfType.restype = POINTER(c_char_p)
__antLib.getSymbolCompartmentsOfType.argtypes = (c_char_p, c_int, )

def getSymbolCompartmentsOfType(moduleName, rtype):
   """
   Returns the compartments associated with the symbols of the given return type.  Note that unlike in SBML, any symbol of any type may have an associated compartment, including compartments themselves.  Rules about compartments in Antimony can be found in the <A class="el" target="_top" HREF="Tutorial.pdf">Tutorial.pdf</a> document included with this documentation.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumSymbolsOfType(moduleName, rtype)):
      ret.append(getNthSymbolCompartmentOfType(moduleName, rtype, n))
   return ret

__antLib.getNthSymbolNameOfType.restype = c_char_p
__antLib.getNthSymbolNameOfType.argtypes = (c_char_p, c_int, c_ulong, )

def getNthSymbolNameOfType(moduleName, rtype, n):
   """
   Returns the name of the Nth symbol of the given type.  If no such symbol exists, NULL is returned and an error is set.  (In SBML, this is the 'id' of the element.)
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthSymbolNameOfType(moduleName, rtype, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthSymbolDisplayNameOfType.restype = c_char_p
__antLib.getNthSymbolDisplayNameOfType.argtypes = (c_char_p, c_int, c_ulong, )

def getNthSymbolDisplayNameOfType(moduleName, rtype, n):
   """
   Returns the 'display name' of the Nth symbol of the given type.  If no such symbol exists, NULL is returned and an error is set.  (In SBML, this is the 'name' of the element.)
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthSymbolDisplayNameOfType(moduleName, rtype, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthSymbolEquationOfType.restype = c_char_p
__antLib.getNthSymbolEquationOfType.argtypes = (c_char_p, c_int, c_ulong, )

def getNthSymbolEquationOfType(moduleName, rtype, n):
   """
   Returns the equation associated with the Nth symbol of the given type.  If no equation is set for the symbol in question, an empty string is returned.  If no symbol can be found, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthSymbolEquationOfType(moduleName, rtype, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthSymbolInitialAssignmentOfType.restype = c_char_p
__antLib.getNthSymbolInitialAssignmentOfType.argtypes = (c_char_p, c_int, c_ulong, )

def getNthSymbolInitialAssignmentOfType(moduleName, rtype, n):
   """
   Returns the initial assignment associated with the Nth symbol of the given type.  If no initial assignment is set for the symbol in question, an empty string is returned.  If no symbol can be found, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthSymbolInitialAssignmentOfType(moduleName, rtype, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthSymbolAssignmentRuleOfType.restype = c_char_p
__antLib.getNthSymbolAssignmentRuleOfType.argtypes = (c_char_p, c_int, c_ulong, )

def getNthSymbolAssignmentRuleOfType(moduleName, rtype, n):
   """
   Returns the assignment rule associated with the Nth symbol of the given type.  If no assignment rule is set for the symbol in question, an empty string is returned.  If no symbol can be found, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthSymbolAssignmentRuleOfType(moduleName, rtype, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthSymbolRateRuleOfType.restype = c_char_p
__antLib.getNthSymbolRateRuleOfType.argtypes = (c_char_p, c_int, c_ulong, )

def getNthSymbolRateRuleOfType(moduleName, rtype, n):
   """
   Returns the rate rule associated with the Nth symbol of the given type.  If no rate rule is set for the symbol in question, an empty string is returned.  If no symbol can be found, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthSymbolRateRuleOfType(moduleName, rtype, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthSymbolCompartmentOfType.restype = c_char_p
__antLib.getNthSymbolCompartmentOfType.argtypes = (c_char_p, c_int, c_ulong, )

def getNthSymbolCompartmentOfType(moduleName, rtype, n):
   """
   Returns the name of the compartment associated with the nth symbol of the given type.  If no compartment is explicitly set in the file, the string "default_compartment" is returned.  If no symbol can be found, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthSymbolCompartmentOfType(moduleName, rtype, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getTypeOfSymbol.restype = c_int
__antLib.getTypeOfSymbol.argtypes = (c_char_p, c_char_p, )

def getTypeOfSymbol(moduleName, symbolName):
   """
   Returns the most specific return type available for the given symbolName.  A symbol defined to be a gene, for example, will return 'allGenes' and not 'allReactions', though the symbol does indeed qualify as a reaction.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   if type(symbolName) == str:
      symbolName = symbolName.encode('utf-8')
   return __antLib.getTypeOfSymbol(moduleName, symbolName)

__antLib.getTypeOfEquationForSymbol.restype = c_int
__antLib.getTypeOfEquationForSymbol.argtypes = (c_char_p, c_char_p, )

def getTypeOfEquationForSymbol(moduleName, symbolName):
   """
   Returns the type of the 'main' equation associated with the given symbolName.  All reactions will return 'formulaKINETIC', and all events will return 'formulaTRIGGER'.  All DNA elements that are not genes will return 'formulaASSIGNMENT', as DNA elements are defined by assignment rules and kinetic laws.  All other symbols will return 'formulaINITIAL' by default (i.e. in the case where no equation at all is associated with the symbol in question), and otherwise will return formulaINITIAL for symbols defined by initial assignments only, formulaASSIGNMENT for symbols defined by assignment rules, and formulaRATE for symbols defined by both initial assignments and rate rules (or just rate rules; it is valid though not simulatable to have a symbol with a rate rule but no initial assignment).  In the case of rate rules, the initial assignment is found in the 'Equation' associated with the symbol, and the rate rule is found in the 'RateRule' associated with the symbol.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   if type(symbolName) == str:
      symbolName = symbolName.encode('utf-8')
   return __antLib.getTypeOfEquationForSymbol(moduleName, symbolName)

__antLib.getCompartmentForSymbol.restype = c_char_p
__antLib.getCompartmentForSymbol.argtypes = (c_char_p, c_char_p, )

def getCompartmentForSymbol(moduleName, symbolName):
   """
   Returns the name of the compartment the given symbol is a member of.  In antimony, all symbols may have compartments, not just species.  If a symbol has no set compartment, and is not a member of a symbol with a set compartment, this will return "default_compartment"
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   if type(symbolName) == str:
      symbolName = symbolName.encode('utf-8')
   ret = __antLib.getCompartmentForSymbol(moduleName, symbolName)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNumReactions.restype = c_ulong
__antLib.getNumReactions.argtypes = (c_char_p, )

def getNumReactions(moduleName = None):
   """
   Returns the number of reactions (including genes) in the named module.  Useful when looping over all reactions in the arrays returned by subsequent functions.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumReactions(moduleName)

__antLib.getNumReactants.restype = c_ulong
__antLib.getNumReactants.argtypes = (c_char_p, c_ulong, )

def getNumReactants(moduleName, rxn):
   """
   Returns the number of reactants (species on the left side of the reaction) for the given reaction.  If no such reaction is present, '0' is returned and an error is set.  Sadly, if there are no reactants, '0' is also returned, though no error is set.  So you'll have to keep track of this one on your own, most likely.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumReactants(moduleName, rxn)

__antLib.getNumProducts.restype = c_ulong
__antLib.getNumProducts.argtypes = (c_char_p, c_ulong, )

def getNumProducts(moduleName, rxn):
   """
   Returns the number of products (species on the right side of the reaction) for the given reaction.  If no such reaction is present, '0' is returned and an error is set.  Sadly, if there are no products, '0' is also returned, though no error is set.  So you'll have to keep track of this one on your own, too.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumProducts(moduleName, rxn)

__antLib.getReactantNames.restype = POINTER(POINTER(c_char_p))
__antLib.getReactantNames.argtypes = (c_char_p, )

def getReactantNames(moduleName = None):
   """
   Returns all the reactant names for all reactions in the given module.  The dimensions of the included arrays can be found with 'getNumReactions' and 'getNumReactants' (the array is not 'square'--each sub array may have a different length).
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumReactions(moduleName)):
      ret.append(getNthReactionReactantNames(moduleName, n))
   return ret

__antLib.getNthReactionReactantNames.restype = POINTER(c_char_p)
__antLib.getNthReactionReactantNames.argtypes = (c_char_p, c_ulong, )

def getNthReactionReactantNames(moduleName, rxn):
   """
   Returns an array of all the reactant names for the given reaction.  The length of the array can be obtained with 'getNumReactants'.  If no such reaction is present, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumReactants(moduleName, rxn)):
      ret.append(getNthReactionMthReactantName(moduleName, rxn, n))
   return ret

__antLib.getNthReactionMthReactantName.restype = c_char_p
__antLib.getNthReactionMthReactantName.argtypes = (c_char_p, c_ulong, c_ulong, )

def getNthReactionMthReactantName(moduleName, rxn, reactant):
   """
   Returns the mth reactant name of the nth reaction.  If no such reaction is present, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthReactionMthReactantName(moduleName, rxn, reactant)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getProductNames.restype = POINTER(POINTER(c_char_p))
__antLib.getProductNames.argtypes = (c_char_p, )

def getProductNames(moduleName = None):
   """
   Returns all the product names for all reactions in the given module.  The dimensions of the included arrays can be found with 'getNumReactions' and 'getNumProducts' (the array is not 'square'--each sub array may have a different length).
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumReactions(moduleName)):
      ret.append(getNthReactionProductNames(moduleName, n))
   return ret

__antLib.getNthReactionProductNames.restype = POINTER(c_char_p)
__antLib.getNthReactionProductNames.argtypes = (c_char_p, c_ulong, )

def getNthReactionProductNames(moduleName, rxn):
   """
   Returns an array of all the product names for the given reaction.  The length of the array can be obtained with 'getNumProducts'.  If no such reaction is present, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumProducts(moduleName, rxn)):
      ret.append(getNthReactionMthProductName(moduleName, rxn, n))
   return ret

__antLib.getNthReactionMthProductName.restype = c_char_p
__antLib.getNthReactionMthProductName.argtypes = (c_char_p, c_ulong, c_ulong, )

def getNthReactionMthProductName(moduleName, rxn, product):
   """
   Returns the mth product name of the given reaction.  If no such reaction or product is present, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthReactionMthProductName(moduleName, rxn, product)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getReactantStoichiometries.restype = POINTER(POINTER(c_double))
__antLib.getReactantStoichiometries.argtypes = (c_char_p, )

def getReactantStoichiometries(moduleName = None):
   """
   Returns a two-dimensional array of the stoichiometries for all reactants in all reactions in the given module.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumReactions(moduleName)):
      ret.append(getNthReactionReactantStoichiometries(moduleName, n))
   return ret

__antLib.getProductStoichiometries.restype = POINTER(POINTER(c_double))
__antLib.getProductStoichiometries.argtypes = (c_char_p, )

def getProductStoichiometries(moduleName = None):
   """
   Returns a two-dimensional array of the stoichiometries for all products in all reactions in the given module.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumReactions(moduleName)):
      ret.append(getNthReactionProductStoichiometries(moduleName, n))
   return ret

__antLib.getNthReactionReactantStoichiometries.restype = POINTER(c_double)
__antLib.getNthReactionReactantStoichiometries.argtypes = (c_char_p, c_ulong, )

def getNthReactionReactantStoichiometries(moduleName, rxn):
   """
   Returns an array of the stoichiometries for the reactants of the Nth reaction in the module.  If no such reaction exists, an error is set and NULL is returned.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumReactants(moduleName, rxn)):
      ret.append(getNthReactionMthReactantStoichiometries(moduleName, rxn, n))
   return ret

__antLib.getNthReactionProductStoichiometries.restype = POINTER(c_double)
__antLib.getNthReactionProductStoichiometries.argtypes = (c_char_p, c_ulong, )

def getNthReactionProductStoichiometries(moduleName, rxn):
   """
   Returns an array of the stoichiometries for the products of the Nth reaction in the module.  If no such reaction exists, an error is set and NULL is returned.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumProducts(moduleName, rxn)):
      ret.append(getNthReactionMthProductStoichiometries(moduleName, rxn, n))
   return ret

__antLib.getNthReactionMthReactantStoichiometries.restype = c_double
__antLib.getNthReactionMthReactantStoichiometries.argtypes = (c_char_p, c_ulong, c_ulong, )

def getNthReactionMthReactantStoichiometries(moduleName, rxn, reactant):
   """
   Returns the stoichiometry for the Mth reactant of the Nth reaction in the module.  If no such reactant or reaction exists, an error is set and 0 is returned.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNthReactionMthReactantStoichiometries(moduleName, rxn, reactant)

__antLib.getNthReactionMthProductStoichiometries.restype = c_double
__antLib.getNthReactionMthProductStoichiometries.argtypes = (c_char_p, c_ulong, c_ulong, )

def getNthReactionMthProductStoichiometries(moduleName, rxn, product):
   """
   Returns the stoichiometries for the Mth product of the Nth reaction in the module.  If no such product or reaction exists, an error is set and 0 is returned.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNthReactionMthProductStoichiometries(moduleName, rxn, product)

__antLib.getNumInteractions.restype = c_ulong
__antLib.getNumInteractions.argtypes = (c_char_p, )

def getNumInteractions(moduleName = None):
   """
   Returns the number of interactions in the named module.  Useful when looping over all interactions in the arrays returned by subsequent functions.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumInteractions(moduleName)

__antLib.getNumInteractors.restype = c_ulong
__antLib.getNumInteractors.argtypes = (c_char_p, c_ulong, )

def getNumInteractors(moduleName, rxn):
   """
   Returns the number of interactors (species on the left side of the interaction) for the given interaction.  If no such interaction is present, '0' is returned and an error is set.  Sadly, if there are no interactors, '0' is also returned, though no error is set.  So you'll have to keep track of this one on your own, most likely.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumInteractors(moduleName, rxn)

__antLib.getNumInteractees.restype = c_ulong
__antLib.getNumInteractees.argtypes = (c_char_p, c_ulong, )

def getNumInteractees(moduleName, rxn):
   """
   Returns the number of interactees (reactions on the right side of the interaction) for the given interaction.  If no such interaction is present, '0' is returned and an error is set.  Sadly, if there are no interactees, '0' is also returned, though no error is set.  So you'll have to keep track of this one on your own, too.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumInteractees(moduleName, rxn)

__antLib.getInteractorNames.restype = POINTER(POINTER(c_char_p))
__antLib.getInteractorNames.argtypes = (c_char_p, )

def getInteractorNames(moduleName = None):
   """
   Returns all the interactor names for all interactions in the given module.  The dimensions of the included arrays can be found with 'getNumInteractions' and 'getNumInteractors' (the array is not 'square'--each sub array may have a different length).
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumInteractions(moduleName)):
      ret.append(getNthInteractionInteractorNames(moduleName, n))
   return ret

__antLib.getNthInteractionInteractorNames.restype = POINTER(c_char_p)
__antLib.getNthInteractionInteractorNames.argtypes = (c_char_p, c_ulong, )

def getNthInteractionInteractorNames(moduleName, rxn):
   """
   Returns an array of all the interactor names for the given interaction.  The length of the array can be obtained with 'getNumInteractors'.  If no such interaction is present, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumInteractors(moduleName, rxn)):
      ret.append(getNthInteractionMthInteractorName(moduleName, rxn, n))
   return ret

__antLib.getNthInteractionMthInteractorName.restype = c_char_p
__antLib.getNthInteractionMthInteractorName.argtypes = (c_char_p, c_ulong, c_ulong, )

def getNthInteractionMthInteractorName(moduleName, interaction, interactor):
   """
   Returns the Mth interactor names for the given interaction.  If no such interactor or interaction is present, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthInteractionMthInteractorName(moduleName, interaction, interactor)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getInteracteeNames.restype = POINTER(POINTER(c_char_p))
__antLib.getInteracteeNames.argtypes = (c_char_p, )

def getInteracteeNames(moduleName = None):
   """
   Returns all the interactee names for all interactions in the given module.  The dimensions of the included arrays can be found with 'getNumInteractions' and 'getNumInteractees' (the array is not 'square'--each sub array may have a different length).
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumInteractions(moduleName)):
      ret.append(getNthInteractionInteracteeNames(moduleName, n))
   return ret

__antLib.getNthInteractionInteracteeNames.restype = POINTER(c_char_p)
__antLib.getNthInteractionInteracteeNames.argtypes = (c_char_p, c_ulong, )

def getNthInteractionInteracteeNames(moduleName, rxn):
   """
   Returns an array of all the interactee names for the given interaction.  The length of the array can be obtained with 'getNumInteractees'.  If no such interaction is present, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumInteractees(moduleName, rxn)):
      ret.append(getNthInteractionMthInteracteeName(moduleName, rxn, n))
   return ret

__antLib.getNthInteractionMthInteracteeName.restype = c_char_p
__antLib.getNthInteractionMthInteracteeName.argtypes = (c_char_p, c_ulong, c_ulong, )

def getNthInteractionMthInteracteeName(moduleName, interaction, interactee):
   """
   Returns the Mth interactee name for the given interaction.  If no such interactee or interaction is present, NULL is returned and an error is set.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthInteractionMthInteracteeName(moduleName, interaction, interactee)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getInteractionDividers.restype = c_int
__antLib.getInteractionDividers.argtypes = (c_char_p, )

def getInteractionDividers(moduleName = None):
   """
   Returns an array of all the interaction dividers in the given module.  The length of the array can be obtained with 'getNumInteractions'.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getInteractionDividers(moduleName)

__antLib.getNthInteractionDivider.restype = c_int
__antLib.getNthInteractionDivider.argtypes = (c_char_p, c_ulong, )

def getNthInteractionDivider(moduleName, n):
   """
   Returns the Nth interaction divider in the module.  If no such interaction is present, 0 is returned, which is 'rdBecomes, which is an invalid Interaction divider (since it's used for reactions instead).
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNthInteractionDivider(moduleName, n)

__antLib.getNumReactionRates.restype = c_ulong
__antLib.getNumReactionRates.argtypes = (c_char_p, )

def getNumReactionRates(moduleName = None):
   """
   Returns the number of reactions (and hence reaction rates) in the module.  Useful for looping over all reaction rates in the following function.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumReactionRates(moduleName)

__antLib.getReactionRates.restype = POINTER(c_char_p)
__antLib.getReactionRates.argtypes = (c_char_p, )

def getReactionRates(moduleName = None):
   """
   Returns an array of the reaction rates for the given module.  Is the same as 'getSymbolEquationsOfType(moduleName, allReactions)', but is provided for convenience.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumReactions(moduleName)):
      ret.append(getNthReactionRate(moduleName, n))
   return ret

__antLib.getNthReactionRate.restype = c_char_p
__antLib.getNthReactionRate.argtypes = (c_char_p, c_ulong, )

def getNthReactionRate(moduleName, rxn):
   """
   Returns the reaction rate for the Nth reaction in the module.  If the reaction exists, but its reaction rate has not been set, returns an empty string.  If the reaction does not exist, an error is set, and NULL is returned.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthReactionRate(moduleName, rxn)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNumEvents.restype = c_ulong
__antLib.getNumEvents.argtypes = (c_char_p, )

def getNumEvents(moduleName = None):
   """
   Returns the number of events in the given module.  Useful for subsequent functions that return arrays of information for all events.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumEvents(moduleName)

__antLib.getEventNames.restype = POINTER(c_char_p)
__antLib.getEventNames.argtypes = (c_char_p, )

def getEventNames(moduleName = None):
   """
   Returns the names of the events in the module.  Is the same as 'getSymbolNamesOfType(moduleName, allEvents)', but is provided for convenience.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = []
   for n in range(getNumEvents(moduleName)):
      ret.append(getNthEventName(moduleName, n))
   return ret

__antLib.getNthEventName.restype = c_char_p
__antLib.getNthEventName.argtypes = (c_char_p, c_ulong, )

def getNthEventName(moduleName, event):
   """
   Returns the name of the nth event in the module.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthEventName(moduleName, event)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNumAssignmentsForEvent.restype = c_ulong
__antLib.getNumAssignmentsForEvent.argtypes = (c_char_p, c_ulong, )

def getNumAssignmentsForEvent(moduleName, event):
   """
   Returns the number of assignments stored in the given event.  Useful when looping through those assignements in functions below.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getNumAssignmentsForEvent(moduleName, event)

__antLib.getTriggerForEvent.restype = c_char_p
__antLib.getTriggerForEvent.argtypes = (c_char_p, c_ulong, )

def getTriggerForEvent(moduleName, event):
   """
   Returns the trigger for the given event, as an equation that can be interpreted in a boolean context.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getTriggerForEvent(moduleName, event)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getDelayForEvent.restype = c_char_p
__antLib.getDelayForEvent.argtypes = (c_char_p, c_ulong, )

def getDelayForEvent(moduleName, event):
   """
   Returns the delay for the given event, as an equation (if present; if the event has no delay, "" is returned.  If no such module or event is present, NULL is returned and an error is set.).
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getDelayForEvent(moduleName, event)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getEventHasDelay.restype = c_bool
__antLib.getEventHasDelay.argtypes = (c_char_p, c_ulong, )

def getEventHasDelay(moduleName, event):
   """
   Returns 'true' if the given event has a delay; 'false' otherwise.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getEventHasDelay(moduleName, event)

__antLib.getPriorityForEvent.restype = c_char_p
__antLib.getPriorityForEvent.argtypes = (c_char_p, c_ulong, )

def getPriorityForEvent(moduleName, event):
   """
   Returns the priority for the given event, as an equation (if present; if the event has no priority, "" is returned.  If no such module or event is present, NULL is returned and an error is set.).
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getPriorityForEvent(moduleName, event)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getEventHasPriority.restype = c_bool
__antLib.getEventHasPriority.argtypes = (c_char_p, c_ulong, )

def getEventHasPriority(moduleName, event):
   """
   Returns 'true' if the given event has a priority; 'false' otherwise.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getEventHasPriority(moduleName, event)

__antLib.getPersistenceForEvent.restype = c_bool
__antLib.getPersistenceForEvent.argtypes = (c_char_p, c_ulong, )

def getPersistenceForEvent(moduleName, event):
   """
   Returns the value of the persistence flag for the given event (default is 'false').  Unable to return an error if there is no such event or module, so will simply return 'false' in those situations, as well.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getPersistenceForEvent(moduleName, event)

__antLib.getT0ForEvent.restype = c_bool
__antLib.getT0ForEvent.argtypes = (c_char_p, c_ulong, )

def getT0ForEvent(moduleName, event):
   """
   Returns the value at time 0 for the given event trigger (default is 'true').  Unable to return an error if there is no such event or module, so will simply return 'true' in those situations, as well.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getT0ForEvent(moduleName, event)

__antLib.getFromTriggerForEvent.restype = c_bool
__antLib.getFromTriggerForEvent.argtypes = (c_char_p, c_ulong, )

def getFromTriggerForEvent(moduleName, event):
   """
   Returns the value of the 'fromTrigger' flag for the given event trigger (default is 'true').  Unable to return an error if there is no such event or module, so will simply return 'true' in those situations, as well.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.getFromTriggerForEvent(moduleName, event)

__antLib.getNthAssignmentVariableForEvent.restype = c_char_p
__antLib.getNthAssignmentVariableForEvent.argtypes = (c_char_p, c_ulong, c_ulong, )

def getNthAssignmentVariableForEvent(moduleName, event, n):
   """
   Each assignment for an event assigns a formula to a variable.  This function returns the variable in question for the given event and assignment.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthAssignmentVariableForEvent(moduleName, event, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.getNthAssignmentEquationForEvent.restype = c_char_p
__antLib.getNthAssignmentEquationForEvent.argtypes = (c_char_p, c_ulong, c_ulong, )

def getNthAssignmentEquationForEvent(moduleName, event, n):
   """
   Each assignment for an event assigns a formula to a variable.  This function returns the in question in question for the given event and assignment.
   """
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   ret = __antLib.getNthAssignmentEquationForEvent(moduleName, event, n)
   freeAll()
   if ret==None:
      return ret
   return ret.decode('utf-8')


__antLib.freeAll.restype = None
__antLib.freeAll.argtypes = ()

def freeAll():
   """
   Frees all pointers handed to you by libAntimony.
   All libAntimony functions above that return pointers return malloc'ed pointers that you now own.  If you wish, you can ignore this and never free anything, as long as you call 'freeAll' at the very end of your program.  If you free *anything* yourself, however, calling this function will cause the program to crash!  It won't know that you already freed that pointer, and will attempt to free it again.  So either keep track of all memory management yourself, or use this function after you're completely done.

   Note that this function only frees pointers handed to you by other antimony_api functions.  The models themselves are still in memory and are available.  (To clear that memory, use clearPreviousLoads() )
   """
   __antLib.freeAll()

__antLib.addDefaultInitialValues.restype = c_bool
__antLib.addDefaultInitialValues.argtypes = (c_char_p, )

def addDefaultInitialValues(moduleName = None):
   """
   Adds default initial values to the named module.
   By default, you must provide initial values to all the values in your model.  If you call this function, all parameters and compartments will be given a default value of '1', and all your species and reaction rates will be given a default value of '0'.

   Returns 'true' if no such moduleName exists, 'false' otherwise.
   """
   if moduleName==None:
      moduleName = getMainModuleName()
   if type(moduleName) == str:
      moduleName = moduleName.encode('utf-8')
   return __antLib.addDefaultInitialValues(moduleName)

__antLib.setBareNumbersAreDimensionless.restype = None
__antLib.setBareNumbersAreDimensionless.argtypes = (c_bool, )

def setBareNumbersAreDimensionless(dimensionless):
   """
   Sets whether bare numbers are dimensionless or undefined.
   By default, all numbers in mathematical equations do not have units unless they are explicitly declared ("1 second" vs. "1").  If this function is called with a value of 'true', all numbers without declared units will be assumed to have the units 'dimensionless'.  If called with a value of 'false', the numbers will not have declared units (the default).  This only affects MathML formulas in SBML; it does not set the 'units' attribute of any parameter or other SBML element.
   """
   __antLib.setBareNumbersAreDimensionless(dimensionless)

