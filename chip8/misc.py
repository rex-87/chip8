# -*- coding: utf-8 -*-
"""
	Miscellaneous
	
	A collection of various useful functions
"""

import datetime
import hashlib
import logging
import logging.handlers
import os
import pickle
import sys
import time
import tkinter
import tkinter.messagebox
import tkinter.simpledialog
import tkinter.filedialog
import traceback

## Path to the user temporary folder
##
UserTempPath = os.path.join(os.path.expanduser('~'), 'Temp')

## --------------------------------------------
##
## LOGGING FUNCTIONS - START
##
## --------------------------------------------

## Class to handle all loggers
##
class MyLoggers(object):

	def __init__(self, Name = None, LogsFolder = None):
	
		if Name is None:
			raise Exception("Please give a name to the MyLoggers instance.")	
	
		# define logs folder if undefined
		if LogsFolder is None:
			LogsDirectory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
			LogsFolder = os.path.join(LogsDirectory, 'logs')
		
		# create logs folder if it does not exist
		if not os.path.exists(LogsFolder):
			os.makedirs(LogsFolder)
				
		# create file handler
		LogFileName = os.path.join(LogsFolder, '{}_{}.log'.format(datetime.datetime.now().strftime("%y%m%d_%H%M%S"), Name))
		fh = logging.handlers.RotatingFileHandler(
			filename = LogFileName,
			maxBytes = 10*1024*1024,
			backupCount = 1000,
			encoding = 'utf-8',
		)
		fh.setLevel(logging.DEBUG)
		
		# create console handler
		ch = logging.StreamHandler()
		
		# create formatter and add it to the handlers
		formatter = logging.Formatter('%(asctime)s | %(name)20s | %(threadName)20s | %(levelname)10s | %(message)s')
		fh.setFormatter(formatter)
		ch.setFormatter(formatter)
		
		self.Name = Name
		self.fh   = fh
		self.ch   = ch
		
		self.SetConsoleVerbosity(ConsoleVerbosity = "INFO")		
		
	def Create(self, LoggerName = None):
	
		if LoggerName is None:
			raise Exception("Please give a name to the logger.")
		
		# create new logger
		NewLogger = logging.getLogger(self.Name+"."+LoggerName)
		NewLogger.setLevel(logging.DEBUG)

		# add the handlers to the logger
		NewLogger.addHandler(self.fh)
		NewLogger.addHandler(self.ch)

		NewLogger.debug("Created logger")
		
		return NewLogger

	def SetConsoleVerbosity(self, ConsoleVerbosity = "DEBUG"):
		if ConsoleVerbosity == "DEBUG":
			self.ch.setLevel(logging.DEBUG)
		elif ConsoleVerbosity == "INFO":
			self.ch.setLevel(logging.INFO)
		else:
			raise Exception("Invalid ConsoleVerbosity '{}'".format(ConsoleVerbosity))
			
## fcr loggers
##		
MyLoggersObj = MyLoggers(Name = "chip8")

## Function to create new logger
##
def CreateLogger(LoggerName = None):
	
	# get new logger
	LOG = MyLoggersObj.Create(LoggerName = LoggerName)
	
	# create associated logging decorator
	def handle_retval_and_log(func):
		
		def wrapper(*args, **kwargs):
			
			# get function call info
			func_call_info = traceback.extract_stack()[-2]
			
			# log function info
			LOG.debug("I    = {}:{}".format(func_call_info[0], func_call_info[1]))
			LOG.debug(" F   = {}".format(func))
			LOG.debug("  P  = {} {}".format(args, kwargs))
			
			# actual function call
			RetVal_ = func(*args, **kwargs)
			
			# log function results
			RetVal = None
			ResultBaseMessage = "   R ="
			if type(RetVal_) == list and len(RetVal_) == 2:
				if RetVal_[0] != 1:			
					LOG.error("{}\n{}\n{}\n{}\n{} *** {}".format(
						"A function returned an error:",
						"I    = {}:{}".format(func_call_info[0], func_call_info[1]),
						" F   = {}".format(func),
						"  P  = {} {}".format(args, kwargs),
						ResultBaseMessage,
						RetVal_[1],
					))
					sys.exit(RetVal_[1])
				else:
					LOG.debug("{} {}".format(ResultBaseMessage, RetVal_[1]))
					RetVal = RetVal_[1]
			else:
				LOG.debug("{} {}".format(ResultBaseMessage, RetVal_))
				RetVal = RetVal_

			return RetVal
		
		return wrapper
	
	return LOG, handle_retval_and_log
LOG, handle_retval_and_log = CreateLogger(__name__)

## --------------------------------------------
##
## LOGGING FUNCTIONS - END
##
## --------------------------------------------
	
## Function to save Python object in pickle format
## https://stackoverflow.com/questions/19201290/how-to-save-a-dictionary-to-a-file
##	
def SaveObj(Obj = None, Name = None, SaveFolder = None):

	with open(os.path.join(SaveFolder, "{}.pkl".format(Name)), 'wb') as f:
		pickle.dump(Obj, f, pickle.HIGHEST_PROTOCOL)

## Function to load Python object in pickle format
## https://stackoverflow.com/questions/19201290/how-to-save-a-dictionary-to-a-file
##
def LoadObj(Name = None, SaveFolder = None):

	FileToLoad = os.path.join(SaveFolder, "{}.pkl".format(Name))
	if not os.path.exists(FileToLoad):
		return None
	with open(FileToLoad, 'rb') as f:
		return pickle.load(f)

## Function to delete a saved Python object in pickle format
##		
def DeleteSavedObj(Name = None, SaveFolder = None):

	FileToDelete = os.path.join(SaveFolder, "{}.pkl".format(Name))
	if os.path.isfile(FileToDelete):
		os.remove(FileToDelete)

## Get the hash from a file
## https://stackoverflow.com/questions/22058048/hashing-a-file-in-python
##
def GetHashFromFile(FilePath = None):

	BUF_SIZE = 65536  # lets read stuff in 64kb chunks!	
	
	sha1 = hashlib.sha1()
	with open(FilePath, 'rb') as f:
		while True:
			data = f.read(BUF_SIZE)
			if not data:
				break
			sha1.update(data)

	return sha1.hexdigest()
	
## show a window with text for the user to read decorated with a meaningful icon
## !!! NOT THREAD-SAFE : do not use directly in separate threads such as RunThread !!!
## Use Queue object as workaround. For mor details see:
## https://stackoverflow.com/questions/7014984/tkinter-tkmessagebox-not-working-in-thread
##
def ShowMessageBox(Type = "info", Title = "Message", Text = None):
	
	TypeLower = Type.lower()
	
	if TypeLower == "info":
		message_box_method = tkinter.messagebox.showinfo
	elif TypeLower == "warning":
		message_box_method = tkinter.messagebox.showwarning	
	elif TypeLower == "error":
		message_box_method = tkinter.messagebox.showerror	
	elif TypeLower == "yesno":
		message_box_method = tkinter.messagebox.askyesno
	else:
		raise Exception("Unexpected message box type '{}'".format(Type))
	
	root = tkinter.Tk()	
	root.withdraw()
	Response = message_box_method(Title, Text)
	root.destroy()
	
	return Response

## show a window with question and input box for the user to populate.
## !!! NOT THREAD-SAFE : do not use directly in separate threads such as RunThread !!!
## Use Queue object as workaround. For mor details see:
## https://stackoverflow.com/questions/7014984/tkinter-tkmessagebox-not-working-in-thread
##	
def ShowUserInputBox(Title = "Untitled", QuestionText = None, InitialValue = ""):
	
	if QuestionText == None:
		raise Exception("QuestionText cannot be None")
	
	root = tkinter.Tk()	
	root.withdraw()
	UserInputStr = tkinter.simpledialog.askstring(Title, QuestionText, initialvalue = InitialValue)
	root.destroy()
	return UserInputStr

## show a file dialog window to get a filename from the user.
## !!! NOT THREAD-SAFE : do not use directly in separate threads such as RunThread !!!
## Use Queue object as workaround. For mor details see:
## https://stackoverflow.com/questions/7014984/tkinter-tkmessagebox-not-working-in-thread
##	
def ShowFileDialogBox(Title = "Choose a file", FileTypes = (("All files", "*"),), InitialDir = None):
	
	askopenfilename_dict = {}
	askopenfilename_dict['title']	 = Title
	askopenfilename_dict['filetypes'] = FileTypes
	if InitialDir != None:
		askopenfilename_dict['initialdir'] = InitialDir
	
	root = tkinter.Tk()	
	root.withdraw()
	FileName = tkinter.filedialog.askopenfilename(**askopenfilename_dict)
	root.destroy()
	return FileName
